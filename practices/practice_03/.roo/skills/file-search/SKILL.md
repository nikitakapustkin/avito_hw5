---
name: file-search
description: >
  Expert guidance on using ripgrep and ast-grep for efficient codebase search.
  Triggered by phrases like "find in code", "search for", "where is",
  "find all usages", "grep", "найди в коде", "где используется".
---

# File Search Skill

## Tools

### ripgrep (rg) — text search
Ultra-fast regex search across files.

```bash
# Find pattern in specific file type
rg "CityNotFoundError" --type py

# Find in specific directory
rg "subscribe" weather_service/

# Show context lines
rg "HTTPException" -C 2 weather_service/app.py

# Find with line numbers
rg -n "async def" weather_service/
```

### ast-grep (sg) — structural search
Syntax-aware search — finds code patterns, not just strings.

```bash
# Find all async functions
sg -p 'async def $NAME($$$)' --lang python

# Find all raise statements
sg -p 'raise $ERROR($MSG)' --lang python

# Find HTTPException usages
sg -p 'HTTPException(status_code=$CODE, detail=$MSG)' --lang python
```

## Key Principle: Start Narrow
Always scope searches before broadening:
1. Target specific file/directory first
2. Filter by file type (`--type py`)
3. Use precise patterns, not broad keywords
4. Limit results: `rg "error" | head -20`

## Common Use Cases for weather_service

| Goal | Command |
|------|---------|
| Find all endpoints | `rg "@app\.(get\|post\|delete)" weather_service/app.py` |
| Find error mappings | `rg "HTTPException" weather_service/app.py` |
| Find Redis calls | `rg "redis\|cache" weather_service/ --type py` |
| Find all imports | `rg "^from\|^import" weather_service/models.py` |
| Find test fixtures | `rg "@pytest.fixture" tests/` |

## Installation (if not present)
```bash
brew install ripgrep ast-grep  # macOS
```
