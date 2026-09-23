"""Small SQLite repository for the personal You Can't Trade service."""

from __future__ import annotations

import json
import os
import sqlite3
import base64
import uuid
from pathlib import Path
from typing import Any

from services.deterministic_analytics import calculate_journal_analytics


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("YOU_CANT_TRADE_DATA_DIR", ROOT / "data"))
DB_PATH = DATA_DIR / "you-cant-trade.sqlite3"
SCREENSHOT_DIR = DATA_DIR / "screenshots"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("pragma foreign_keys = on")
    connection.execute("pragma journal_mode = wal")
    return connection


def initialise() -> None:
    with connect() as connection:
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            connection.executescript(migration.read_text(encoding="utf-8"))

        columns = {row[1] for row in connection.execute("pragma table_info(trades)").fetchall()}
        if "intelligence_json" not in columns:
            connection.execute("alter table trades add column intelligence_json text not null default '{}' ")
        connection.execute("update trades set schema_version = 4 where schema_version < 4")


def trade_count() -> int:
    with connect() as connection:
        return int(connection.execute("select count(*) from trades").fetchone()[0])


def historical_candidate_limit() -> int:
    """Return a bounded candidate count for fast historical comparison."""
    count = trade_count()

    if count <= 500:
        return count

    if count <= 1000:
        return 500

    return 1000


def storage_stats() -> dict[str, int]:
    total_bytes = sum(
        path.stat().st_size
        for path in DATA_DIR.rglob("*")
        if path.is_file()
    ) if DATA_DIR.exists() else 0
    return {"bytes": total_bytes, "tradeCount": trade_count()}


def _empty_intelligence() -> dict[str, Any]:
    return {
        "marketContext": {"trend": None, "regime": None, "volatility": None, "momentum": None, "session": None, "higherTimeframe": None},
        "marketStructure": {"events": [], "swings": [], "levels": []},
        "setupFingerprint": {"version": 1, "features": [], "tags": [], "marketRegime": None},
        "calculated": {"features": {}, "provenance": {"source": "CALCULATED", "confidence": 1, "evidence": []}},
        "execution": {"actualEntry": None, "actualStopLoss": None, "actualTakeProfit": None, "entryTime": None, "exitTime": None, "stopMoved": None, "targetMoved": None, "partialExits": [], "breakEven": None, "slippage": None},
        "behavior": {"ruleViolations": [], "tags": [], "evidence": []},
        "rules": {"applicable": [], "satisfied": [], "violated": []},
        "historical": {"similarTradeIds": [], "similarityScore": None, "sampleSize": None, "comparableStats": None, "patternReferences": []},
        "ai": {"analysis": None, "evidence": [], "memoryReferences": [], "retrievedMemories": [], "reasoning": None},
    }


def _store_screenshot(trade_id: str, screenshot: Any) -> str | None:
    if not isinstance(screenshot, str) or not screenshot.startswith("data:"):
        return None

    header, encoded = screenshot.split(",", 1) if "," in screenshot else ("", "")
    if ";base64" not in header:
        return None

    mime = header[5:].split(";", 1)[0]
    extension = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
    }.get(mime, "bin")
    screenshot_path = SCREENSHOT_DIR / f"{trade_id}.{extension}"
    screenshot_path.write_bytes(base64.b64decode(encoded, validate=True))
    return f"screenshots/{screenshot_path.name}"


def _review_values(payload: dict[str, Any]) -> tuple[Any, ...]:
    emotions = payload.get("emotions", [])
    if not isinstance(emotions, list) or not all(isinstance(item, str) for item in emotions):
        emotions = []

    return (
        payload.get("setup", ""),
        payload.get("session"),
        payload.get("planAdherence"),
        payload.get("executionTag"),
        payload.get("notes", ""),
        json.dumps(emotions),
    )


def upsert_trade(payload: dict[str, Any]) -> dict[str, Any]:
    trade_id = payload.get("id")
    if not isinstance(trade_id, str) or not trade_id.strip():
        raise ValueError("A stable trade id is required.")
    captured_at = payload.get("timestamp")
    updated_at = payload.get("updatedAt") or captured_at
    if not isinstance(captured_at, str) or not isinstance(updated_at, str):
        raise ValueError("Capture and update timestamps are required.")

    screenshot_path = _store_screenshot(trade_id, payload.get("screenshot"))
    if screenshot_path is None:
        screenshot_path = payload.get("screenshotPath")
    if screenshot_path is None:
        with connect() as connection:
            existing = connection.execute(
                "select screenshot_path from trades where id = ?",
                (trade_id,),
            ).fetchone()
        screenshot_path = existing[0] if existing else None

    fields = (
        trade_id,
        int(payload.get("schemaVersion", 4)),
        payload.get("source", "TRADINGVIEW"),
        payload.get("status", "CAPTURED"),
        captured_at,
        updated_at,
        payload.get("symbol", ""),
        payload.get("timeframe", ""),
        payload.get("exchange", ""),
        payload.get("direction"),
        payload.get("entry"),
        payload.get("stopLoss"),
        payload.get("takeProfit"),
        payload.get("chartAnchorTime"),
        payload.get("chartAnchorInterval"),
        payload.get("exitPrice"),
        payload.get("result"),
        payload.get("url", ""),
        screenshot_path,
        json.dumps(payload.get("intelligence") or {}, ensure_ascii=False),
    )
    with connect() as connection:
        connection.execute(
            """insert into trades (
                id, schema_version, source, status, captured_at, updated_at,
                symbol, timeframe, exchange, direction, entry, stop_loss,
                take_profit, chart_anchor_time, chart_anchor_interval,
                exit_price, result, source_url, screenshot_path, intelligence_json
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(id) do update set
                schema_version=excluded.schema_version,
                status=excluded.status,
                updated_at=excluded.updated_at,
                symbol=excluded.symbol,
                timeframe=excluded.timeframe,
                exchange=excluded.exchange,
                direction=excluded.direction,
                entry=excluded.entry,
                stop_loss=excluded.stop_loss,
                take_profit=excluded.take_profit,
                chart_anchor_time=excluded.chart_anchor_time,
                chart_anchor_interval=excluded.chart_anchor_interval,
                exit_price=excluded.exit_price,
                result=excluded.result,
                source_url=excluded.source_url,
                screenshot_path=excluded.screenshot_path,
                intelligence_json=excluded.intelligence_json""",
            fields,
        )
        connection.execute(
            """insert into trade_reviews (
                trade_id, setup, session, plan_adherence, execution_tag, notes, emotions_json
            ) values (?, ?, ?, ?, ?, ?, ?)
            on conflict(trade_id) do update set
                setup=excluded.setup,
                session=excluded.session,
                plan_adherence=excluded.plan_adherence,
                execution_tag=excluded.execution_tag,
                notes=excluded.notes,
                emotions_json=excluded.emotions_json,
                reviewed_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now')""",
            (trade_id, *_review_values(payload)),
        )

    return get_trade(trade_id) or {}


def _row_to_trade(row: sqlite3.Row) -> dict[str, Any]:
    trade = dict(row)
    schema_version = trade.pop("schema_version", 4)
    trade["schemaVersion"] = int(schema_version or 4)
    trade["timestamp"] = trade.pop("captured_at")
    trade["updatedAt"] = trade.pop("updated_at")
    trade["stopLoss"] = trade.pop("stop_loss")
    trade["takeProfit"] = trade.pop("take_profit")
    chart_anchor_time = trade.pop("chart_anchor_time")
    if chart_anchor_time is not None:
        try:
            numeric_chart_time = float(chart_anchor_time)
            chart_anchor_time = int(numeric_chart_time) if numeric_chart_time.is_integer() else numeric_chart_time
        except (TypeError, ValueError):
            chart_anchor_time = None
    trade["chartAnchorTime"] = chart_anchor_time
    trade["chartAnchorInterval"] = trade.pop("chart_anchor_interval")
    trade["exitPrice"] = trade.pop("exit_price")
    trade["url"] = trade.pop("source_url")
    trade["screenshotPath"] = trade.pop("screenshot_path")
    intelligence = trade.pop("intelligence_json", "{}")
    try:
        stored = json.loads(intelligence) if intelligence else {}
        trade["intelligence"] = stored if isinstance(stored, dict) and stored else _empty_intelligence()
    except (TypeError, json.JSONDecodeError):
        trade["intelligence"] = _empty_intelligence()
    emotions = trade.pop("emotions_json", "[]")
    trade["emotions"] = json.loads(emotions) if emotions else []
    trade["setup"] = trade.pop("setup", "")
    trade["session"] = trade.pop("session", None)
    trade["planAdherence"] = trade.pop("plan_adherence", None)
    trade["executionTag"] = trade.pop("execution_tag", None)
    trade.pop("trade_id", None)
    trade.pop("reviewed_at", None)
    return trade


def _canonical_similarity_score(source: dict[str, Any], candidate: dict[str, Any]) -> int:
    """Score historical similarity using canonical intelligence first.

    Outcome/result is intentionally excluded so retrieval does not become
    outcome-biased. Journal fields provide secondary context only.
    """
    score = 0

    # Primary trade identity/context.
    if source.get("symbol") and source.get("symbol") == candidate.get("symbol"):
        score += 5

    if source.get("timeframe") and source.get("timeframe") == candidate.get("timeframe"):
        score += 3

    if source.get("direction") and source.get("direction") == candidate.get("direction"):
        score += 2

    source_intelligence = source.get("intelligence") or {}
    candidate_intelligence = candidate.get("intelligence") or {}

    source_context = source_intelligence.get("marketContext") or {}
    candidate_context = candidate_intelligence.get("marketContext") or {}

    # Canonical market regime.
    if (
        source_context.get("regime")
        and source_context.get("regime") == candidate_context.get("regime")
    ):
        score += 4

    if (
        source_context.get("direction")
        and source_context.get("direction") == candidate_context.get("direction")
    ):
        score += 3

    # Canonical market structure.
    source_structure = source_intelligence.get("marketStructure") or {}
    candidate_structure = candidate_intelligence.get("marketStructure") or {}

    if (
        source_structure.get("state")
        and source_structure.get("state") == candidate_structure.get("state")
    ):
        score += 4

    # Setup fingerprint.
    source_fingerprint = source_intelligence.get("setupFingerprint") or {}
    candidate_fingerprint = candidate_intelligence.get("setupFingerprint") or {}

    source_features = set(source_fingerprint.get("features") or [])
    candidate_features = set(candidate_fingerprint.get("features") or [])
    score += 2 * len(source_features & candidate_features)

    source_tags = set(source_fingerprint.get("tags") or [])
    candidate_tags = set(candidate_fingerprint.get("tags") or [])
    score += 2 * len(source_tags & candidate_tags)

    # Latest structural event provides additional context.
    def latest_structure_event(structure: dict[str, Any]) -> str | None:
        events = structure.get("events") or []
        if not events:
            return None

        valid_events = [
            event
            for event in events
            if isinstance(event, dict) and event.get("event")
        ]

        if not valid_events:
            return None

        valid_events.sort(
            key=lambda event: (
                float(event.get("time"))
                if isinstance(event.get("time"), (int, float))
                else float("-inf")
            )
        )

        return valid_events[-1].get("event")

    source_event = latest_structure_event(source_structure)
    candidate_event = latest_structure_event(candidate_structure)

    if source_event and source_event == candidate_event:
        score += 3

    # Secondary journal context.
    if source.get("setup") and source.get("setup") == candidate.get("setup"):
        score += 3

    if source.get("session") and source.get("session") == candidate.get("session"):
        score += 1

    if (
        source.get("planAdherence")
        and source.get("planAdherence") == candidate.get("planAdherence")
    ):
        score += 1

    if (
        source.get("executionTag")
        and source.get("executionTag") == candidate.get("executionTag")
    ):
        score += 1

    shared_emotions = set(source.get("emotions") or []) & set(candidate.get("emotions") or [])
    score += len(shared_emotions)

    return score

def build_historical_context(
    trade_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    """Build compact historical evidence for a persisted trade."""
    source = get_trade(trade_id)

    if not source:
        return _empty_intelligence()["historical"]

    matches = similar_trades(trade_id, limit=limit)

    reviewed = [
        trade
        for trade in matches
        if trade.get("result") in {"WIN", "LOSS", "BE"}
    ]

    wins = sum(trade.get("result") == "WIN" for trade in reviewed)
    losses = sum(trade.get("result") == "LOSS" for trade in reviewed)
    break_even = sum(trade.get("result") == "BE" for trade in reviewed)

    actual_r: list[float] = []
    planned_rr: list[float] = []

    for trade in reviewed:
        entry = trade.get("entry")
        stop = trade.get("stopLoss")
        exit_price = trade.get("exitPrice")

        if all(
            isinstance(value, (int, float))
            for value in (entry, stop, exit_price)
        ):
            risk = abs(entry - stop)

            if risk > 0:
                profit = (
                    exit_price - entry
                    if trade.get("direction") == "LONG"
                    else entry - exit_price
                )
                actual_r.append(profit / risk)

        intelligence = trade.get("intelligence") or {}
        calculated = intelligence.get("calculated") or {}
        features = calculated.get("features") or {}

        value = features.get("plannedRR")
        if isinstance(value, (int, float)):
            planned_rr.append(float(value))

    comparable_stats = {
        "reviewedSampleSize": len(reviewed),
        "wins": wins,
        "losses": losses,
        "breakEven": break_even,
        "winRate": (
            round(wins / len(reviewed), 4)
            if reviewed
            else None
        ),
        "actualR": {
            "count": len(actual_r),
            "average": (
                round(sum(actual_r) / len(actual_r), 6)
                if actual_r
                else None
            ),
        },
        "plannedRR": {
            "count": len(planned_rr),
            "average": (
                round(sum(planned_rr) / len(planned_rr), 6)
                if planned_rr
                else None
            ),
        },
    }

    pattern_references: list[str] = []

    source_fingerprint = (
        (source.get("intelligence") or {}).get("setupFingerprint") or {}
    )

    for tag in source_fingerprint.get("tags") or []:
        if isinstance(tag, str) and tag not in pattern_references:
            pattern_references.append(tag)

    for feature in source_fingerprint.get("features") or []:
        if isinstance(feature, str) and feature not in pattern_references:
            pattern_references.append(feature)

    scores = [
        _canonical_similarity_score(source, trade)
        for trade in matches
    ]

    compact_matches = []

    for trade, score in zip(matches, scores):
        intelligence = trade.get("intelligence") or {}
        market_context = intelligence.get("marketContext") or {}
        market_structure = intelligence.get("marketStructure") or {}
        fingerprint = intelligence.get("setupFingerprint") or {}
        calculated = intelligence.get("calculated") or {}
        features = calculated.get("features") or {}

        compact_matches.append({
            "id": trade.get("id"),
            "similarityScore": score,
            "symbol": trade.get("symbol"),
            "timeframe": trade.get("timeframe"),
            "direction": trade.get("direction"),
            "result": trade.get("result"),
            "marketRegime": market_context.get("regime"),
            "structureState": market_structure.get("state"),
            "setupFeatures": fingerprint.get("features") or [],
            "setupTags": fingerprint.get("tags") or [],
            "plannedRR": features.get("plannedRR"),
        })

    return {
        "similarTradeIds": [
            trade.get("id")
            for trade in matches
            if isinstance(trade.get("id"), str)
        ],
        "similarityScore": max(scores) if scores else None,
        "sampleSize": len(matches),
        "comparableStats": comparable_stats,
        "patternReferences": pattern_references,
        "matches": compact_matches,
    }


def similar_trades(trade_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Return historically similar trades using canonical intelligence signals."""
    source = get_trade(trade_id)
    if not source:
        return []

    candidates = list_trades(limit=1000)
    scored = []

    for trade in candidates:
        if trade.get("id") == trade_id:
            continue

        score = _canonical_similarity_score(source, trade)

        if score:
            scored.append((score, trade))

    scored.sort(
        key=lambda item: (
            -item[0],
            item[1].get("timestamp") or "",
        )
    )

    return [
        trade
        for _, trade in scored[: max(1, min(int(limit), 50))]
    ]


def search_trades(query: str, limit: int = 50) -> list[dict[str, Any]]:
    """Search journal text locally without sending records to an external service."""
    term = " ".join(str(query or "").split()).strip()
    if not term:
        return []
    safe_limit = max(1, min(int(limit), 200))
    pattern = f"%{term}%"
    with connect() as connection:
        rows = connection.execute(
            """select t.*, r.setup, r.session, r.plan_adherence,
                      r.execution_tag, r.notes, r.emotions_json, r.reviewed_at
               from trades t left join trade_reviews r on r.trade_id = t.id
               where lower(
                   coalesce(t.symbol, '') || ' ' || coalesce(t.timeframe, '') || ' ' ||
                   coalesce(t.direction, '') || ' ' || coalesce(t.result, '') || ' ' ||
                   coalesce(r.setup, '') || ' ' || coalesce(r.session, '') || ' ' ||
                   coalesce(r.plan_adherence, '') || ' ' || coalesce(r.execution_tag, '') || ' ' ||
                   coalesce(r.notes, '') || ' ' || coalesce(r.emotions_json, '')
               ) like lower(?)
               order by t.captured_at desc limit ?""",
            (pattern, safe_limit),
        ).fetchall()
    return [_row_to_trade(row) for row in rows]


def get_trade(trade_id: str) -> dict[str, Any] | None:
    with connect() as connection:
        row = connection.execute(
            """select t.*, r.setup, r.session, r.plan_adherence,
                      r.execution_tag, r.notes, r.emotions_json, r.reviewed_at
               from trades t left join trade_reviews r on r.trade_id = t.id
               where t.id = ?""",
            (trade_id,),
        ).fetchone()
    return _row_to_trade(row) if row else None


def list_trades(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 1000))
    safe_offset = max(0, int(offset))
    with connect() as connection:
        rows = connection.execute(
            """select t.*, r.setup, r.session, r.plan_adherence,
                      r.execution_tag, r.notes, r.emotions_json, r.reviewed_at
               from trades t left join trade_reviews r on r.trade_id = t.id
               order by t.captured_at desc limit ? offset ?""",
            (safe_limit, safe_offset),
        ).fetchall()
    return [_row_to_trade(row) for row in rows]


def journal_analytics() -> dict[str, Any]:
    return calculate_journal_analytics(list_trades(limit=1000))

def list_experiments() -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute("select * from experiments order by created_at desc").fetchall()
        experiments = []
        for row in rows:
            item = dict(row)
            reviewed_since = connection.execute(
                "select count(*) from trades where result in ('WIN','LOSS','BE') and updated_at >= ?",
                (item["start_date"],),
            ).fetchone()[0]
            item["reviewedCount"] = int(reviewed_since)
            item["progress"] = min(item["sample_target"], int(reviewed_since))
            experiments.append(item)
        return experiments


def create_experiment(payload: dict[str, Any]) -> dict[str, Any]:
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z")
    experiment = {
        "id": str(uuid.uuid4()),
        "title": str(payload.get("title") or payload.get("behavior") or "Untitled experiment").strip(),
        "behavior": str(payload.get("behavior") or "").strip(),
        "hypothesis": str(payload.get("hypothesis") or "").strip(),
        "baseline_metric": str(payload.get("baselineMetric") or "").strip(),
        "target_metric": str(payload.get("targetMetric") or "").strip(),
        "sample_target": max(1, min(int(payload.get("sampleTarget") or 10), 100)),
        "start_date": now,
        "end_date": payload.get("endDate"),
        "status": "ACTIVE",
        "related_pattern_id": payload.get("relatedPatternId"),
        "notes": str(payload.get("notes") or "").strip(),
        "created_at": now,
        "completed_at": None,
    }
    with connect() as connection:
        connection.execute(
            """insert into experiments (id,title,behavior,hypothesis,baseline_metric,target_metric,sample_target,start_date,end_date,status,related_pattern_id,notes,created_at,completed_at)
               values (:id,:title,:behavior,:hypothesis,:baseline_metric,:target_metric,:sample_target,:start_date,:end_date,:status,:related_pattern_id,:notes,:created_at,:completed_at)""",
            experiment,
        )
    return next(item for item in list_experiments() if item["id"] == experiment["id"])


def update_experiment_status(experiment_id: str, status: str) -> dict[str, Any] | None:
    if status not in {"DRAFT", "ACTIVE", "PAUSED", "COMPLETED", "ARCHIVED"}:
        raise ValueError("Invalid experiment status")
    completed_at = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')" if status == "COMPLETED" else "null"
    with connect() as connection:
        connection.execute(f"update experiments set status = ?, completed_at = {completed_at} where id = ?", (status, experiment_id))
    return next((item for item in list_experiments() if item["id"] == experiment_id), None)


def delete_trade(trade_id: str) -> bool:
    with connect() as connection:
        row = connection.execute("select screenshot_path from trades where id = ?", (trade_id,)).fetchone()
        if not row:
            return False
        connection.execute("delete from ai_insights where source_trade_ids_json like ?", (f"%{trade_id}%",))
        connection.execute("delete from trades where id = ?", (trade_id,))
    screenshot_path = row[0]
    if screenshot_path:
        candidate = (DATA_DIR / screenshot_path).resolve()
        if candidate.parent == SCREENSHOT_DIR.resolve() and candidate.is_file():
            candidate.unlink()
    return True


def save_ai_insight(
    trade_id: str,
    summary: str,
    action: str | None,
    model: str,
    prompt_version: str,
) -> dict[str, Any]:
    insight = {
        "id": str(uuid.uuid4()),
        "insightType": "POST_TRADE_REFLECTION",
        "sourceTradeIds": [trade_id],
        "summary": summary,
        "action": action,
        "model": model,
        "promptVersion": prompt_version,
    }
    with connect() as connection:
        connection.execute(
            """insert into ai_insights (
                id, insight_type, source_trade_ids_json, summary, action,
                model, prompt_version
            ) values (?, ?, ?, ?, ?, ?, ?)""",
            (
                insight["id"],
                insight["insightType"],
                json.dumps(insight["sourceTradeIds"]),
                summary,
                action,
                model,
                prompt_version,
            ),
        )
    return insight


def latest_ai_insight(trade_id: str) -> dict[str, Any] | None:
    with connect() as connection:
        rows = connection.execute(
            """select id, insight_type, source_trade_ids_json, summary,
                      action, model, prompt_version, created_at
               from ai_insights order by created_at desc"""
        ).fetchall()

    for row in rows:
        source_trade_ids = json.loads(row["source_trade_ids_json"] or "[]")
        if trade_id not in source_trade_ids:
            continue
        return {
            "id": row["id"],
            "insightType": row["insight_type"],
            "sourceTradeIds": source_trade_ids,
            "summary": row["summary"],
            "action": row["action"],
            "model": row["model"],
            "promptVersion": row["prompt_version"],
            "createdAt": row["created_at"],
        }

    return None

def save_ai_trade_reflection(
    trade_id: str,
    trade_updated_at: str,
    summary: str,
    key_observations: list[str],
    action: str | None,
    unknowns: list[str],
    evidence_refs: list[str],
    model: str,
    prompt_version: str,
    contract_version: int = 1,
) -> dict[str, Any]:
    reflection = {
        "id": str(uuid.uuid4()),
        "tradeId": trade_id,
        "tradeUpdatedAt": trade_updated_at,
        "summary": summary,
        "keyObservations": key_observations,
        "action": action,
        "unknowns": unknowns,
        "evidenceRefs": evidence_refs,
        "model": model,
        "promptVersion": prompt_version,
        "contractVersion": contract_version,
    }

    with connect() as connection:
        row = connection.execute(
            """insert into ai_trade_reflections (
                id, trade_id, summary, key_observations_json, action,
                unknowns_json, evidence_refs_json, model, prompt_version,
                contract_version, trade_updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            returning created_at""",
            (
                reflection["id"],
                trade_id,
                summary,
                json.dumps(key_observations),
                action,
                json.dumps(unknowns),
                json.dumps(evidence_refs),
                model,
                prompt_version,
                contract_version,
                trade_updated_at,
            ),
        ).fetchone()

    reflection["createdAt"] = row["created_at"]
    return reflection


def latest_ai_trade_reflection(trade_id: str) -> dict[str, Any] | None:
    with connect() as connection:
        row = connection.execute(
            """select id, trade_id, summary, key_observations_json, action,
                      unknowns_json, evidence_refs_json, model, prompt_version,
                      contract_version, created_at
               from ai_trade_reflections
               where trade_id = ?
               order by created_at desc
               limit 1""",
            (trade_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "tradeId": row["trade_id"],
        "summary": row["summary"],
        "keyObservations": json.loads(row["key_observations_json"] or "[]"),
        "action": row["action"],
        "unknowns": json.loads(row["unknowns_json"] or "[]"),
        "evidenceRefs": json.loads(row["evidence_refs_json"] or "[]"),
        "model": row["model"],
        "promptVersion": row["prompt_version"],
        "contractVersion": row["contract_version"],
        "createdAt": row["created_at"],
    }


def queue_storage_job(trade_id: str, operation: str, payload: dict[str, Any], error: str) -> str:
    """Keep a bounded, recoverable Notion retry payload; callers must surface it."""
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z")
    job_id = str(uuid.uuid4())
    with connect() as connection:
        count = connection.execute("select count(*) from storage_outbox").fetchone()[0]
        if count >= 100:
            raise ValueError("The Notion retry queue is full. Export the pending trades before trying again.")
        connection.execute(
            """insert into storage_outbox(job_id,trade_id,operation,payload_json,attempts,status,created_at,next_retry_at,last_error)
               values(?,?,?,?,0,'PENDING',?,?,?)""",
            (job_id, trade_id, operation, json.dumps(payload), now, now, error[:500]),
        )
    return job_id


def storage_outbox_status() -> dict[str, Any]:
    with connect() as connection:
        row = connection.execute("select count(*) from storage_outbox where status in ('PENDING','RETRYING','FAILED')").fetchone()
        return {"pending": int(row[0]), "max": 100}


def provider_cache_status(provider: str = "notion") -> dict[str, Any]:
    with connect() as connection:
        row = connection.execute(
            "select count(*), coalesce(sum(length(metadata_json)), 0), max(touched_at) from provider_cache where provider = ?",
            (provider,),
        ).fetchone()
    return {"records": int(row[0]), "bytes": int(row[1]), "lastTouchedAt": row[2], "maxRecords": 250}


def clear_provider_cache(provider: str = "notion") -> int:
    with connect() as connection:
        cursor = connection.execute("delete from provider_cache where provider = ?", (provider,))
        return int(cursor.rowcount or 0)


def list_storage_jobs(limit: int = 20) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute("select * from storage_outbox order by created_at asc limit ?", (max(1, min(int(limit), 100)),)).fetchall()
    return [dict(row) for row in rows]


def complete_storage_job(job_id: str) -> None:
    with connect() as connection:
        connection.execute("delete from storage_outbox where job_id = ?", (job_id,))


def fail_storage_job(job_id: str, error: str) -> None:
    with connect() as connection:
        connection.execute("update storage_outbox set attempts = attempts + 1, status = 'RETRYING', last_error = ?, next_retry_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '+5 minutes') where job_id = ?", (error[:500], job_id))


def create_memory_finding(finding: dict[str, Any]) -> dict[str, Any]:
    """Persist a new Memory finding and its canonical supporting trades."""
    required = (
        "id",
        "type",
        "statement",
        "sampleSize",
        "evidenceStrength",
        "firstObserved",
        "status",
        "contractVersion",
    )
    missing = [key for key in required if finding.get(key) is None]
    if missing:
        raise ValueError(f"Missing memory finding fields: {', '.join(missing)}")

    supporting_trade_ids = list(dict.fromkeys(
        trade_id
        for trade_id in finding.get("supportingTradeIds", [])
        if trade_id is not None and str(trade_id).strip()
    ))

    with connect() as connection:
        connection.execute(
            """insert into memory_findings (
                id, type, statement, sample_size, evidence_strength,
                first_observed, last_verified, status, contract_version
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                finding["id"],
                finding["type"],
                finding["statement"],
                int(finding["sampleSize"]),
                finding["evidenceStrength"],
                finding["firstObserved"],
                finding.get("lastVerified"),
                finding["status"],
                int(finding["contractVersion"]),
            ),
        )

        for trade_id in supporting_trade_ids:
            connection.execute(
                """insert into memory_finding_trades (finding_id, trade_id)
                   values (?, ?)""",
                (finding["id"], trade_id),
            )

    result = get_memory_finding(finding["id"])
    if result is None:
        raise RuntimeError("Memory finding was inserted but could not be retrieved")
    return result


def get_memory_finding(finding_id: str) -> dict[str, Any] | None:
    """Return a Memory finding with its canonical supporting trade IDs."""
    with connect() as connection:
        row = connection.execute(
            """select id, type, statement, sample_size, evidence_strength,
                      first_observed, last_verified, status, contract_version,
                      created_at, updated_at
               from memory_findings
               where id = ?""",
            (finding_id,),
        ).fetchone()

        if row is None:
            return None

        trade_rows = connection.execute(
            """select trade_id
               from memory_finding_trades
               where finding_id = ?
               order by trade_id""",
            (finding_id,),
        ).fetchall()

    return {
        "id": row["id"],
        "type": row["type"],
        "statement": row["statement"],
        "sampleSize": row["sample_size"],
        "evidenceStrength": row["evidence_strength"],
        "firstObserved": row["first_observed"],
        "lastVerified": row["last_verified"],
        "status": row["status"],
        "contractVersion": row["contract_version"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "supportingTradeIds": [item["trade_id"] for item in trade_rows],
    }


def list_memory_findings(
    status: str | None = None,
    finding_type: str | None = None,
) -> list[dict[str, Any]]:
    """List Memory findings with optional deterministic filters."""
    clauses = []
    params: list[Any] = []

    if status is not None:
        clauses.append("status = ?")
        params.append(status)

    if finding_type is not None:
        clauses.append("type = ?")
        params.append(finding_type)

    where = f"where {' and '.join(clauses)}" if clauses else ""

    with connect() as connection:
        rows = connection.execute(
            f"""select id
                from memory_findings
                {where}
                order by first_observed asc, id asc""",
            params,
        ).fetchall()

    return [
        finding
        for row in rows
        if (finding := get_memory_finding(row["id"])) is not None
    ]


def save_memory_verification(
    finding_id: str,
    verification: dict[str, Any],
) -> dict[str, Any]:
    """Persist one immutable deterministic Memory verification result."""
    required = (
        "id",
        "verifiedAt",
        "status",
        "sampleSize",
        "evidenceStrength",
        "contractVersion",
    )
    missing = [key for key in required if verification.get(key) is None]
    if missing:
        raise ValueError(
            f"Missing memory verification fields: {', '.join(missing)}"
        )

    supporting_trade_ids = list(dict.fromkeys(
        trade_id
        for trade_id in verification.get("supportingTradeIds", [])
        if trade_id is not None and str(trade_id).strip()
    ))

    with connect() as connection:
        connection.execute(
            """insert into memory_verifications (
                id, finding_id, verified_at, status, sample_size,
                evidence_strength, supporting_trade_count,
                supporting_trade_ids_json, contract_version
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                verification["id"],
                finding_id,
                verification["verifiedAt"],
                verification["status"],
                int(verification["sampleSize"]),
                verification["evidenceStrength"],
                len(supporting_trade_ids),
                json.dumps(supporting_trade_ids),
                int(verification["contractVersion"]),
            ),
        )

        connection.execute(
            """update memory_findings
               set last_verified = ?, status = ?, sample_size = ?,
                   evidence_strength = ?, updated_at = strftime(
                       '%Y-%m-%dT%H:%M:%fZ', 'now'
                   )
               where id = ?""",
            (
                verification["verifiedAt"],
                verification["status"],
                int(verification["sampleSize"]),
                verification["evidenceStrength"],
                finding_id,
            ),
        )

    with connect() as connection:
        row = connection.execute(
            """select id, finding_id, verified_at, status, sample_size,
                      evidence_strength, supporting_trade_count,
                      supporting_trade_ids_json, contract_version, created_at
               from memory_verifications
               where id = ?""",
            (verification["id"],),
        ).fetchone()

    if row is None:
        raise RuntimeError("Memory verification was inserted but could not be retrieved")

    return {
        "id": row["id"],
        "findingId": row["finding_id"],
        "verifiedAt": row["verified_at"],
        "status": row["status"],
        "sampleSize": row["sample_size"],
        "evidenceStrength": row["evidence_strength"],
        "supportingTradeCount": row["supporting_trade_count"],
        "supportingTradeIds": json.loads(
            row["supporting_trade_ids_json"] or "[]"
        ),
        "contractVersion": row["contract_version"],
        "createdAt": row["created_at"],
    }


def list_memory_verifications(finding_id: str) -> list[dict[str, Any]]:
    """Return immutable verification history in newest-first order."""
    with connect() as connection:
        rows = connection.execute(
            """select id, finding_id, verified_at, status, sample_size,
                      evidence_strength, supporting_trade_count,
                      supporting_trade_ids_json, contract_version, created_at
               from memory_verifications
               where finding_id = ?
               order by verified_at desc, id desc""",
            (finding_id,),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "findingId": row["finding_id"],
            "verifiedAt": row["verified_at"],
            "status": row["status"],
            "sampleSize": row["sample_size"],
            "evidenceStrength": row["evidence_strength"],
            "supportingTradeCount": row["supporting_trade_count"],
            "supportingTradeIds": json.loads(
                row["supporting_trade_ids_json"] or "[]"
            ),
            "contractVersion": row["contract_version"],
            "createdAt": row["created_at"],
        }
        for row in rows
    ]


def challenge_memory_finding(finding_id: str) -> dict[str, Any] | None:
    """Mark a Memory finding as challenged without altering its evidence."""
    with connect() as connection:
        connection.execute(
            """update memory_findings
               set status = 'CHALLENGED',
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
               where id = ?""",
            (finding_id,),
        )

    return get_memory_finding(finding_id)


def update_memory_finding(
    finding_id: str,
    statement: str,
) -> dict[str, Any] | None:
    """Update a finding's statement while preserving identity and history."""
    statement = str(statement or "").strip()
    if not statement:
        raise ValueError("Memory finding statement is required")

    with connect() as connection:
        connection.execute(
            """update memory_findings
               set statement = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
               where id = ?""",
            (statement, finding_id),
        )

    return get_memory_finding(finding_id)


def retire_memory_finding(finding_id: str) -> dict[str, Any] | None:
    """Retire a Memory finding without deleting its evidence or history."""
    with connect() as connection:
        connection.execute(
            """update memory_findings
               set status = 'RETIRED',
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
               where id = ?""",
            (finding_id,),
        )

    return get_memory_finding(finding_id)
