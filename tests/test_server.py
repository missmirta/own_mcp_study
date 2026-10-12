import pytest
from mcp import Client

from server import mcp


@pytest.mark.anyio
async def test_ping_tool_is_listed():
    async with Client(mcp) as client:
        tools = await client.list_tools()
    assert [t.name for t in tools.tools] == ["ping"]


@pytest.mark.anyio
async def test_ping_echoes_message():
    async with Client(mcp) as client:
        result = await client.call_tool("ping", {"message": "привіт"})
    assert result.content[0].text == "notes-mcp отримав: привіт"
