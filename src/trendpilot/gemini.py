"""Gemini research loop for the judge copy. The key stays in .env."""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import httpx

from trendpilot.agent import SYSTEM, _event, _normalize_findings, company_brief
from trendpilot.fetch import FetchError, fetch_page

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MAX_ROUNDS = 5


def run(company: dict[str, str], question: str | None = None) -> Iterator[dict[str, Any]]:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing. Put it in trendpilot_/.env.")
    model = os.environ.get("TRENDPILOT_MODEL", "gemini-3.5-flash-lite")
    language = company.get("language") or "Russian"
    instructions = SYSTEM.format(language=language).replace(
        "Call web_search before any claim",
        "Use the search notes already in the conversation, then open pages with fetch_page, before any claim",
    )
    instructions += (
        "\nYou are running on Gemini, not Grok. Finish by calling submit_findings. "
        "Do not invent URLs. If search was unavailable, say so inside market_read and do not pretend you searched."
    )
    contents: list[dict[str, Any]] = [
        {"role": "user", "parts": [{"text": company_brief(company, question)}]}
    ]
    findings: dict[str, Any] | None = None
    trace: list[dict[str, Any]] = []
    last_text = ""

    yield _event("status", "Gemini", f"Asking {model}.")
    search_note = _search(key, model, instructions, contents[0]["parts"][0]["text"])
    if search_note["ok"]:
        event = _event("search", "Google search", search_note["detail"])
        trace.append(event)
        yield event
        contents.append({"role": "user", "parts": [{"text": search_note["detail"]}]})
    else:
        event = _event("note", "Search unavailable", search_note["detail"])
        trace.append(event)
        yield event

    for round_index in range(1, MAX_ROUNDS + 1):
        yield _event("status", f"Round {round_index}", "Asking Gemini.")
        data = _post(key, model, instructions, contents, _function_tools())
        parts = _parts(data)
        contents.append({"role": "model", "parts": parts})
        calls = [part["functionCall"] for part in parts if isinstance(part.get("functionCall"), dict)]
        texts = [part.get("text") or "" for part in parts if part.get("text")]
        if texts:
            last_text = "\n".join(text for text in texts if text).strip()
            if last_text:
                event = _event("note", "Agent note", last_text[:1200])
                trace.append(event)
                yield event
        if not calls:
            break

        responses = []
        stop = False
        for call in calls:
            name = call.get("name") or ""
            args = call.get("args") if isinstance(call.get("args"), dict) else {}
            if name == "fetch_page":
                url = str(args.get("url") or "")
                yield _event("status", "Opening page", url)
                try:
                    output_text = fetch_page(url)
                    event = _event("fetch", url, output_text[:500])
                except FetchError as exc:
                    output_text = f"ERROR: {exc}"
                    event = _event("error", "fetch_page", str(exc))
            elif name == "submit_findings":
                findings = _normalize_findings(args)
                output_text = "accepted"
                event = _event("findings", "Findings filed", findings.get("headline", ""))
                event["payload"] = findings
                stop = True
            else:
                output_text = f"ERROR: unknown tool {name}"
                event = _event("error", name, output_text)
            trace.append(event)
            yield event
            responses.append(
                {
                    "functionResponse": {
                        "name": name,
                        "response": {"result": output_text[:7000]},
                    }
                }
            )
        contents.append({"role": "user", "parts": responses})
        if stop:
            break
    else:
        yield _event("error", "Stopped", "Reached the round limit before a clean finish.")

    yield {
        "kind": "done",
        "title": "Done",
        "detail": findings.get("headline", "") if findings else "No structured findings.",
        "payload": {"findings": findings, "trace": trace, "note": last_text, "model": model},
    }


def _search(key: str, model: str, instructions: str, brief: str) -> dict[str, Any]:
    try:
        data = _post(
            key,
            model,
            instructions,
            [{"role": "user", "parts": [{"text": brief + "\nSearch public web pages. Do not file findings yet."}]}],
            [{"google_search": {}}],
        )
    except RuntimeError as exc:
        text = str(exc)
        if "429" in text or "quota" in text.lower():
            return {
                "ok": False,
                "detail": "Gemini answered, but Google Search on this free key is over its quota. Research can still open pages, without live search.",
            }
        return {"ok": False, "detail": text[:400]}
    meta = ((data.get("candidates") or [{}])[0]).get("groundingMetadata") or {}
    queries = meta.get("webSearchQueries") or []
    urls = []
    for chunk in meta.get("groundingChunks") or []:
        web = chunk.get("web") or {}
        if web.get("uri"):
            urls.append(web["uri"])
    detail = "\n".join([*queries, *urls[:8]]).strip()
    if not detail:
        detail = _text(data)[:800] or "Search returned no public URLs."
    return {"ok": True, "detail": detail}


def _post(key: str, model: str, instructions: str, contents: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
    body = {
        "systemInstruction": {"parts": [{"text": instructions}]},
        "contents": contents,
        "tools": tools,
        "generationConfig": {"maxOutputTokens": 4000},
    }
    url = API.format(model=model)
    try:
        with httpx.Client(timeout=120) as client:
            response = client.post(
                url,
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                json=body,
            )
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Could not reach Gemini: {exc}") from exc
    if response.status_code >= 400:
        raise RuntimeError(f"Gemini {response.status_code}: {response.text[:400]}")
    return response.json()


def _parts(data: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Gemini returned no candidates: {str(data)[:300]}")
    parts = ((candidates[0].get("content") or {}).get("parts")) or []
    if not parts:
        raise RuntimeError(f"Gemini returned no parts: {str(data)[:300]}")
    return parts


def _text(data: dict[str, Any]) -> str:
    parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    return "\n".join(part.get("text") or "" for part in parts if isinstance(part, dict)).strip()


def _function_tools() -> list[dict[str, Any]]:
    bet = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "status": {"type": "string"},
            "claim": {"type": "string"},
            "evidence": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "what_it_shows": {"type": "string"},
                    },
                    "required": ["url", "what_it_shows"],
                },
            },
            "relevance": {"type": "string"},
            "cost": {"type": "string"},
            "benefit": {"type": "string"},
            "test": {"type": "string"},
            "kill_line": {"type": "string"},
        },
        "required": [
            "title",
            "status",
            "claim",
            "evidence",
            "relevance",
            "cost",
            "benefit",
            "test",
            "kill_line",
        ],
    }
    return [
        {
            "functionDeclarations": [
                {
                    "name": "fetch_page",
                    "description": "Open one public http(s) page and read its text.",
                    "parameters": {
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"],
                    },
                },
                {
                    "name": "submit_findings",
                    "description": "File the finished analysis once.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "headline": {"type": "string"},
                            "market_read": {"type": "string"},
                            "bets": {"type": "array", "items": bet},
                        },
                        "required": ["headline", "market_read", "bets"],
                    },
                },
            ]
        }
    ]
