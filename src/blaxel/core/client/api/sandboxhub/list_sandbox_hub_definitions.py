from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import Client
from ...models.sandbox_definition import SandboxDefinition
from ...types import Response


def _get_kwargs() -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/sandbox/hub",
    }

    return _kwargs


def _parse_response(
    *, client: Client, response: httpx.Response
) -> list["SandboxDefinition"] | None:
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
        response_200 = []
        _response_200 = _response_content
        for response_200_item_data in _response_200:
            response_200_item = SandboxDefinition.from_dict(response_200_item_data)

            response_200.append(response_200_item)

        return response_200
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Client, response: httpx.Response
) -> Response[list["SandboxDefinition"]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Client,
) -> Response[list["SandboxDefinition"]]:
    """List Sandbox Hub templates

     Returns all pre-built sandbox templates available in the Blaxel Hub. These include popular
    development environments with pre-installed tools and frameworks.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        errors.ResponseParseError: If a documented response body cannot be parsed and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[list['SandboxDefinition']]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Client,
) -> list["SandboxDefinition"] | None:
    """List Sandbox Hub templates

     Returns all pre-built sandbox templates available in the Blaxel Hub. These include popular
    development environments with pre-installed tools and frameworks.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        errors.ResponseParseError: If a documented response body cannot be parsed and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        list['SandboxDefinition']
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: Client,
) -> Response[list["SandboxDefinition"]]:
    """List Sandbox Hub templates

     Returns all pre-built sandbox templates available in the Blaxel Hub. These include popular
    development environments with pre-installed tools and frameworks.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        errors.ResponseParseError: If a documented response body cannot be parsed and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[list['SandboxDefinition']]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Client,
) -> list["SandboxDefinition"] | None:
    """List Sandbox Hub templates

     Returns all pre-built sandbox templates available in the Blaxel Hub. These include popular
    development environments with pre-installed tools and frameworks.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        errors.ResponseParseError: If a documented response body cannot be parsed and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        list['SandboxDefinition']
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
