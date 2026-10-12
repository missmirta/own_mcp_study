# own_mcp_study

Власний MCP-сервер для конспекту з Notion. Пишемо його крок за кроком, щоб вивчити Model Context Protocol.

## План

1. **Скелет сервера** з одним інструментом `ping`, перевірка в MCP Inspector і Claude Desktop. ✅
2. **Конспект як дані**: Markdown-експорт з Notion та інструменти `list_notes`, `read_note`, `search_notes`. ✅
3. **Решта протоколу**: resource для кожної нотатки та prompt «зроби квіз за темою». ✅
4. **Живий Notion**: читання через Notion API замість експорту. ← зараз тут

## Запуск

Потрібен [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/missmirta/own_mcp_study
cd own_mcp_study
uv sync
uv run pytest        # тести
```

### Конспект

Сервер читає Markdown-експорт з Notion:

1. У Notion відкрий сторінку конспекту → **⋯ → Export**.
2. Формат **Markdown & CSV**, увімкни **Include subpages** (інакше потрапить лише верхня сторінка без підсторінок).
3. Розпакуй zip у папку `notes/` у репозиторії (вона в .gitignore, тож конспект не потрапить у git) або в будь-яку іншу і вкажи її в `NOTES_DIR`.

Інструменти:

- `list_notes` — список нотаток з id. Notion-ові хеші з назв прибрано, тож id виглядають як `Machine Learning/PyTorch`.
- `read_note(note_id)` — повний текст нотатки.
- `search_notes(query, limit=20)` — рядки зі збігом, без урахування регістру.

Ресурси та prompt:

- Кожна нотатка є ресурсом `note:///<id>`. У Claude Desktop їх видно в меню **+ → notes**, і нотатку можна прикріпити до розмови цілком.
- Prompt `quiz(topic, questions=5)` знаходить нотатки, де згадується тема, і просить Claude провести квіз з питаннями по одному. У Claude Desktop він теж у меню **+ → notes**.

Три частини MCP і хто їх викликає: **tools** вирішує викликати модель, **resources** прикріплює користувач чи застосунок, **prompts** обирає користувач як готовий сценарій.

### Живий Notion (без експорту)

Сервер може читати конспект напряму з Notion, тоді нічого експортувати не треба:

1. Відкрий [notion.so/my-integrations](https://www.notion.so/my-integrations) → **New integration**, тип Internal, дозволи **Read content**. Скопіюй токен (`ntn_…` або `secret_…`).
2. Відкрий кореневу сторінку конспекту → **⋯ → Connections** → додай свою інтеграцію. Підсторінки успадкують доступ.
3. Скопіюй посилання на цю сторінку (**Share → Copy link**).
4. Додай у `env` конфігу Claude Desktop:

```json
"env": {
  "NOTION_TOKEN": "ntn_...",
  "NOTION_PAGE": "https://www.notion.so/Machine-Learning-3b2736c1ab2c8060b525fd7bc7052f74"
}
```

Коли обидві змінні задані, `NOTES_DIR` ігнорується. Сервер обходить кореневу сторінку та всі підсторінки (і `child_page`, і посилання на сторінки), перетворює блоки на Markdown і кешує результат на хвилину, бо Notion API повільний і обмежує частоту запитів. Токен нікуди не потрапляє, крім заголовка запитів до api.notion.com. Зображення й вбудовані бази даних поки пропускаються.

Щоб оновити конспект, просто заміни файли в папці: сервер перечитує її на кожен виклик.

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
      "args": ["run", "--directory", "/ПОВНИЙ/ШЛЯХ/до/own_mcp_study", "server.py"],
      "env": { "NOTES_DIR": "/ПОВНИЙ/ШЛЯХ/до/експорту" }
    }
  }
}
```

`env` можна прибрати, якщо експорт лежить у `notes/`.

Перезапусти Claude Desktop і спитай, наприклад: «що в моєму конспекті про Tensor Cores?»
Якщо `uv` не знаходиться, вкажи в `command` повний шлях до нього (`which uv`).
