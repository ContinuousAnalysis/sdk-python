from http import HTTPStatus
from types import SimpleNamespace

import httpx
import pytest

import blaxel.core.jobs as job_module
from blaxel.core.client import errors
from blaxel.core.client.api.agents import list_agents
from blaxel.core.client.api.compute import create_sandbox, list_sandboxes
from blaxel.core.client.client import Client
from blaxel.core.client.models.agent_list import AgentList
from blaxel.core.client.models.job_execution_list import JobExecutionList
from blaxel.core.client.models.sandbox_error import SandboxError
from blaxel.core.client.models.sandbox_list import SandboxList
from blaxel.core.client.types import Unset
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


def agent_payload(name: str) -> dict:
    return {
        "metadata": {"name": name},
        "spec": {},
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
    parsed = SandboxList.from_dict(payload)

    assert parsed is not None
    assert not isinstance(parsed.data, Unset)
    assert isinstance(parsed, SandboxList)
    assert [sandbox.metadata.name for sandbox in parsed.data] == expected_names


@pytest.mark.parametrize(
    ("parser", "payload", "request_url", "expected_names"),
    [
        (
            list_agents._parse_response,
            [agent_payload("legacy-agent")],
            "https://api.blaxel.test/v0/agents",
            ["legacy-agent"],
        ),
        (
            list_sandboxes._parse_response,
            [sandbox_payload("legacy-sandbox")],
            "https://api.blaxel.test/v0/sandboxes",
            ["legacy-sandbox"],
        ),
        (
            list_sandboxes._parse_response,
            [],
            "https://api.blaxel.test/v0/sandboxes",
            [],
        ),
    ],
)
def test_generated_list_endpoint_preserves_legacy_bare_array_return(
    parser,
    payload,
    request_url,
    expected_names,
):
    client = Client(base_url="https://api.blaxel.test", raise_on_unexpected_status=True)

    parsed = parser(
        client=client,
        response=httpx.Response(
            200,
            json=payload,
            request=httpx.Request("GET", request_url),
        ),
    )

    assert isinstance(parsed, list)
    assert [item.metadata.name for item in parsed] == expected_names


def test_generated_list_endpoint_returns_wrapper_for_paginated_response():
    client = Client(base_url="https://api.blaxel.test", raise_on_unexpected_status=True)

    parsed = list_agents._parse_response(
        client=client,
        response=httpx.Response(
            200,
            json={
                "data": [agent_payload("wrapped-agent")],
                "meta": {
                    "hasMore": False,
                    "nextCursor": "",
                    "total": 1,
                },
            },
            request=httpx.Request("GET", "https://api.blaxel.test/v0/agents"),
        ),
    )

    assert isinstance(parsed, AgentList)
    assert not isinstance(parsed.data, Unset)
    assert not isinstance(parsed.meta, Unset)
    assert parsed.data[0].metadata.name == "wrapped-agent"
    assert parsed.meta.has_more is False


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


@pytest.mark.asyncio
async def test_sandbox_instance_list_preserves_legacy_bare_array_response(monkeypatch):
    async def fake_list_sandboxes(*, client):
        response = SandboxList.from_dict([sandbox_payload("legacy-list-shape")])
        assert response is not None
        assert not isinstance(response.data, Unset)
        return response.data

    monkeypatch.setattr(sandbox_module, "list_sandboxes", fake_list_sandboxes)

    sandboxes = await sandbox_module.SandboxInstance.list()

    assert len(sandboxes) == 1
    assert sandboxes[0].metadata.name == "legacy-list-shape"


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


def test_job_list_executions_preserves_legacy_bare_array_response(monkeypatch):
    def fake_list_job_executions(*, job_id, client, limit, offset):
        assert job_id == "mk3"
        assert limit == 20
        assert offset == 0
        response = JobExecutionList.from_dict([])
        assert response is not None
        assert not isinstance(response.data, Unset)
        return SimpleNamespace(
            status_code=HTTPStatus.OK,
            parsed=response.data,
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


def test_documented_success_html_body_raises_sdk_parse_error():
    client = Client(base_url="https://api.blaxel.test", raise_on_unexpected_status=True)
    html = b"<html>edge error page on a 200</html>"

    with pytest.raises(errors.ResponseParseError) as exc_info:
        create_sandbox._parse_response(
            client=client,
            response=response(200, html, "text/html"),
        )

    assert exc_info.value.status_code == 200


def test_documented_success_html_body_returns_none_when_raises_disabled():
    client = Client(base_url="https://api.blaxel.test", raise_on_unexpected_status=False)

    parsed = create_sandbox._parse_response(
        client=client,
        response=response(200, b"<html>edge error page on a 200</html>", "text/html"),
    )

    assert parsed is None
