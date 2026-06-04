from http import HTTPStatus
from typing import Any, Union, cast

import httpx

from ... import errors
from ...client import Client
from ...models.drive_list import DriveList
from ...models.list_drives_anchor import ListDrivesAnchor
from ...models.list_drives_sort import ListDrivesSort
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    cursor: Union[Unset, str] = UNSET,
    limit: Union[Unset, int] = 50,
    sort: Union[Unset, ListDrivesSort] = UNSET,
    q: Union[Unset, str] = UNSET,
    anchor: Union[Unset, ListDrivesAnchor] = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["cursor"] = cursor

    params["limit"] = limit

    json_sort: Union[Unset, str] = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort.value

    params["sort"] = json_sort

    params["q"] = q

    json_anchor: Union[Unset, str] = UNSET
    if not isinstance(anchor, Unset):
        json_anchor = anchor.value

    params["anchor"] = json_anchor

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/drives",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Client, response: httpx.Response
) -> Union[list[Any], Any, DriveList] | None:
    if response.status_code == 200:
        try:
            _response_content = response.json()
        except ValueError as exc:
            if client.raise_on_unexpected_status:
                raise errors.ResponseParseError(
                    response.status_code,
                    response.content,
                    response.headers.get("Content-Type"),
                ) from exc
            return None
        response_200 = DriveList.from_dict(_response_content)

        if isinstance(_response_content, list):
            if response_200 is None:
                return []
            if response_200.data is UNSET or response_200.data is None:
                return []
            return cast(list[Any], response_200.data)
        return response_200
    if response.status_code == 401:
        response_401 = cast(Any, None)
        return response_401
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Client, response: httpx.Response
) -> Response[Union[list[Any], Any, DriveList]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Client,
    cursor: Union[Unset, str] = UNSET,
    limit: Union[Unset, int] = 50,
    sort: Union[Unset, ListDrivesSort] = UNSET,
    q: Union[Unset, str] = UNSET,
    anchor: Union[Unset, ListDrivesAnchor] = UNSET,
) -> Response[Union[list[Any], Any, DriveList]]:
    """List drives

     Returns all drives in the workspace. Drives provide persistent storage that can be attached to
    agents, functions, and sandboxes. Starting with API version 2026-04-28, the response wraps items in
    `{data, meta}` and supports cursor pagination via the `cursor` and `limit` query parameters; older
    versions keep returning a bare array with all drives.

    Args:
        cursor (Union[Unset, str]):
        limit (Union[Unset, int]):  Default: 50.
        sort (Union[Unset, ListDrivesSort]):
        q (Union[Unset, str]):
        anchor (Union[Unset, ListDrivesAnchor]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        errors.ResponseParseError: If a documented response body cannot be parsed and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[list[Any], Any, DriveList]]
    """

    kwargs = _get_kwargs(
        cursor=cursor,
        limit=limit,
        sort=sort,
        q=q,
        anchor=anchor,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Client,
    cursor: Union[Unset, str] = UNSET,
    limit: Union[Unset, int] = 50,
    sort: Union[Unset, ListDrivesSort] = UNSET,
    q: Union[Unset, str] = UNSET,
    anchor: Union[Unset, ListDrivesAnchor] = UNSET,
) -> Union[list[Any], Any, DriveList] | None:
    """List drives

     Returns all drives in the workspace. Drives provide persistent storage that can be attached to
    agents, functions, and sandboxes. Starting with API version 2026-04-28, the response wraps items in
    `{data, meta}` and supports cursor pagination via the `cursor` and `limit` query parameters; older
    versions keep returning a bare array with all drives.

    Args:
        cursor (Union[Unset, str]):
        limit (Union[Unset, int]):  Default: 50.
        sort (Union[Unset, ListDrivesSort]):
        q (Union[Unset, str]):
        anchor (Union[Unset, ListDrivesAnchor]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        errors.ResponseParseError: If a documented response body cannot be parsed and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[list[Any], Any, DriveList]
    """

    return sync_detailed(
        client=client,
        cursor=cursor,
        limit=limit,
        sort=sort,
        q=q,
        anchor=anchor,
    ).parsed


async def asyncio_detailed(
    *,
    client: Client,
    cursor: Union[Unset, str] = UNSET,
    limit: Union[Unset, int] = 50,
    sort: Union[Unset, ListDrivesSort] = UNSET,
    q: Union[Unset, str] = UNSET,
    anchor: Union[Unset, ListDrivesAnchor] = UNSET,
) -> Response[Union[list[Any], Any, DriveList]]:
    """List drives

     Returns all drives in the workspace. Drives provide persistent storage that can be attached to
    agents, functions, and sandboxes. Starting with API version 2026-04-28, the response wraps items in
    `{data, meta}` and supports cursor pagination via the `cursor` and `limit` query parameters; older
    versions keep returning a bare array with all drives.

    Args:
        cursor (Union[Unset, str]):
        limit (Union[Unset, int]):  Default: 50.
        sort (Union[Unset, ListDrivesSort]):
        q (Union[Unset, str]):
        anchor (Union[Unset, ListDrivesAnchor]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        errors.ResponseParseError: If a documented response body cannot be parsed and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[list[Any], Any, DriveList]]
    """

    kwargs = _get_kwargs(
        cursor=cursor,
        limit=limit,
        sort=sort,
        q=q,
        anchor=anchor,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Client,
    cursor: Union[Unset, str] = UNSET,
    limit: Union[Unset, int] = 50,
    sort: Union[Unset, ListDrivesSort] = UNSET,
    q: Union[Unset, str] = UNSET,
    anchor: Union[Unset, ListDrivesAnchor] = UNSET,
) -> Union[list[Any], Any, DriveList] | None:
    """List drives

     Returns all drives in the workspace. Drives provide persistent storage that can be attached to
    agents, functions, and sandboxes. Starting with API version 2026-04-28, the response wraps items in
    `{data, meta}` and supports cursor pagination via the `cursor` and `limit` query parameters; older
    versions keep returning a bare array with all drives.

    Args:
        cursor (Union[Unset, str]):
        limit (Union[Unset, int]):  Default: 50.
        sort (Union[Unset, ListDrivesSort]):
        q (Union[Unset, str]):
        anchor (Union[Unset, ListDrivesAnchor]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        errors.ResponseParseError: If a documented response body cannot be parsed and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[list[Any], Any, DriveList]
    """

    return (
        await asyncio_detailed(
            client=client,
            cursor=cursor,
            limit=limit,
            sort=sort,
            q=q,
            anchor=anchor,
        )
    ).parsed
