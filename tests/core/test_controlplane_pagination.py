from types import SimpleNamespace

import pytest

from blaxel.core.client.models import Drive, DriveSpec, Metadata, Sandbox, SandboxSpec
from blaxel.core.client.models.drive_list import DriveList
from blaxel.core.client.models.job_execution import JobExecution
from blaxel.core.client.models.job_execution_list import JobExecutionList
from blaxel.core.client.models.job_execution_metadata import JobExecutionMetadata
from blaxel.core.client.models.job_execution_spec import JobExecutionSpec
from blaxel.core.client.models.pagination_meta import PaginationMeta
from blaxel.core.client.models.sandbox_list import SandboxList
from blaxel.core.client.types import UNSET
from blaxel.core.drive.drive import SyncDriveInstance
from blaxel.core.jobs import bl_job
from blaxel.core.sandbox.default.sandbox import SandboxInstance


@pytest.mark.asyncio
async def test_sandbox_list_returns_page_with_next_page(monkeypatch):
    pages = [
        SandboxList(
            data=[Sandbox(metadata=Metadata(name="sandbox-a"), spec=SandboxSpec())],
            meta=PaginationMeta(has_more=True, next_cursor="cursor-2"),
        ),
        SandboxList(
            data=[Sandbox(metadata=Metadata(name="sandbox-b"), spec=SandboxSpec())],
            meta=PaginationMeta(has_more=False),
        ),
    ]
    calls = []

    async def fake_list_sandboxes(*, client, cursor=UNSET, limit=50):
        calls.append((cursor, limit))
        return pages.pop(0)

    monkeypatch.setattr("blaxel.core.sandbox.default.sandbox.list_sandboxes", fake_list_sandboxes)

    page = await SandboxInstance.list(limit=1)
    next_page = await page.next_page()

    assert [sandbox.metadata.name for sandbox in page.data] == ["sandbox-a"]
    assert page.has_more is True
    assert page.next_cursor == "cursor-2"
    assert [sandbox.metadata.name for sandbox in next_page.data] == ["sandbox-b"]
    assert next_page.has_more is False
    assert calls == [(UNSET, 1), ("cursor-2", 1)]


def test_drive_list_returns_page_with_next_page(monkeypatch):
    pages = [
        DriveList(
            data=[Drive(metadata=Metadata(name="drive-a"), spec=DriveSpec())],
            meta=PaginationMeta(has_more=True, next_cursor="cursor-2"),
        ),
        DriveList(
            data=[Drive(metadata=Metadata(name="drive-b"), spec=DriveSpec())],
            meta=PaginationMeta(has_more=False),
        ),
    ]
    calls = []

    def fake_list_drives(*, client, cursor=UNSET, limit=50):
        calls.append((cursor, limit))
        return pages.pop(0)

    monkeypatch.setattr("blaxel.core.drive.drive.list_drives_sync", fake_list_drives)

    page = SyncDriveInstance.list(limit=1)
    next_page = page.next_page()

    assert [drive.name for drive in page.data] == ["drive-a"]
    assert page.has_more is True
    assert page.next_cursor == "cursor-2"
    assert [drive.name for drive in next_page.data] == ["drive-b"]
    assert next_page.has_more is False
    assert calls == [(UNSET, 1), ("cursor-2", 1)]


def test_job_execution_list_supports_explicit_next_page(monkeypatch):
    first_execution = JobExecution(
        metadata=JobExecutionMetadata(id="execution-a"),
        spec=JobExecutionSpec(),
    )
    second_execution = JobExecution(
        metadata=JobExecutionMetadata(id="execution-b"),
        spec=JobExecutionSpec(),
    )
    pages = [
        JobExecutionList(
            data=[first_execution],
            meta=PaginationMeta(has_more=True, next_cursor="cursor-2"),
        ),
        JobExecutionList(
            data=[second_execution],
            meta=PaginationMeta(has_more=False),
        ),
    ]
    calls = []

    def fake_list_job_executions(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            status_code=200,
            parsed=pages.pop(0),
        )

    monkeypatch.setattr(
        "blaxel.core.jobs.list_job_executions.sync_detailed",
        fake_list_job_executions,
    )

    executions = bl_job("job-a").list_executions(limit=10, cursor="cursor-1")
    next_executions = executions.next_page()

    assert executions.data == [first_execution]
    assert executions.has_more is True
    assert executions.next_cursor == "cursor-2"
    assert next_executions.data == [second_execution]
    assert next_executions.has_more is False
    assert calls[0]["job_id"] == "job-a"
    assert calls[0]["limit"] == 10
    assert calls[0]["cursor"] == "cursor-1"
    assert calls[1]["cursor"] == "cursor-2"


def test_job_execution_auto_paging_iter_is_explicit(monkeypatch):
    first_execution = JobExecution(
        metadata=JobExecutionMetadata(id="execution-a"),
        spec=JobExecutionSpec(),
    )
    second_execution = JobExecution(
        metadata=JobExecutionMetadata(id="execution-b"),
        spec=JobExecutionSpec(),
    )
    pages = [
        JobExecutionList(
            data=[first_execution],
            meta=PaginationMeta(has_more=True, next_cursor="cursor-2"),
        ),
        JobExecutionList(
            data=[second_execution],
            meta=PaginationMeta(has_more=False),
        ),
    ]

    def fake_list_job_executions(**kwargs):
        return SimpleNamespace(
            status_code=200,
            parsed=pages.pop(0),
        )

    monkeypatch.setattr(
        "blaxel.core.jobs.list_job_executions.sync_detailed",
        fake_list_job_executions,
    )

    executions = list(bl_job("job-a").list_executions(limit=10).auto_paging_iter())

    assert executions == [first_execution, second_execution]
