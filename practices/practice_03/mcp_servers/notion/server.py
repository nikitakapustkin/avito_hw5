import os
import httpx
from mcp.server.fastmcp import FastMCP

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

mcp = FastMCP("notion")


@mcp.tool()
def search_pages(query: str) -> dict:
    """Search pages and databases in Notion by text query."""
    response = httpx.post(
        f"{BASE_URL}/search",
        headers=HEADERS,
        json={"query": query, "page_size": 10},
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    return {
        "count": len(results),
        "pages": [
            {
                "id": r["id"],
                "type": r["object"],
                "title": _extract_title(r),
                "url": r.get("url", ""),
            }
            for r in results
        ],
    }


@mcp.tool()
def get_page(page_id: str) -> dict:
    """Get a Notion page by its ID."""
    response = httpx.get(f"{BASE_URL}/pages/{page_id}", headers=HEADERS)
    response.raise_for_status()
    page = response.json()
    return {
        "id": page["id"],
        "title": _extract_title(page),
        "url": page.get("url", ""),
        "created_time": page.get("created_time"),
        "last_edited_time": page.get("last_edited_time"),
    }


@mcp.tool()
def create_page(parent_page_id: str, title: str, content: str = "") -> dict:
    """Create a new Notion page under a parent page."""
    body = {
        "parent": {"page_id": parent_page_id},
        "properties": {
            "title": {
                "title": [{"type": "text", "text": {"content": title}}]
            }
        },
        "children": (
            [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    },
                }
            ]
            if content
            else []
        ),
    }
    response = httpx.post(f"{BASE_URL}/pages", headers=HEADERS, json=body)
    response.raise_for_status()
    page = response.json()
    return {"id": page["id"], "url": page.get("url", ""), "title": title}


@mcp.tool()
def append_text(page_id: str, text: str) -> dict:
    """Append a text paragraph to an existing Notion page."""
    body = {
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                },
            }
        ]
    }
    response = httpx.patch(
        f"{BASE_URL}/blocks/{page_id}/children", headers=HEADERS, json=body
    )
    response.raise_for_status()
    return {"status": "ok", "page_id": page_id}


def _extract_title(obj: dict) -> str:
    props = obj.get("properties", {})
    for key in ("title", "Name", "Title"):
        if key in props:
            rich = props[key].get("title", [])
            if rich:
                return rich[0].get("plain_text", "")
    return "(без названия)"


if __name__ == "__main__":
    mcp.run()
