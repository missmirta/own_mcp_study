# own_mcp_study

Власний MCP-сервер для конспекту з Notion. Пишемо його крок за кроком, щоб вивчити Model Context Protocol.

## План

1. **Скелет сервера** з одним інструментом `ping`, перевірка в MCP Inspector і Claude Desktop. ← зараз тут
2. **Конспект як дані**: Markdown-експорт з Notion та інструменти `list_notes`, `read_note`, `search_notes`.
3. **Решта протоколу**: resource для кожної нотатки та prompt «зроби квіз за темою».
4. **Живий Notion**: читання через Notion API замість експорту.

## Запуск

Потрібен [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/missmirta/own_mcp_study
cd own_mcp_study
uv sync
uv run pytest        # тести
```

### Перевірка в MCP Inspector

Inspector показує, які інструменти бачить клієнт, і дає викликати їх вручну (потрібен Node.js):

```bash
npx @modelcontextprotocol/inspector uv run server.py
```

У вікні, що відкриється, натисни **Connect**, потім **Tools → List Tools → ping → Run Tool**.

### Підключення до Claude Desktop

Відкрий **Settings → Developer → Edit Config** і додай сервер у `claude_desktop_config.json`
(шлях заміни на свій, на Windows через `\\`):

```json
{
  "mcpServers": {
    "notes": {
      "command": "uv",
      "args": ["run", "--directory", "/ПОВНИЙ/ШЛЯХ/до/own_mcp_study", "server.py"]
    }
  }
}
```

Перезапусти Claude Desktop і попроси: «виклич інструмент ping з повідомленням привіт».
Якщо `uv` не знаходиться, вкажи в `command` повний шлях до нього (`which uv`).
