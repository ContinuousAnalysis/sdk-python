"""Tests for unwrapping paginated list responses across wrapper list() paths."""

from unittest.mock import patch

from blaxel.core.client.models.drive_list import DriveList
from blaxel.core.client.models.job_execution import JobExecution
from blaxel.core.client.models.job_execution_list import JobExecutionList
from blaxel.core.client.types import UNSET
from blaxel.core.common.internal import list_response_items
from blaxel.core.jobs import BlJob


class TestListResponseItems:
    def test_unwraps_paginated_model(self):
        model = DriveList(data=[{"metadata": {"name": "d1"}, "spec": {}}])
        assert list_response_items(model) == [{"metadata": {"name": "d1"}, "spec": {}}]

    def test_passes_through_bare_list(self):
        items = [{"metadata": {"name": "d1"}, "spec": {}}]
        assert list_response_items(items) == items

    def test_none_response_returns_empty(self):
        assert list_response_items(None) == []

    def test_unset_data_returns_empty(self):
        model = DriveList()
        model.data = UNSET
        assert list_response_items(model) == []


class TestListModelFromDict:
    def test_from_dict_accepts_bare_array(self):
        parsed = DriveList.from_dict([{"metadata": {"name": "d1"}, "spec": {}}])
        assert len(parsed.data) == 1
        assert parsed.data[0].metadata.name == "d1"

    def test_from_dict_accepts_paginated_object(self):
        parsed = DriveList.from_dict({"data": [{"metadata": {"name": "d1"}, "spec": {}}]})
        assert len(parsed.data) == 1
        assert parsed.data[0].metadata.name == "d1"

    def test_from_dict_empty_dict_yields_no_items(self):
        parsed = DriveList.from_dict({})
        assert list_response_items(parsed) == []


class _FakeResponse:
    def __init__(self, status_code, parsed):
        self.status_code = status_code
        self.parsed = parsed


class TestJobListExecutions:
    def test_list_executions_unwraps_paginated_model(self):
        executions = JobExecutionList(
            data=[JobExecution.from_dict({"metadata": {"name": "e1"}, "spec": {}})]
        )
        with patch(
            "blaxel.core.jobs.list_job_executions.sync_detailed",
            return_value=_FakeResponse(200, executions),
        ):
            result = BlJob("my-job").list_executions()
        assert len(result) == 1
        assert isinstance(result[0], JobExecution)

    def test_list_executions_handles_none_parsed(self):
        with patch(
            "blaxel.core.jobs.list_job_executions.sync_detailed",
            return_value=_FakeResponse(200, None),
        ):
            assert BlJob("my-job").list_executions() == []
