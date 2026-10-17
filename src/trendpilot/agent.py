"""Live research agent. Uses the Pi xAI login and Grok's web search."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from typing import Any

import httpx

from trendpilot.auth import bearer_token
from trendpilot.fetch import FetchError, fetch_page

MODEL = os.environ.get("TRENDPILOT_MODEL", "grok-4.7")
API_URL = "https://api.x.ai/v1/responses"
MAX_ROUNDS = 7

STATUSES = {"act", "watch", "not_local", "unknown", "do_nothing"}

SYSTEM = """You are TrendPilot, an autonomous business-intelligence agent for a company in Taraz, Kazakhstan. You research, you do not chat.

Job: use tools to find public evidence, decide whether it is relevant to this specific company, and turn only the supported part into a bet the owner can falsify. No research team. No outreach.

Rules:
- Call web_search before any claim about a trend, competitor, price, or local event. Then open the best public pages with fetch_page, including competitor URLs the user gave you.
- Prefer Russian and Kazakh sources about Taraz or Zhambyl oblast. A national or English article is not local evidence by itself.
- Never invent numbers, quotes, or URLs. If the page does not support the claim, drop the claim.
- Do not tell the owner to email, call, or message strangers. A test uses a channel and stock they already have.
- Price cost in their unit: appointment slots, staff hours, SKU margin, truck-kilometers, table turns, guide-days. A paid ad campaign is not an acceptable first test.
- status must be one of: act, watch, not_local, unknown, do_nothing. Weak or non-local evidence cannot be act.
- The bet shape is the same for every industry. Do not assume restaurants or shops.
- Finish by calling submit_findings. That call is the product. Prose alone does not count.
- Write headline, market_read, and every bet field in {language}.
"""


def sentinel_hints(industry: str) -> str:
    text = (industry or "").lower()
    packs = [
        (
            ("clinic", "hospital", "medical", "стомат", "клиник"),
            "appointment demand, seasonal illness load, 2GIS clinic cards, public health-service news in Taraz",
        ),
        (
            ("material", "construct", "строй", "cement", "yard"),
            "local construction starts, heating-season repairs, cement or insulation prices, public contractor news in Zhambyl",
        ),
        (
            ("tour", "travel", "туризм", "hotel"),
            "park access, weekend demand, Aksu-Zhabagly or Karatau public notices, visitor seasonality",
        ),
        (
            ("restaurant", "cafe", "food", "кафе"),
            "public menu or delivery listings, local food prices, weekend footfall signals, not generic global food trends",
        ),
        (
            ("logistic", "freight", "груз", "transport"),
            "road, border, fuel, and warehouse news that changes a Taraz route this month",
        ),
        (
            ("farm", "agri", "сель", "grain"),
            "Zhambyl harvest, water, and wholesale price notices",
        ),
    ]
    for keys, hint in packs:
        if any(key in text for key in keys):
            return hint
    return (
        "public local news, competitor pages, and a price or demand signal the owner can see "
        "without private data"
    )


def company_brief(company: dict[str, str], question: str | None) -> str:
    lines = [
        "Research this company. It may be a demo profile, so do not pretend you have its private books.",
        f"Name: {company.get('name') or 'unnamed'}",
        f"Industry: {company.get('industry') or 'unspecified'}",
        f"Size: {company.get('size') or 'unspecified'}",
        f"City: {company.get('city') or 'Taraz'}",
        f"Offer: {company.get('offer') or 'unspecified'}",
        f"Customer: {company.get('customer') or 'unspecified'}",
        f"Channel they already own: {company.get('channel') or 'unspecified'}",
        f"Hard constraint: {company.get('constraint') or 'unspecified'}",
        f"Competitors: {company.get('competitors') or 'unspecified'}",
        f"Sentinels to check: {sentinel_hints(company.get('industry', ''))}",
        "Return 1 to 3 bets. One is enough if the evidence is thin.",
    ]
    if question:
        lines.append(f"Owner question: {question}")
    else:
        lines.append(
            "No extra question. Find the single most useful local signal and say what to do about it, including doing nothing."
        )
    return "\n".join(lines)


def run(
    company: dict[str, str],
    question: str | None = None,
    transcript: list[dict[str, Any]] | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield trace events. The last event with kind 'done' carries findings and transcript."""
    from trendpilot.envfile import load_env

    load_env()
    if os.environ.get("TRENDPILOT_PROVIDER", "").lower() == "gemini":
        from trendpilot.gemini import run as run_gemini

        yield from run_gemini(company, question)
        return
    token = bearer_token()
    language = company.get("language") or "Russian"
    instructions = SYSTEM.format(language=language)
    items: list[dict[str, Any]] = list(transcript or [])
    items.append({"role": "user", "content": company_brief(company, question)})

    findings: dict[str, Any] | None = None
    trace: list[dict[str, Any]] = []
    last_text = ""

    for round_index in range(1, MAX_ROUNDS + 1):
        yield _event("status", f"Round {round_index}", "Asking Grok, with web search enabled.")
        data = _post(token, instructions, items)
        output = data.get("output") or []
        if not output:
            raise RuntimeError(f"xAI returned no output: {json.dumps(data)[:400]}")
        items.extend(output)

        calls: list[dict[str, Any]] = []
        for item in output:
            kind = item.get("type")
            if kind == "web_search_call":
                event = _search_event(item)
                trace.append(event)
                yield event
            elif kind == "function_call":
                calls.append(item)
            elif kind == "message":
                last_text = _message_text(item)
                if last_text:
                    event = _event("note", "Agent note", last_text[:1200])
                    trace.append(event)
                    yield event

        if not calls:
            break

        stop = False
        for call in calls:
            name = call.get("name") or ""
            raw_args = call.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                args = {}
                output_text = "ERROR: arguments were not valid JSON. Call the tool again with valid JSON."
                event = _event("error", name, output_text)
                trace.append(event)
                yield event
                items.append(_tool_output(call, output_text))
                continue

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
            items.append(_tool_output(call, output_text))

        if stop:
            break
    else:
        yield _event("error", "Stopped", "Reached the round limit before a clean finish.")

    if findings is None and last_text:
        findings = _findings_from_text(last_text)

    public_transcript = [_public_item(item) for item in items]
    yield {
        "kind": "done",
        "title": "Done",
        "detail": findings.get("headline", "") if findings else "No structured findings.",
        "payload": {
            "findings": findings,
            "trace": trace,
            "transcript": public_transcript,
            "note": last_text,
        },
    }


def _post(token: str, instructions: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    body = {
        "model": MODEL,
        "store": False,
        "instructions": instructions,
        "input": items,
        "tools": _tools(),
        "max_output_tokens": 8000,
    }
    try:
        with httpx.Client(timeout=180) as client:
            response = client.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Could not reach xAI: {exc}") from exc
    if response.status_code >= 400:
        raise RuntimeError(f"xAI {response.status_code}: {response.text[:500]}")
    return response.json()


def _tools() -> list[dict[str, Any]]:
    return [
        {"type": "web_search"},
        {
            "type": "function",
            "name": "fetch_page",
            "description": "Open one public http(s) page and read its text. Use this on search results and competitor sites.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "Public http or https URL"}},
                "required": ["url"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "submit_findings",
            "description": "File the finished analysis. Call this once, after the searches.",
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": ["headline", "market_read", "bets"],
                "properties": {
                    "headline": {"type": "string"},
                    "market_read": {"type": "string"},
                    "bets": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 3,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
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
                            "properties": {
                                "title": {"type": "string"},
                                "status": {
                                    "type": "string",
                                    "enum": ["act", "watch", "not_local", "unknown", "do_nothing"],
                                },
                                "claim": {"type": "string"},
                                "evidence": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "required": ["url", "what_it_shows"],
                                        "properties": {
                                            "url": {"type": "string"},
                                            "what_it_shows": {"type": "string"},
                                        },
                                    },
                                },
                                "relevance": {"type": "string"},
                                "cost": {"type": "string"},
                                "benefit": {"type": "string"},
                                "test": {"type": "string"},
                                "kill_line": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    ]


def _search_event(item: dict[str, Any]) -> dict[str, Any]:
    action = item.get("action") or {}
    query = action.get("query") or item.get("query") or "web search"
    sources = action.get("sources") or []
    urls = []
    for source in sources:
        if isinstance(source, dict) and source.get("url"):
            urls.append(source["url"])
        elif isinstance(source, str):
            urls.append(source)
    detail = query if not urls else query + "\n" + "\n".join(urls[:8])
    return _event("search", "Web search", detail)


def _message_text(item: dict[str, Any]) -> str:
    parts = []
    for block in item.get("content") or []:
        if isinstance(block, dict) and block.get("type") in {"output_text", "text"}:
            parts.append(block.get("text") or "")
    return "\n".join(part for part in parts if part).strip()


def _tool_output(call: dict[str, Any], output_text: str) -> dict[str, Any]:
    return {
        "type": "function_call_output",
        "call_id": call.get("call_id"),
        "output": output_text,
    }


def _normalize_findings(args: dict[str, Any]) -> dict[str, Any]:
    bets = []
    for raw in args.get("bets") or []:
        if not isinstance(raw, dict):
            continue
        status = str(raw.get("status") or "unknown")
        if status not in STATUSES:
            status = "unknown"
        evidence = []
        for item in raw.get("evidence") or []:
            if isinstance(item, dict) and item.get("url"):
                evidence.append(
                    {
                        "url": str(item.get("url")),
                        "what_it_shows": str(item.get("what_it_shows") or ""),
                    }
                )
        bets.append(
            {
                "title": str(raw.get("title") or "Untitled bet"),
                "status": status,
                "claim": str(raw.get("claim") or ""),
                "evidence": evidence,
                "relevance": str(raw.get("relevance") or ""),
                "cost": str(raw.get("cost") or ""),
                "benefit": str(raw.get("benefit") or ""),
                "test": str(raw.get("test") or ""),
                "kill_line": str(raw.get("kill_line") or ""),
            }
        )
    return {
        "headline": str(args.get("headline") or "No headline"),
        "market_read": str(args.get("market_read") or ""),
        "bets": bets,
    }


def _findings_from_text(text: str) -> dict[str, Any] | None:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or "bets" not in parsed:
        return None
    return _normalize_findings(parsed)


def _public_item(item: dict[str, Any]) -> dict[str, Any]:
    """Drop encrypted reasoning before anything is shown or stored."""
    cleaned = {key: value for key, value in item.items() if key != "encrypted_content"}
    if cleaned.get("type") == "reasoning":
        return {"type": "reasoning", "status": cleaned.get("status", "completed")}
    return cleaned


def _event(kind: str, title: str, detail: str = "") -> dict[str, Any]:
    return {"kind": kind, "title": title, "detail": detail}
