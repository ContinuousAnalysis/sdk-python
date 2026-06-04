from http import HTTPStatus
from typing import Any, Union

import httpx

from ... import errors
from ...client import Client
from ...models.error import Error
from ...models.volume import Volume
from ...types import Response


def _get_kwargs(
    *,
    body: Volume,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/volumes",
    }

    if type(body) is dict:
        _body = body
    else:
        _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: Client, response: httpx.Response) -> Union[Error, Volume] | None:
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
        response_200 = Volume.from_dict(_response_content)

        return response_200
    if response.status_code == 400:
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
        response_400 = Error.from_dict(_response_content)

        return response_400
    if response.status_code == 401:
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
        response_401 = Error.from_dict(_response_content)

        return response_401
    if response.status_code == 403:
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
        response_403 = Error.from_dict(_response_content)

        return response_403
    if response.status_code == 409:
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
        response_409 = Error.from_dict(_response_content)

        return response_409
    if response.status_code == 500:
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
        response_500 = Error.from_dict(_response_content)

        return response_500
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: Client, response: httpx.Response) -> Response[Union[Error, Volume]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Client,
    body: Volume,
) -> Response[Union[Error, Volume]]:
    """Create persistent volume

     Creates a new persistent storage volume that can be attached to sandboxes. Volumes must be created
    in a specific region and can only attach to sandboxes in the same region.

    Args:
        body (Volume): Persistent storage volume that can be attached to sandboxes for durable
            file storage across sessions. Volumes survive sandbox deletion and can be reattached to
            new sandboxes.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        errors.ResponseParseError: If a documented response body cannot be parsed and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Error, Volume]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Client,
    body: Volume,
) -> Union[Error, Volume] | None:
    """Create persistent volume

     Creates a new persistent storage volume that can be attached to sandboxes. Volumes must be created
    in a specific region and can only attach to sandboxes in the same region.

    Args:
        body (Volume): Persistent storage volume that can be attached to sandboxes for durable
            file storage across sessions. Volumes survive sandbox deletion and can be reattached to
            new sandboxes.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        errors.ResponseParseError: If a documented response body cannot be parsed and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Error, Volume]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Client,
    body: Volume,
) -> Response[Union[Error, Volume]]:
    """Create persistent volume

     Creates a new persistent storage volume that can be attached to sandboxes. Volumes must be created
    in a specific region and can only attach to sandboxes in the same region.

    Args:
        body (Volume): Persistent storage volume that can be attached to sandboxes for durable
            file storage across sessions. Volumes survive sandbox deletion and can be reattached to
            new sandboxes.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        errors.ResponseParseError: If a documented response body cannot be parsed and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Error, Volume]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Client,
    body: Volume,
) -> Union[Error, Volume] | None:
    """Create persistent volume

     Creates a new persistent storage volume that can be attached to sandboxes. Volumes must be created
    in a specific region and can only attach to sandboxes in the same region.

    Args:
        body (Volume): Persistent storage volume that can be attached to sandboxes for durable
            file storage across sessions. Volumes survive sandbox deletion and can be reattached to
            new sandboxes.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        errors.ResponseParseError: If a documented response body cannot be parsed and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Error, Volume]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
