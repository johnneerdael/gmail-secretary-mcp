from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional
from datetime import datetime
import html
import os
import httpx

from workspace_secretary.web import database as db

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def format_date(date_val) -> str:
    if not date_val:
        return ""
    if isinstance(date_val, str):
        try:
            date_val = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return date_val[:10] if len(date_val) > 10 else date_val
    if isinstance(date_val, datetime):
        return date_val.strftime("%b %d, %Y")
    return str(date_val)


def truncate(text: str, length: int = 100) -> str:
    if not text:
        return ""
    text = html.escape(text.strip())
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "..."


def extract_name(addr: str) -> str:
    if not addr:
        return ""
    if "<" in addr:
        return addr.split("<")[0].strip().strip('"')
    return addr.split("@")[0]


async def get_embedding(text: str) -> Optional[list[float]]:
    api_base = os.environ.get("EMBEDDINGS_API_BASE")
    api_key = os.environ.get("EMBEDDINGS_API_KEY", "")
    model = os.environ.get("EMBEDDINGS_MODEL", "text-embedding-3-small")

    if not api_base:
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{api_base}/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "input": text},
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
    except Exception:
        return None


@router.get("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    q: str = Query(""),
    mode: str = Query("keyword"),
    folder: str = Query("INBOX"),
    limit: int = Query(50, ge=1, le=100),
):
    supports_semantic = db.has_embeddings()

    if not q.strip():
        return templates.TemplateResponse(
            "search.html",
            {
                "request": request,
                "query": "",
                "mode": mode,
                "results": [],
                "folder": folder,
                "supports_semantic": supports_semantic,
            },
        )

    results_raw = []
    if mode == "semantic" and supports_semantic:
        embedding = await get_embedding(q)
        if embedding:
            results_raw = db.semantic_search(embedding, folder, limit)
        else:
            results_raw = db.search_emails(q, folder, limit)
    else:
        results_raw = db.search_emails(q, folder, limit)

    results = [
        {
            "uid": e["uid"],
            "folder": e.get("folder", folder),
            "from_name": extract_name(e.get("from_addr", "")),
            "subject": e.get("subject", "(no subject)"),
            "preview": truncate(e.get("preview") or "", 150),
            "date": format_date(e.get("date")),
            "similarity": e.get("similarity"),
        }
        for e in results_raw
    ]

    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "query": q,
            "mode": mode,
            "results": results,
            "folder": folder,
            "supports_semantic": supports_semantic,
        },
    )
