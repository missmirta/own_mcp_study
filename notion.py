"""Читання конспекту напряму з Notion API.

Беремо кореневу сторінку, обходимо її блоки і перетворюємо їх на Markdown.
Кожна підсторінка (child_page або link_to_page) стає окремою нотаткою з id
«Батьківська/Підсторінка», як і в експорті.
"""

import re
import time

import httpx

from notes import Note

API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
PAGE_ID = re.compile(r"([0-9a-f]{32})|([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")


def parse_page_id(value: str) -> str:
    """Дістає id сторінки з посилання на Notion або з самого id."""
    match = PAGE_ID.search(value.split("?")[0].lower())
    if not match:
        raise ValueError(f"Не бачу id сторінки Notion у «{value}»")
    return match.group(0).replace("-", "")


def rich_text(parts: list[dict]) -> str:
    out = []
    for part in parts:
        text = part.get("plain_text", "")
        ann = part.get("annotations", {})
        if ann.get("code"):
            text = f"`{text}`"
        if ann.get("bold"):
            text = f"**{text}**"
        if ann.get("italic"):
            text = f"*{text}*"
        if ann.get("strikethrough"):
            text = f"~~{text}~~"
        if part.get("href"):
            text = f"[{text}]({part['href']})"
        out.append(text)
    return "".join(out)


class NotionSource:
    """Завантажує дерево сторінок і тримає його в кеші ttl секунд.

    Інструменти викликаються часто (search читає все), а Notion API повільний
    і має ліміт ~3 запити на секунду, тож без кешу кожне питання чекало б.
    """

    def __init__(self, token: str, root: str, ttl: float = 60, client: httpx.Client | None = None):
        self.root = parse_page_id(root)
        self.ttl = ttl
        self.client = client or httpx.Client(base_url=API, timeout=30)
        self.client.headers.update({"Authorization": f"Bearer {token}", "Notion-Version": NOTION_VERSION})
        self._cache: dict[str, Note] | None = None
        self._loaded_at = 0.0

    def load(self) -> dict[str, Note]:
        if self._cache is None or time.monotonic() - self._loaded_at > self.ttl:
            notes: dict[str, Note] = {}
            self._load_page(self.root, None, notes, set())
            self._cache = dict(sorted(notes.items()))
            self._loaded_at = time.monotonic()
        return self._cache

    def _get(self, path: str, **params) -> dict:
        response = self.client.get(path, params=params)
        if response.status_code in (401, 403, 404):
            raise PermissionError(
                f"Notion повернув {response.status_code} для {path}. Перевір NOTION_TOKEN і що сторінку "
                "підключено до інтеграції (⋯ → Connections)."
            )
        response.raise_for_status()
        return response.json()

    def _children(self, block_id: str) -> list[dict]:
        blocks, cursor = [], None
        while True:
            params = {"page_size": 100} | ({"start_cursor": cursor} if cursor else {})
            data = self._get(f"/blocks/{block_id}/children", **params)
            blocks += data["results"]
            if not data.get("has_more"):
                return blocks
            cursor = data["next_cursor"]

    def _page_title(self, page_id: str) -> str:
        page = self._get(f"/pages/{page_id}")
        for prop in page.get("properties", {}).values():
            if prop.get("type") == "title":
                return rich_text(prop["title"]) or "Без назви"
        return "Без назви"

    def _load_page(self, page_id: str, parent: str | None, notes: dict[str, Note], seen: set[str]) -> None:
        seen.add(page_id)
        title = self._page_title(page_id)
        note_id = f"{parent}/{title}" if parent else title
        subpages: list[str] = []
        body = self._blocks_to_md(self._children(page_id), subpages, seen, depth=0)
        notes[note_id] = Note(note_id, title, f"# {title}\n\n{body}".rstrip() + "\n")
        for sub in subpages:
            if sub not in seen:
                self._load_page(sub, note_id, notes, seen)

    def _blocks_to_md(self, blocks: list[dict], subpages: list[str], seen: set[str], depth: int) -> str:
        lines: list[str] = []
        indent = "  " * depth
        number = 0
        for block in blocks:
            kind = block["type"]
            data = block.get(kind, {})
            text = rich_text(data.get("rich_text", []))
            number = number + 1 if kind == "numbered_list_item" else 0

            if kind == "paragraph":
                line = text
            elif kind in ("heading_1", "heading_2", "heading_3"):
                line = "#" * (int(kind[-1]) + 1) + " " + text
            elif kind == "bulleted_list_item":
                line = f"- {text}"
            elif kind == "numbered_list_item":
                line = f"{number}. {text}"
            elif kind == "to_do":
                line = f"- [{'x' if data.get('checked') else ' '}] {text}"
            elif kind == "toggle":
                line = f"- {text}"
            elif kind in ("quote", "callout"):
                line = f"> {text}"
            elif kind == "code":
                line = f"```{data.get('language', '')}\n{text}\n```"
            elif kind == "equation":
                line = f"$$ {data.get('expression', '')} $$"
            elif kind == "divider":
                line = "---"
            elif kind == "table_row":
                line = "| " + " | ".join(rich_text(cell) for cell in data.get("cells", [])) + " |"
            elif kind == "child_page":
                subpages.append(block["id"].replace("-", ""))
                line = f"📄 {data.get('title', '')}"
            elif kind == "link_to_page" and data.get("type") == "page_id":
                subpages.append(data["page_id"].replace("-", ""))
                line = ""
            elif kind in ("bookmark", "embed", "link_preview"):
                line = data.get("url", "")
            else:
                line = ""  # зображення, бази даних тощо поки пропускаємо

            if line:
                lines.append(indent + line)
            if block.get("has_children") and kind not in ("child_page", "child_database"):
                child_depth = depth if kind == "table" else depth + 1
                child_md = self._blocks_to_md(self._children(block["id"]), subpages, seen, child_depth)
                if kind == "table" and child_md:
                    rows = child_md.split("\n\n")
                    width = rows[0].count("|") - 1
                    rows.insert(1, indent + "|" + " --- |" * width)
                    child_md = "\n".join(rows)
                if child_md:
                    lines.append(child_md)
        return "\n\n".join(lines)
