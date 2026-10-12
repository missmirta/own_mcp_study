"""MCP-сервер для конспекту з Notion.

Нотатки читаються з папки з Markdown-експортом Notion. Шлях до неї задає
змінна середовища NOTES_DIR (за замовчуванням папка notes/ поруч із сервером).
"""

import os
from pathlib import Path

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel

import notes

NOTES_DIR = Path(os.environ.get("NOTES_DIR", Path(__file__).parent / "notes"))

mcp = MCPServer("notes")


class NoteInfo(BaseModel):
    id: str
    title: str


class SearchHit(BaseModel):
    note_id: str
    line: int
    text: str


def _notes() -> dict[str, notes.Note]:
    # Читаємо папку на кожен виклик: свіжий експорт підхоплюється без перезапуску.
    if not NOTES_DIR.is_dir():
        raise ToolError(f"Папку з нотатками не знайдено: {NOTES_DIR}. Вкажи її в NOTES_DIR.")
    return notes.load_notes(NOTES_DIR)


@mcp.tool()
def ping(message: str = "ping") -> str:
    """Перевірка зв'язку: повертає повідомлення назад з позначкою сервера."""
    return f"notes-mcp отримав: {message}"


@mcp.tool()
def list_notes() -> list[NoteInfo]:
    """Список усіх нотаток конспекту: id (для read_note) і заголовок."""
    return [NoteInfo(id=n.id, title=n.title) for n in _notes().values()]


@mcp.tool()
def read_note(note_id: str) -> str:
    """Повний текст нотатки в Markdown. note_id береться з list_notes або search_notes."""
    all_notes = _notes()
    if note_id not in all_notes:
        raise ToolError(f"Нотатки «{note_id}» немає. Доступні: {', '.join(all_notes)}")
    return all_notes[note_id].read()


@mcp.tool()
def search_notes(query: str, limit: int = 20) -> list[SearchHit]:
    """Шукає текст у всіх нотатках (без урахування регістру) і повертає рядки зі збігами."""
    return [SearchHit(note_id=m.note_id, line=m.line, text=m.text) for m in notes.search(_notes(), query, limit)]


def main() -> None:
    # stdio: клієнт (Claude Desktop, Inspector) запускає сервер як процес
    # і спілкується з ним через stdin/stdout.
    mcp.run()


if __name__ == "__main__":
    main()
