"""
Manual test for per-drive ACL enforcement (ENG-2761).

Prerequisites (all three PRs must be deployed):
  - controlplane#4582  -- DrivePermission model + ACL sync to filer
  - seaweedfs#27       -- filer-side ACL enforcement (domain-aware: blaxel.dev / blaxel.ai)
  - executionplane#171 -- workload labels in JWT token

Environment variables:
  BL_WORKSPACE     -- workspace name
  BL_API_KEY       -- API key with drive + sandbox permissions
  BL_ENV           -- "dev" or "prod" (default: "dev")
  BL_DRIVE_REGION  -- drive region override (default: eu-dub-1 for dev, us-pdx-1 for prod)

Usage:
  uv run python tests/manual/drive_acl.py
  uv run python tests/manual/drive_acl.py --scenario open-access
  uv run python tests/manual/drive_acl.py --scenario label-match
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from blaxel.core.client.models import Drive, DriveSpec, Metadata, MetadataLabels
from blaxel.core.client.models.drive_permission import DrivePermission
from blaxel.core.client.models.drive_permission_labels import DrivePermissionLabels
from blaxel.core.client.models.drive_permission_mode import DrivePermissionMode
from blaxel.core.client.types import UNSET
from blaxel.core.common.settings import settings
from blaxel.core.drive import DriveInstance
from blaxel.core.sandbox import SandboxInstance

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ENV = os.environ.get("BL_ENV", "dev")
REGION = os.environ.get("BL_DRIVE_REGION", "eu-dub-1" if ENV == "dev" else "us-pdx-1")
IMAGE = "blaxel/base-image:latest"
TEST_LABELS = {"env": "manual-test", "created-by": "drive-acl-test"}
EXEC_TIMEOUT_S = 30
MOUNT_SETTLE_S = 3

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def async_sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


async def create_drive_with_permissions(
    name: str,
    permissions: list[dict[str, Any]],
) -> DriveInstance:
    perm_objects = []
    for p in permissions:
        raw_labels = p.get("labels", {})
        if raw_labels:
            labels = DrivePermissionLabels.from_dict(raw_labels)
        else:
            # Empty dict is falsy, from_dict returns None; construct manually
            labels = DrivePermissionLabels()
        mode = DrivePermissionMode(p.get("mode", "read-write"))
        path = p.get("path", UNSET)
        perm_objects.append(DrivePermission(labels=labels, mode=mode, path=path))

    drive = Drive(
        metadata=Metadata(
            name=name,
            labels=MetadataLabels.from_dict(TEST_LABELS),
        ),
        spec=DriveSpec(
            region=REGION,
            size=1,
            permissions=perm_objects,
        ),
    )
    return await DriveInstance.create(drive)


async def update_drive_permissions(
    drive_name: str,
    permissions: list[dict[str, Any]],
) -> None:
    await settings.authenticate()
    auth_headers = settings.headers
    base_url = settings.base_url
    url = f"{base_url}/drives/{drive_name}"

    perm_dicts = []
    for p in permissions:
        perm_dicts.append(
            {
                "labels": p.get("labels", {}),
                "mode": p.get("mode", "read-write"),
            }
        )

    async with httpx.AsyncClient() as http_client:
        res = await http_client.put(
            url,
            headers={"Content-Type": "application/json", **auth_headers},
            json={"metadata": {}, "spec": {"permissions": perm_dicts}},
        )
        if res.status_code >= 400:
            raise Exception(f"Failed to update drive permissions: {res.status_code} {res.text}")


async def create_sandbox(
    name: str,
    labels: dict[str, str],
) -> SandboxInstance:
    return await SandboxInstance.create(
        {
            "name": name,
            "image": IMAGE,
            "memory": 2048,
            "region": REGION,
            "labels": {**TEST_LABELS, **labels},
        },
        safe=True,
    )


async def exec_in_sandbox(
    sbx: SandboxInstance,
    command: str,
) -> tuple[bool, str]:
    try:
        result = await asyncio.wait_for(
            sbx.process.exec({"command": command, "wait_for_completion": True}),
            timeout=EXEC_TIMEOUT_S,
        )
        return (True, result.logs or "")
    except Exception as err:
        return (False, str(err))


# ---------------------------------------------------------------------------
# Cleanup tracker
# ---------------------------------------------------------------------------

cleanup_sandboxes: list[str] = []
cleanup_drives: list[str] = []


async def cleanup() -> None:
    print("\n--- Cleanup ---")
    for name in cleanup_sandboxes:
        try:
            await SandboxInstance.delete(name)
            print(f"  deleted sandbox {name}")
        except Exception:
            pass
    await async_sleep(5)
    for name in cleanup_drives:
        try:
            await DriveInstance.delete(name)
            print(f"  deleted drive {name}")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------


@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str
    skipped: bool = False


results: list[TestResult] = []


def record(name: str, passed: bool, detail: str) -> None:
    icon = "PASS" if passed else "FAIL"
    print(f"  [{icon}] {name}: {detail}")
    results.append(TestResult(name=name, passed=passed, detail=detail))


def skip(name: str, reason: str) -> None:
    print(f"  [SKIP] {name}: {reason}")
    results.append(TestResult(name=name, passed=True, detail=reason, skipped=True))


def format_error(err: Exception) -> str:
    return str(err)


async def debug_jwt(sbx: SandboxInstance) -> dict[str, Any] | None:
    domain = "blaxel.dev" if ENV == "dev" else "blaxel.ai"
    token_path = f"/var/run/secrets/{domain}/identity/token"
    ok, logs = await exec_in_sandbox(sbx, f"cat {token_path}")
    if not ok or not logs.strip():
        print(f"  [DEBUG] Could not read JWT from {token_path}: {logs}")
        return None
    try:
        parts = logs.strip().split(".")
        if len(parts) != 3:
            return None
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
        payload_str = json.dumps(payload, indent=2)
        print(f"  [DEBUG] JWT claims: {chr(10).join(payload_str.split(chr(10))[:15])}...")
        return payload
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


async def scenario_open_access() -> None:
    """Drive with NO permissions (empty array) -- any sandbox can access."""
    print("\n=== Scenario: open-access (no permissions = allow all) ===")
    drive_name = uid("acl-open")
    sbx_name = uid("acl-open-sbx")

    await create_drive_with_permissions(drive_name, [])
    cleanup_drives.append(drive_name)

    sbx = await create_sandbox(sbx_name, {"role": "anything"})
    cleanup_sandboxes.append(sbx_name)

    await sbx.drives.mount(drive_name, "/mnt/open")
    await async_sleep(MOUNT_SETTLE_S)

    ok, logs = await exec_in_sandbox(sbx, "echo 'open-access-ok' > /mnt/open/test.txt")
    record("open-access write", ok, "wrote successfully" if ok else logs)

    ok, logs = await exec_in_sandbox(sbx, "cat /mnt/open/test.txt")
    record("open-access read", ok and "open-access-ok" in logs, logs.strip())


async def scenario_label_match() -> None:
    """Drive with label-based permission -- matching sandbox gets access."""
    print("\n=== Scenario: label-match (sandbox has matching labels) ===")
    drive_name = uid("acl-match")
    sbx_name = uid("acl-match-sbx")

    await create_drive_with_permissions(
        drive_name,
        [
            {"labels": {"team": "backend", "project": "acl-test"}, "mode": "read-write"},
        ],
    )
    cleanup_drives.append(drive_name)

    sbx = await create_sandbox(sbx_name, {"team": "backend", "project": "acl-test"})
    cleanup_sandboxes.append(sbx_name)

    await debug_jwt(sbx)

    await sbx.drives.mount(drive_name, "/mnt/match")
    await async_sleep(MOUNT_SETTLE_S)

    ok, logs = await exec_in_sandbox(sbx, "echo 'label-match-ok' > /mnt/match/test.txt")
    record("label-match write", ok, "wrote successfully" if ok else logs)

    ok, logs = await exec_in_sandbox(sbx, "cat /mnt/match/test.txt")
    record("label-match read", ok and "label-match-ok" in logs, logs.strip())


async def scenario_label_mismatch() -> None:
    """Drive with label-based permission -- non-matching sandbox is denied."""
    print("\n=== Scenario: label-mismatch (sandbox lacks required labels) ===")
    drive_name = uid("acl-mis")
    sbx_name = uid("acl-mis-sbx")

    await create_drive_with_permissions(
        drive_name,
        [
            {"labels": {"team": "secret-team"}, "mode": "read-write"},
        ],
    )
    cleanup_drives.append(drive_name)

    sbx = await create_sandbox(sbx_name, {"team": "other"})
    cleanup_sandboxes.append(sbx_name)

    try:
        await sbx.drives.mount(drive_name, "/mnt/mis")
        await async_sleep(MOUNT_SETTLE_S)
        ok, logs = await exec_in_sandbox(sbx, "echo 'should-fail' > /mnt/mis/test.txt")
        record(
            "label-mismatch mount+write denied",
            not ok,
            f"unexpected success: {logs.strip()}" if ok else "write denied at file level",
        )
    except Exception as err:
        msg = format_error(err)
        is_acl_denial = any(
            s in msg
            for s in ("timeout", "denied", "Permission", "exited unexpectedly: exit status 2")
        )
        record(
            "label-mismatch mount denied",
            is_acl_denial,
            "mount correctly denied by ACL" if is_acl_denial else f"unexpected error: {msg}",
        )


async def scenario_read_only() -> None:
    """Read-only mode: matching sandbox can read but NOT write."""
    print("\n=== Scenario: read-only (mode=read blocks writes) ===")
    drive_name = uid("acl-ro")
    writer_name = uid("acl-ro-writer")
    reader_name = uid("acl-ro-reader")

    await create_drive_with_permissions(
        drive_name,
        [
            {"labels": {"role": "reader"}, "mode": "read"},
            {"labels": {"role": "writer"}, "mode": "read-write"},
        ],
    )
    cleanup_drives.append(drive_name)

    writer = await create_sandbox(writer_name, {"role": "writer"})
    cleanup_sandboxes.append(writer_name)
    await writer.drives.mount(drive_name, "/mnt/ro")
    await async_sleep(MOUNT_SETTLE_S)

    ok, logs = await exec_in_sandbox(writer, "echo 'read-only-test-data' > /mnt/ro/readonly.txt")
    record("read-only seed write", ok, "seeded data" if ok else logs)

    reader = await create_sandbox(reader_name, {"role": "reader"})
    cleanup_sandboxes.append(reader_name)
    try:
        await reader.drives.mount(drive_name, "/mnt/ro", read_only=True)
    except Exception as err:
        msg = format_error(err)
        record("read-only mount", False, f"mount failed: {msg}")
        return
    await async_sleep(MOUNT_SETTLE_S)

    ok, logs = await exec_in_sandbox(reader, "cat /mnt/ro/readonly.txt")
    record("read-only read succeeds", ok and "read-only-test-data" in logs, logs.strip())

    ok, logs = await exec_in_sandbox(reader, "echo 'should-fail' > /mnt/ro/illegal.txt")
    record(
        "read-only write denied",
        not ok or any(s in logs for s in ("denied", "Read-only", "Permission", "error")),
        f"unexpected success: {logs.strip()}" if ok else "write denied as expected",
    )


async def scenario_multiple_permissions_or() -> None:
    """Two permissions with OR logic -- second rule match grants access."""
    print("\n=== Scenario: multiple-permissions-or (first match wins) ===")
    drive_name = uid("acl-or")
    sbx_name = uid("acl-or-sbx")

    await create_drive_with_permissions(
        drive_name,
        [
            {"labels": {"team": "alpha"}, "mode": "read-write"},
            {"labels": {"team": "beta"}, "mode": "read-write"},
        ],
    )
    cleanup_drives.append(drive_name)

    sbx = await create_sandbox(sbx_name, {"team": "beta"})
    cleanup_sandboxes.append(sbx_name)

    await sbx.drives.mount(drive_name, "/mnt/or")
    await async_sleep(MOUNT_SETTLE_S)

    ok, logs = await exec_in_sandbox(sbx, "echo 'or-logic-ok' > /mnt/or/test.txt")
    record("or-logic write", ok, "wrote successfully" if ok else logs)

    ok, logs = await exec_in_sandbox(sbx, "cat /mnt/or/test.txt")
    record("or-logic read", ok and "or-logic-ok" in logs, logs.strip())


async def scenario_and_logic() -> None:
    """AND logic within a single permission -- all labels must match."""
    print("\n=== Scenario: and-logic (all labels must match within a permission) ===")
    drive_name = uid("acl-and")
    sbx_partial_name = uid("acl-and-partial")
    sbx_full_name = uid("acl-and-full")

    await create_drive_with_permissions(
        drive_name,
        [
            {"labels": {"team": "core", "tier": "staging"}, "mode": "read-write"},
        ],
    )
    cleanup_drives.append(drive_name)

    # Partial match: has team=core but NOT tier=staging -- should be denied
    partial = await create_sandbox(sbx_partial_name, {"team": "core"})
    cleanup_sandboxes.append(sbx_partial_name)
    try:
        await partial.drives.mount(drive_name, "/mnt/and")
        await async_sleep(MOUNT_SETTLE_S)
        ok, logs = await exec_in_sandbox(partial, "echo 'should-fail' > /mnt/and/test.txt")
        record(
            "and-logic partial denied",
            not ok,
            f"unexpected success: {logs.strip()}" if ok else "denied at file level",
        )
    except Exception as err:
        msg = format_error(err)
        is_acl_denial = any(
            s in msg
            for s in ("timeout", "denied", "Permission", "exited unexpectedly: exit status 2")
        )
        record(
            "and-logic partial denied",
            is_acl_denial,
            "mount correctly denied (partial label match)"
            if is_acl_denial
            else f"unexpected error: {msg}",
        )

    # Full match: has both team=core AND tier=staging -- should succeed
    full = await create_sandbox(sbx_full_name, {"team": "core", "tier": "staging"})
    cleanup_sandboxes.append(sbx_full_name)
    await full.drives.mount(drive_name, "/mnt/and")
    await async_sleep(MOUNT_SETTLE_S)

    ok, logs = await exec_in_sandbox(full, "echo 'and-logic-ok' > /mnt/and/test.txt")
    record("and-logic full-match write", ok, "wrote successfully" if ok else logs)


async def scenario_path_scoping() -> None:
    """Permission restricts access to /data/ subfolder."""
    print("\n=== Scenario: path-scoping (permission restricts to subfolder) ===")
    drive_name = uid("acl-path")
    writer_name = uid("acl-path-writer")
    scoped_name = uid("acl-path-scoped")

    await create_drive_with_permissions(
        drive_name,
        [
            {"labels": {"role": "admin"}, "mode": "read-write", "path": "/"},
            {"labels": {"role": "scoped"}, "mode": "read-write", "path": "/data"},
        ],
    )
    cleanup_drives.append(drive_name)

    # Admin sandbox: seed data in both root and /data/
    admin = await create_sandbox(writer_name, {"role": "admin"})
    cleanup_sandboxes.append(writer_name)
    await admin.drives.mount(drive_name, "/mnt/path")
    await async_sleep(MOUNT_SETTLE_S)

    await exec_in_sandbox(admin, "echo 'root-secret' > /mnt/path/secret.txt")
    await exec_in_sandbox(
        admin, "mkdir -p /mnt/path/data && echo 'data-ok' > /mnt/path/data/file.txt"
    )

    # Scoped sandbox: mount with drive_path="/data" (only has access to /data)
    scoped = await create_sandbox(scoped_name, {"role": "scoped"})
    cleanup_sandboxes.append(scoped_name)
    await scoped.drives.mount(drive_name, "/mnt/scoped", drive_path="/data")
    await async_sleep(MOUNT_SETTLE_S)

    ok, logs = await exec_in_sandbox(scoped, "cat /mnt/scoped/file.txt")
    record("path-scoping /data read", ok and "data-ok" in logs, logs.strip())

    ok, logs = await exec_in_sandbox(scoped, "cat /mnt/scoped/secret.txt")
    record(
        "path-scoping root not visible",
        not ok or "No such file" in logs,
        f"unexpected: {logs.strip()}" if ok else "root files not visible as expected",
    )


async def scenario_update_permissions() -> None:
    """Update permissions on an existing drive, verify enforcement changes."""
    print("\n=== Scenario: update-permissions (edit permissions on existing drive) ===")
    drive_name = uid("acl-upd")
    sbx_open_name = uid("acl-upd-open")
    sbx_denied_name = uid("acl-upd-denied")
    sbx_allowed_name = uid("acl-upd-allowed")

    # Step 1: Create drive with NO permissions (open access)
    await create_drive_with_permissions(drive_name, [])
    cleanup_drives.append(drive_name)

    sbx_open = await create_sandbox(sbx_open_name, {"role": "tester"})
    cleanup_sandboxes.append(sbx_open_name)
    await sbx_open.drives.mount(drive_name, "/mnt/upd")
    await async_sleep(MOUNT_SETTLE_S)

    ok, logs = await exec_in_sandbox(sbx_open, "echo 'before-update' > /mnt/upd/test.txt")
    record("update-permissions open write", ok, "wrote before restriction" if ok else logs)

    # Step 2: Update drive to restrict permissions
    await update_drive_permissions(
        drive_name,
        [
            {"labels": {"team": "restricted"}, "mode": "read-write"},
        ],
    )
    record("update-permissions API call", True, "permissions updated successfully")

    # Step 3: Verify the update persisted
    updated = await DriveInstance.get(drive_name)
    perms = updated.spec.permissions if updated.spec else None
    has_perms = (
        perms is not None
        and len(perms) == 1
        and hasattr(perms[0], "labels")
        and perms[0].labels is not None
        and perms[0].labels.additional_properties.get("team") == "restricted"
    )
    record(
        "update-permissions persisted",
        has_perms,
        "permissions correctly saved" if has_perms else f"got: {perms}",
    )

    # Step 4: New sandbox WITHOUT the label should be denied
    sbx_denied = await create_sandbox(sbx_denied_name, {"team": "other"})
    cleanup_sandboxes.append(sbx_denied_name)
    try:
        await sbx_denied.drives.mount(drive_name, "/mnt/upd")
        await async_sleep(MOUNT_SETTLE_S)
        ok, logs = await exec_in_sandbox(sbx_denied, "echo 'should-fail' > /mnt/upd/test.txt")
        record(
            "update-permissions denied after update",
            not ok,
            f"unexpected success: {logs.strip()}" if ok else "write denied at file level",
        )
    except Exception as err:
        msg = format_error(err)
        is_acl_denial = any(
            s in msg
            for s in ("timeout", "denied", "Permission", "exited unexpectedly: exit status 2")
        )
        record(
            "update-permissions denied after update",
            is_acl_denial,
            "mount correctly denied after permission update"
            if is_acl_denial
            else f"unexpected error: {msg}",
        )

    # Step 5: New sandbox WITH the label should succeed
    sbx_allowed = await create_sandbox(sbx_allowed_name, {"team": "restricted"})
    cleanup_sandboxes.append(sbx_allowed_name)
    await sbx_allowed.drives.mount(drive_name, "/mnt/upd")
    await async_sleep(MOUNT_SETTLE_S)

    ok, logs = await exec_in_sandbox(sbx_allowed, "echo 'after-update-ok' > /mnt/upd/test2.txt")
    record(
        "update-permissions allowed after update", ok, "wrote with correct labels" if ok else logs
    )

    ok, logs = await exec_in_sandbox(sbx_allowed, "cat /mnt/upd/test2.txt")
    record("update-permissions allowed read", ok and "after-update-ok" in logs, logs.strip())


async def scenario_wildcard_permission() -> None:
    """Wildcard permission (empty labels = match all workloads)."""
    print("\n=== Scenario: wildcard-permission (empty labels match all) ===")
    drive_name = uid("acl-wild")
    sbx_name = uid("acl-wild-sbx")

    await create_drive_with_permissions(
        drive_name,
        [
            {"labels": {}, "mode": "read-write"},
        ],
    )
    cleanup_drives.append(drive_name)

    sbx = await create_sandbox(sbx_name, {"random": "anything"})
    cleanup_sandboxes.append(sbx_name)

    await sbx.drives.mount(drive_name, "/mnt/wild")
    await async_sleep(MOUNT_SETTLE_S)

    ok, logs = await exec_in_sandbox(sbx, "echo 'wildcard-ok' > /mnt/wild/test.txt")
    record("wildcard-permission write", ok, "wrote successfully" if ok else logs)

    ok, logs = await exec_in_sandbox(sbx, "cat /mnt/wild/test.txt")
    record("wildcard-permission read", ok and "wildcard-ok" in logs, logs.strip())


# ---------------------------------------------------------------------------
# Scenario registry
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, Any] = {
    "open-access": scenario_open_access,
    "label-match": scenario_label_match,
    "label-mismatch": scenario_label_mismatch,
    "read-only": scenario_read_only,
    "multiple-permissions-or": scenario_multiple_permissions_or,
    "and-logic": scenario_and_logic,
    "path-scoping": scenario_path_scoping,
    "update-permissions": scenario_update_permissions,
    "wildcard-permission": scenario_wildcard_permission,
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    args = sys.argv[1:]
    selected_scenario: str | None = None
    if "--scenario" in args:
        idx = args.index("--scenario")
        if idx + 1 < len(args):
            selected_scenario = args[idx + 1]

    print("Drive ACL Manual Test (ENG-2761)")
    print(f"  env={ENV}  region={REGION}")
    print(f"  scenarios={selected_scenario or 'all'}")

    if selected_scenario and selected_scenario not in SCENARIOS:
        print(f"Unknown scenario: {selected_scenario}")
        print(f"Available: {', '.join(SCENARIOS.keys())}")
        sys.exit(1)

    to_run = {selected_scenario: SCENARIOS[selected_scenario]} if selected_scenario else SCENARIOS

    try:
        for name, fn in to_run.items():
            try:
                await fn()
            except Exception as err:
                record(f"{name} (scenario error)", False, format_error(err))
    finally:
        await cleanup()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = [r for r in results if r.passed and not r.skipped]
    skipped = [r for r in results if r.skipped]
    failed = [r for r in results if not r.passed]

    print(f"  Total:   {len(results)}")
    print(f"  Passed:  {len(passed)}")
    print(f"  Skipped: {len(skipped)}")
    print(f"  Failed:  {len(failed)}")

    if failed:
        print("\nFailed checks:")
        for f in failed:
            print(f"  - {f.name}: {f.detail}")

    print()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
