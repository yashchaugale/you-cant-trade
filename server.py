import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from ai.providers.base import (
    AIProviderError,
    AIProviderResponseError,
    AIProviderUnavailableError,
)
from ai.service import (
    analyze_patterns,
    analyze_trade,
    analyze_trade_multi_agent,
    compare_trade,
    health as ai_health,
)
from database.local_database import (
    SCREENSHOT_DIR,
    get_trade,
    initialise,
    list_trades,
    journal_analytics,
    delete_trade,
    list_experiments,
    create_experiment,
    update_experiment_status,
    search_trades,
    similar_trades,
    latest_ai_insight,
    save_ai_insight,
    storage_stats,
    clear_provider_cache,
    upsert_trade,
    list_storage_jobs,
    complete_storage_job,
    fail_storage_job,
)
from services.storage import get_storage_provider, provider_status
from services.canonical_intelligence import assemble_canonical_intelligence
from services.pattern_discovery import discover_patterns, MIN_PATTERN_SAMPLE
from services.edge_map import build_edge_map
from services.leak_map import build_leak_map
from services.storage.base import StorageProviderError
from services.storage.credentials import clear_token, store_token
from services.storage.credentials import get_token
from services.storage.notion_client import NotionClient
from services.storage.notion_provider import clear_notion_caches
from services.storage.settings import notion_config, provider_name, set_setting

app = FastAPI()

initialise()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r"chrome-extension://.*|https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/trade-event")
async def trade_event(event: dict):
    try:
        provider = get_storage_provider()
        existing_trades = provider.list_trades(
            limit=provider.historical_candidate_limit()
        )
        canonical_trade = assemble_canonical_intelligence(
            event,
            existing_trades,
        )
        trade = provider.create_trade(canonical_trade)
    except StorageProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"status": "received", "trade": trade, "storage": provider_status()}


@app.get("/health")
async def health():
    storage = provider_status()
    local = storage_stats() if storage.get("provider") == "local" else {}
    return {"status": "ok", **local, "storage": storage}


@app.get("/storage/status")
async def storage_status():
    return provider_status()


@app.get("/storage/outbox")
async def storage_outbox():
    jobs = list_storage_jobs()
    return {"pending": [{"jobId": job["job_id"], "tradeId": job["trade_id"], "operation": job["operation"], "attempts": job["attempts"], "status": job["status"], "createdAt": job["created_at"], "lastError": job["last_error"]} for job in jobs]}


@app.delete("/storage/cache")
async def clear_storage_cache():
    provider = provider_name()
    removed = clear_provider_cache(provider)
    clear_notion_caches()
    return {"provider": provider, "clearedRecords": removed, "status": provider_status()}


@app.post("/storage/outbox/retry")
async def retry_storage_outbox():
    try:
        provider = get_storage_provider()
        if provider.name != "notion":
            return {"retried": 0, "pending": 0}
        retried = 0
        for job in list_storage_jobs():
            try:
                provider.create_trade(__import__("json").loads(job["payload_json"]), queue_on_failure=False)
                complete_storage_job(job["job_id"])
                retried += 1
            except (StorageProviderError, ValueError) as error:
                fail_storage_job(job["job_id"], str(error))
        return {"retried": retried, "pending": len(list_storage_jobs())}
    except StorageProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/storage/provider")
async def select_storage_provider(payload: dict):
    selected = str(payload.get("provider") or "").lower()
    if selected not in {"local", "notion"}:
        raise HTTPException(status_code=400, detail="Choose Local or Notion storage.")
    if selected == "notion":
        config = notion_config()
        if not config.get("databaseId") or not config.get("dataSourceId"):
            raise HTTPException(status_code=400, detail="Connect Notion and choose a trading data source first.")
    set_setting("storage_provider", selected)
    return provider_status()


@app.post("/storage/notion/connect")
async def connect_notion(payload: dict):
    token = str(payload.get("token") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Enter a Notion connection token.")
    try:
        identity = NotionClient(token).validate()
        persistence = store_token(token)
    except StorageProviderError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "CONNECTED", "workspace": identity.get("name") or identity.get("bot", {}).get("owner"), "credential": persistence, "token": None}


@app.post("/storage/notion/disconnect")
async def disconnect_notion():
    clear_token()
    set_setting("storage_provider", "local")
    return provider_status()


@app.get("/storage/notion/databases")
async def notion_databases(query: str = ""):
    try:
        return {"databases": NotionClient(get_token() or "").search_databases(query)}
    except StorageProviderError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/storage/notion/databases/{database_id}")
async def notion_database(database_id: str):
    try:
        database = NotionClient(get_token() or "").retrieve_database(database_id)
    except StorageProviderError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"database": database, "dataSources": database.get("data_sources", [])}


@app.post("/storage/notion/database-url")
async def notion_database_url(payload: dict):
    raw_url = str(payload.get("url") or "").strip()
    match = re.search(r"([0-9a-fA-F]{32}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(?:\?|$)", raw_url)
    if not match:
        raise HTTPException(status_code=400, detail="That does not look like a Notion database URL.")
    return await notion_database(match.group(1))


@app.get("/storage/notion/data-sources/{data_source_id}")
async def notion_data_source(data_source_id: str):
    try:
        source = NotionClient(get_token() or "").retrieve_data_source(data_source_id)
    except StorageProviderError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"dataSource": source}


@app.post("/storage/notion/configure")
async def configure_notion(payload: dict):
    database_id = str(payload.get("databaseId") or "").strip()
    data_source_id = str(payload.get("dataSourceId") or "").strip()
    if not database_id or not data_source_id:
        raise HTTPException(status_code=400, detail="Choose both a Notion database and data source.")
    try:
        source = NotionClient(get_token() or "").retrieve_data_source(data_source_id)
    except StorageProviderError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    set_setting("notion_database_id", database_id)
    set_setting("notion_data_source_id", data_source_id)
    set_setting("notion_database_name", payload.get("databaseName") or "Trading Journal")
    set_setting("notion_data_source_name", payload.get("dataSourceName") or "Trades")
    return {"status": "CONFIGURATION_REQUIRED", "schema": source.get("properties", {}), "provider": "notion"}


@app.post("/storage/notion/data-sources/{data_source_id}/create-fields")
async def create_notion_fields(data_source_id: str):
    try:
        client = NotionClient(get_token() or "")
        source = client.retrieve_data_source(data_source_id)
        existing = source.get("properties", {})
        aliases = {str(name).lower() for name in existing}
        fields = {}
        if "vf trade id" not in aliases:
            fields["VF Trade ID"] = {"rich_text": {}}
        for name, definition in {
            "Symbol": {"rich_text": {}}, "Timeframe": {"rich_text": {}}, "Exchange": {"rich_text": {}},
            "Direction": {"select": {"options": [{"name": "LONG"}, {"name": "SHORT"}]}},
            "Entry": {"number": {"format": "number"}}, "Stop Loss": {"number": {"format": "number"}},
            "Take Profit": {"number": {"format": "number"}}, "Exit Price": {"number": {"format": "number"}},
            "Planned R": {"number": {"format": "number"}}, "Actual R": {"number": {"format": "number"}},
            "Result": {"select": {"options": [{"name": "WIN"}, {"name": "LOSS"}, {"name": "BE"}]}},
            "Notes": {"rich_text": {}}, "Setup": {"rich_text": {}}, "Execution": {"rich_text": {}},
            "Session": {"select": {"options": [{"name": "ASIA"}, {"name": "LONDON"}, {"name": "NEW YORK"}, {"name": "OTHER"}]}},
            "Plan Adherence": {"select": {"options": [{"name": "FOLLOWED"}, {"name": "DEVIATED"}]}},
            "Emotions": {"multi_select": {}}, "Source": {"rich_text": {}}, "Status": {"select": {"options": [{"name": "CAPTURED"}, {"name": "REVIEWED"}]}},
            "You Can't Trade URL": {"url": {}}, "Captured At": {"date": {}}, "Chart Anchor Time": {"date": {}},
            "Chart Anchor Interval": {"rich_text": {}}, "Outcome Evidence Time": {"date": {}}, "Chart Screenshot": {"files": {}},
        }.items():
            if name.lower() not in aliases:
                fields[name] = definition
        updated = client.update_data_source_properties(data_source_id, fields) if fields else source
        clear_notion_caches()
    except StorageProviderError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "SCHEMA_UPDATED", "schema": updated.get("properties", {})}


@app.get("/trades")
async def trades(limit: int = 100, offset: int = 0):
    try:
        return {"trades": get_storage_provider().list_trades(limit=limit, offset=offset), "storage": provider_status()}
    except StorageProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/experiments")
async def experiments():
    return {"experiments": list_experiments()}


@app.post("/experiments")
async def new_experiment(payload: dict):
    if not payload.get("behavior"):
        raise HTTPException(status_code=400, detail="A behaviour is required")
    return {"experiment": create_experiment(payload)}


@app.patch("/experiments/{experiment_id}")
async def change_experiment_status(experiment_id: str, payload: dict):
    try:
        result = update_experiment_status(experiment_id, payload.get("status", ""))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"experiment": result}


@app.get("/patterns")
async def patterns():
    try:
        provider = get_storage_provider()
        trades = provider.list_trades(
            limit=provider.historical_candidate_limit()
        )
        return {
            "patterns": discover_patterns(
                trades,
                min_sample=MIN_PATTERN_SAMPLE,
            ),
            "sampleSize": len(trades),
            "minimumSample": MIN_PATTERN_SAMPLE,
        }
    except StorageProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/edge-map")
async def edge_map(
    dimension_a: str,
    dimension_b: str,
):
    allowed_dimensions = {
        "setup",
        "session",
        "direction",
        "market_regime",
        "structure_state",
    }

    if dimension_a not in allowed_dimensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported Edge Map dimension: {dimension_a}",
        )

    if dimension_b not in allowed_dimensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported Edge Map dimension: {dimension_b}",
        )

    if dimension_a == dimension_b:
        raise HTTPException(
            status_code=400,
            detail="Edge Map dimensions must be different",
        )

    try:
        provider = get_storage_provider()
        trades = provider.list_trades(
            limit=provider.historical_candidate_limit()
        )
        cells = build_edge_map(
            trades,
            dimension_a,
            dimension_b,
            min_sample=MIN_PATTERN_SAMPLE,
        )
        return {
            "dimensionA": dimension_a,
            "dimensionB": dimension_b,
            "cells": cells,
            "sampleSize": len(trades),
            "minimumSample": MIN_PATTERN_SAMPLE,
        }
    except StorageProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/leak-map")
async def leak_map():
    try:
        provider = get_storage_provider()
        trades = provider.list_trades(
            limit=provider.historical_candidate_limit()
        )

        leaks = build_leak_map(trades)

        return {
            "version": 1,
            "leaks": leaks,
            "sampleSize": len(trades),
        }
    except StorageProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error



@app.get("/analytics/summary")
async def analytics_summary():
    try:
        return get_storage_provider().get_statistics()
    except StorageProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/trades/{trade_id}/similar")
async def similar_trade_records(trade_id: str, limit: int = 10):
    try:
        provider = get_storage_provider()
        if provider.get_trade(trade_id) is None:
            raise HTTPException(status_code=404, detail="Trade not found")
        return {"trades": provider.get_similar_trades(trade_id, limit=limit)}
    except StorageProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

@app.get("/trades/{trade_id}/historical-context")
async def historical_trade_context(trade_id: str, limit: int = 10):
    try:
        provider = get_storage_provider()
        if provider.get_trade(trade_id) is None:
            raise HTTPException(status_code=404, detail="Trade not found")
        return {
            "historical": provider.get_historical_context(
                trade_id,
                limit=limit,
            )
        }
    except StorageProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/trades/search")
async def search_trade_records(q: str = "", limit: int = 50):
    try:
        return {"trades": get_storage_provider().search_trades(q, limit=limit), "query": q}
    except StorageProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/trades/{trade_id}")
async def trade(trade_id: str):
    try:
        record = get_storage_provider().get_trade(trade_id)
    except StorageProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    if record is None:
        raise HTTPException(status_code=404, detail="Trade not found")

    return {"trade": record}


@app.put("/trades/{trade_id}")
async def update_trade(trade_id: str, payload: dict):
    if payload.get("id") not in (None, trade_id):
        raise HTTPException(status_code=400, detail="Trade ID does not match the URL")

    payload["id"] = trade_id
    try:
        return {"trade": get_storage_provider().update_trade(trade_id, payload)}
    except StorageProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.delete("/trades/{trade_id}")
async def remove_trade(trade_id: str):
    try:
        deleted = get_storage_provider().delete_trade(trade_id)
    except StorageProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if not deleted:
        raise HTTPException(status_code=404, detail="Trade not found")
    return {"status": "deleted", "tradeId": trade_id}


@app.get("/screenshots/{filename}")
async def screenshot(filename: str):
    candidate = (SCREENSHOT_DIR / filename).resolve()
    if candidate.parent != SCREENSHOT_DIR.resolve() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Screenshot not found")

    return FileResponse(candidate)


@app.get("/ai/health")
async def local_ai_health():
    return ai_health()


@app.get("/ai/insights/{trade_id}")
async def trade_insight(trade_id: str):
    return {"insight": latest_ai_insight(trade_id)}


@app.post("/ai/compare/{trade_id}")
async def compare_trade_locally(trade_id: str):
    try:
        provider = get_storage_provider()
        target = provider.get_trade(trade_id)
        matches = provider.get_similar_trades(trade_id, limit=10)
    except StorageProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if target is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    try:
        result = compare_trade(target, matches)
    except AIProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"matches": matches, "insight": result}


@app.post("/ai/analyze-patterns")
async def analyze_patterns_locally():
    try:
        analytics = get_storage_provider().get_statistics()
    except StorageProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    try:
        result = analyze_patterns(analytics)
    except AIProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"analytics": analytics, "insight": result}


@app.post("/ai/analyze/{trade_id}")
async def analyze_trade_locally(trade_id: str):
    try:
        record = get_storage_provider().get_trade(trade_id)
    except StorageProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    if record is None:
        raise HTTPException(status_code=404, detail="Trade not found")

    try:
        result = analyze_trade(record)
    except AIProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    insight = {**result, "source": provider_name()}
    if provider_name() == "local":
        insight = save_ai_insight(trade_id, result["summary"], result["action"], result["model"], result["promptVersion"])
    return {"insight": insight}

@app.post("/ai/analyze-multi/{trade_id}")
async def analyze_trade_multi_locally(trade_id: str):
    """Run the V1 multi-agent post-trade reasoning pipeline."""

    try:
        record = get_storage_provider().get_trade(trade_id)
    except StorageProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    if record is None:
        raise HTTPException(status_code=404, detail="Trade not found")

    try:
        result = analyze_trade_multi_agent(record)
    except AIProviderError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error

    

    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765)
