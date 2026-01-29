"""Specifies the parameter for the httpx download."""

from httpx import AsyncClient, BasicAuth, Response, Timeout


async def get_calendar(
    client: AsyncClient,
    url: str,
    username: str | None = None,
    password: str | None = None,
) -> Response:
    """Make an HTTP GET request using Home Assistant's async HTTPX client with timeout."""
    auth = BasicAuth(username, password) if username and password else None

    return await client.get(
        url,
        auth=auth,
        follow_redirects=True,
        timeout=Timeout(5, read=30, write=5, pool=5),
    )
