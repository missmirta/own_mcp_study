from pathlib import Path

import pytest
from mcp import Client

import server

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def notes_dir(monkeypatch):
    monkeypatch.setattr(server, "NOTES_DIR", FIXTURES)
    monkeypatch.setattr(server, "NOTION", None)


@pytest.mark.anyio
async def test_tools_are_listed():
    async with Client(server.mcp) as client:
        tools = await client.list_tools()
    assert sorted(t.name for t in tools.tools) == ["list_notes", "ping", "read_note", "search_notes"]


@pytest.mark.anyio
async def test_ping_echoes_message():
    async with Client(server.mcp) as client:
        result = await client.call_tool("ping", {"message": "hello"})
    assert result.content[0].text == "notes-mcp received: hello"


@pytest.mark.anyio
async def test_list_notes_strips_notion_ids():
    async with Client(server.mcp) as client:
        result = await client.call_tool("list_notes", {})
    assert result.structured_content == {
        "result": [
            {"id": "Course", "title": "Course"},
            {"id": "Course/PyTorch", "title": "PyTorch"},
        ]
    }


@pytest.mark.anyio
async def test_read_note():
    async with Client(server.mcp) as client:
        result = await client.call_tool("read_note", {"note_id": "Course/PyTorch"})
    assert "Tensors are like NumPy arrays" in result.content[0].text


@pytest.mark.anyio
async def test_read_unknown_note_is_error():
    async with Client(server.mcp) as client:
        result = await client.call_tool("read_note", {"note_id": "Missing"})
    assert result.is_error
    assert "Course/PyTorch" in result.content[0].text


@pytest.mark.anyio
async def test_search_is_case_insensitive():
    async with Client(server.mcp) as client:
        result = await client.call_tool("search_notes", {"query": "gpu"})
    assert result.structured_content == {
        "result": [{"note_id": "Course/PyTorch", "line": 3, "text": "Tensors are like NumPy arrays, but they run on the GPU."}]
    }


@pytest.mark.anyio
async def test_missing_notes_dir_is_error(monkeypatch):
    monkeypatch.setattr(server, "NOTES_DIR", FIXTURES / "missing")
    async with Client(server.mcp) as client:
        result = await client.call_tool("list_notes", {})
    assert result.is_error
    assert "NOTES_DIR" in result.content[0].text


@pytest.mark.anyio
async def test_each_note_is_a_listed_resource():
    async with Client(server.mcp) as client:
        resources = await client.list_resources()
    assert [(str(r.uri), r.title) for r in resources.resources] == [
        ("note:///Course", "Course"),
        ("note:///Course/PyTorch", "PyTorch"),
    ]


@pytest.mark.anyio
async def test_read_note_resource():
    async with Client(server.mcp) as client:
        result = await client.read_resource(server.note_uri("Course/PyTorch"))
    assert "Tensors are like NumPy arrays" in result.contents[0].text


@pytest.mark.anyio
async def test_quiz_prompt_includes_matching_notes():
    async with Client(server.mcp) as client:
        result = await client.get_prompt("quiz", {"topic": "GPU", "questions": "3"})
    text = result.messages[0].content.text
    assert "quiz of 3 questions" in text
    assert "--- Course/PyTorch ---" in text
    assert "--- Course ---" not in text


@pytest.mark.anyio
async def test_quiz_prompt_without_matches_suggests_topics():
    async with Client(server.mcp) as client:
        result = await client.get_prompt("quiz", {"topic": "quantum computers"})
    assert "nothing about" in result.messages[0].content.text
