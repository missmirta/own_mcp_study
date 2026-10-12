import httpx
import pytest
from mcp import Client

import server
from notion import NotionSource, parse_page_id

ROOT = "11111111111111111111111111111111"
SUB = "22222222222222222222222222222222"
LINKED = "33333333333333333333333333333333"


def text(content, **annotations):
    return [{"plain_text": content, "annotations": annotations, "href": None}]


def block(kind, has_children=False, id="b", **data):
    return {"id": id, "type": kind, "has_children": has_children, kind: data}


PAGES = {
    ROOT: {"properties": {"title": {"type": "title", "title": text("Machine Learning")}}},
    SUB: {"properties": {"Name": {"type": "title", "title": text("PyTorch")}}},
    LINKED: {"properties": {"title": {"type": "title", "title": text("NLP")}}},
}

CHILDREN = {
    ROOT: [
        block("heading_2", rich_text=text("Процесори")),
        block("paragraph", rich_text=text("CUDA", bold=True) + text(" від NVIDIA")),
        block("bulleted_list_item", has_children=True, id="list", rich_text=text("GPU")),
        block("numbered_list_item", rich_text=text("перший")),
        block("numbered_list_item", rich_text=text("другий")),
        block("table", has_children=True, id="table", table_width=2),
        block("child_page", id=SUB, title="PyTorch"),
        block("link_to_page", type="page_id", page_id=LINKED),
        block("image", type="external"),
    ],
    "list": [block("bulleted_list_item", rich_text=text("Tensor Cores"))],
    "table": [
        block("table_row", cells=[text("Процесор"), text("Сила")]),
        block("table_row", cells=[text("TPU"), text("матриці")]),
    ],
    SUB: [block("code", rich_text=text("x = torch.ones(2)"), language="python")],
    LINKED: [block("paragraph", rich_text=text("Токенізація"))],
}


def fake_notion(calls):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        assert request.headers["Authorization"] == "Bearer secret"
        parts = request.url.path.removeprefix("/v1/").split("/")
        if parts[0] == "pages" and parts[1] in PAGES:
            return httpx.Response(200, json=PAGES[parts[1]])
        if parts[0] == "blocks" and parts[1] in CHILDREN:
            return httpx.Response(200, json={"results": CHILDREN[parts[1]], "has_more": False})
        return httpx.Response(404, json={})

    return httpx.Client(base_url="https://api.notion.com/v1", transport=httpx.MockTransport(handler))


@pytest.fixture
def calls():
    return []


@pytest.fixture
def source(calls):
    return NotionSource("secret", f"https://www.notion.so/Machine-Learning-{ROOT}?pvs=4", client=fake_notion(calls))


def test_parse_page_id_accepts_urls_and_dashed_ids():
    assert parse_page_id(f"https://www.notion.so/My-Page-{ROOT}?v=1") == ROOT
    assert parse_page_id("11111111-1111-1111-1111-111111111111") == ROOT
    with pytest.raises(ValueError):
        parse_page_id("https://www.notion.so/no-id")


def test_page_tree_becomes_notes(source):
    notes = source.load()
    assert list(notes) == ["Machine Learning", "Machine Learning/NLP", "Machine Learning/PyTorch"]
    assert notes["Machine Learning/PyTorch"].text == "# PyTorch\n\n```python\nx = torch.ones(2)\n```\n"


def test_blocks_become_markdown(source):
    assert source.load()["Machine Learning"].text == (
        "# Machine Learning\n\n"
        "### Процесори\n\n"
        "**CUDA** від NVIDIA\n\n"
        "- GPU\n\n"
        "  - Tensor Cores\n\n"
        "1. перший\n\n"
        "2. другий\n\n"
        "| Процесор | Сила |\n| --- | --- |\n| TPU | матриці |\n\n"
        "📄 PyTorch\n"
    )


def test_results_are_cached(source, calls):
    source.load()
    count = len(calls)
    source.load()
    assert len(calls) == count


def test_missing_access_is_a_clear_error(calls):
    source = NotionSource("secret", "44444444444444444444444444444444", client=fake_notion(calls))
    with pytest.raises(PermissionError, match="Connections"):
        source.load()


@pytest.mark.anyio
async def test_server_tools_use_notion(monkeypatch, source):
    monkeypatch.setattr(server, "NOTION", source)
    async with Client(server.mcp) as client:
        hits = await client.call_tool("search_notes", {"query": "токен"})
        resources = await client.list_resources()
    assert hits.structured_content == {"result": [{"note_id": "Machine Learning/NLP", "line": 3, "text": "Токенізація"}]}
    assert len(resources.resources) == 3
