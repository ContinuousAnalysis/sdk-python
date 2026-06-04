from http import HTTPStatus
from types import SimpleNamespace

import httpx
import pytest

import blaxel.core.jobs as job_module
from blaxel.core.client import errors
from blaxel.core.client.api.compute import create_sandbox, list_sandboxes
from blaxel.core.client.client import Client
from blaxel.core.client.models.job_execution_list import JobExecutionList
from blaxel.core.client.models.sandbox_error import SandboxError
from blaxel.core.client.models.sandbox_list import SandboxList
from blaxel.core.jobs import BlJob
from blaxel.core.sandbox.default import sandbox as sandbox_module


def response(status_code: int, content: bytes, content_type: str) -> httpx.Response:
    return httpx.Response(
        status_code,
        content=content,
        headers={"Content-Type": content_type},
        request=httpx.Request("POST", "https://api.blaxel.test/v0/sandboxes"),
    )


def sandbox_payload(name: str) -> dict:
    return {
        "metadata": {"name": name},
        "spec": {"enabled": True},
    }


def test_documented_html_error_body_raises_sdk_parse_error():
    client = Client(base_url="https://api.blaxel.test", raise_on_unexpected_status=True)
    html = b'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"><html></html>'

    with pytest.raises(errors.ResponseParseError) as exc_info:
        create_sandbox._parse_response(
            client=client,
            response=response(403, html, "text/html"),
        )

    exc = exc_info.value
    assert exc.status_code == 403
    assert exc.content == html
    assert exc.content_type == "text/html"
    assert "Could not parse response body for documented status code 403 as JSON" in str(exc)
    assert "<!DOCTYPE HTML" in str(exc)


def test_documented_html_error_body_returns_none_when_raises_disabled():
    client = Client(base_url="https://api.blaxel.test", raise_on_unexpected_status=False)

    parsed = create_sandbox._parse_response(
        client=client,
        response=response(403, b"<html></html>", "text/html"),
    )

    assert parsed is None


def test_documented_json_error_body_still_parses_model():
    client = Client(base_url="https://api.blaxel.test", raise_on_unexpected_status=True)
    parsed = create_sandbox._parse_response(
        client=client,
        response=httpx.Response(
            403,
            json={"code": "UNAUTHORIZED", "message": "Authorization failed", "status_code": 403},
            request=httpx.Request("POST", "https://api.blaxel.test/v0/sandboxes"),
        ),
    )

    assert isinstance(parsed, SandboxError)
    assert parsed.code == "UNAUTHORIZED"
    assert parsed.message == "Authorization failed"
    assert parsed.status_code == 403


def test_undocumented_status_still_uses_unexpected_status():
    client = Client(base_url="https://api.blaxel.test", raise_on_unexpected_status=True)

    with pytest.raises(errors.UnexpectedStatus):
        create_sandbox._parse_response(
            client=client,
            response=response(418, b"teapot", "text/plain"),
        )


@pytest.mark.parametrize(
    ("payload", "expected_names"),
    [
        ([sandbox_payload("legacy-list-shape")], ["legacy-list-shape"]),
        ([], []),
        ({}, []),
    ],
)
def test_paginated_list_model_accepts_legacy_response_shapes(payload, expected_names):
    client = Client(base_url="https://api.blaxel.test", raise_on_unexpected_status=True)

    parsed = list_sandboxes._parse_response(
        client=client,
        response=httpx.Response(
            200,
            json=payload,
            request=httpx.Request("GET", "https://api.blaxel.test/v0/sandboxes"),
        ),
    )

    assert isinstance(parsed, SandboxList)
    assert [sandbox.metadata.name for sandbox in parsed.data] == expected_names


def test_paginated_list_model_preserves_json_null_as_none():
    client = Client(base_url="https://api.blaxel.test", raise_on_unexpected_status=True)

    parsed = list_sandboxes._parse_response(
        client=client,
        response=httpx.Response(
            200,
            content=b"null",
            headers={"Content-Type": "application/json"},
            request=httpx.Request("GET", "https://api.blaxel.test/v0/sandboxes"),
        ),
    )

    assert parsed is None


@pytest.mark.asyncio
async def test_sandbox_instance_list_unwraps_paginated_response(monkeypatch):
    async def fake_list_sandboxes(*, client):
        return SandboxList.from_dict({"data": [sandbox_payload("wrapped-list-shape")]})

    monkeypatch.setattr(sandbox_module, "list_sandboxes", fake_list_sandboxes)

    sandboxes = await sandbox_module.SandboxInstance.list()

    assert len(sandboxes) == 1
    assert sandboxes[0].metadata.name == "wrapped-list-shape"


def test_job_list_executions_unwraps_paginated_response(monkeypatch):
    def fake_list_job_executions(*, job_id, client, limit, offset):
        assert job_id == "mk3"
        assert limit == 20
        assert offset == 0
        return SimpleNamespace(
            status_code=HTTPStatus.OK,
            parsed=JobExecutionList.from_dict({"data": []}),
        )

    monkeypatch.setattr(
        job_module.list_job_executions,
        "sync_detailed",
        fake_list_job_executions,
    )

    executions = BlJob("mk3").list_executions()

    assert executions == []


@pytest.mark.asyncio
async def test_job_alist_executions_unwraps_paginated_response(monkeypatch):
    async def fake_list_job_executions(*, job_id, client, limit, offset):
        assert job_id == "mk3"
        assert limit == 20
        assert offset == 0
        return SimpleNamespace(
            status_code=HTTPStatus.OK,
            parsed=JobExecutionList.from_dict({"data": []}),
        )

    monkeypatch.setattr(
        job_module.list_job_executions,
        "asyncio_detailed",
        fake_list_job_executions,
    )

    executions = await BlJob("mk3").alist_executions()

    assert executions == []
