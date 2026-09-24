const LOCAL_API_BASE = "http://127.0.0.1:8765";
const REQUEST_TIMEOUT_MS = 5000;


export class LocalApiUnavailableError extends Error {

    constructor(message = "The local You Can't Trade service is unavailable.") {

        super(message);
        this.name = "LocalApiUnavailableError";
    }
}


async function request(path, options = {}) {

    const controller = new AbortController();
    const timeout = setTimeout(
        () => controller.abort(),
        REQUEST_TIMEOUT_MS
    );

    try {
        const response = await fetch(
            `${LOCAL_API_BASE}${path}`,
            {
                ...options,
                signal: controller.signal,
                headers: {
                    "Content-Type": "application/json",
                    ...(options.headers || {})
                }
            }
        );

        if (!response.ok) {
            const detail = await response.text();
            throw new Error(detail || `Local service returned ${response.status}.`);
        }

        return response.json();
    } catch (error) {
        if (error.name === "AbortError" || error instanceof TypeError) {
            throw new LocalApiUnavailableError();
        }

        throw error;
    } finally {
        clearTimeout(timeout);
    }
}


function withScreenshotUrl(trade) {

    if (
        trade &&
        typeof trade.chartAnchorTime === "string" &&
        Number.isFinite(Number(trade.chartAnchorTime))
    ) {
        trade = {
            ...trade,
            chartAnchorTime: Number(trade.chartAnchorTime)
        };
    }

    if (
        trade &&
        trade.screenshotPath &&
        !trade.screenshot
    ) {
        return {
            ...trade,
            screenshot: `${LOCAL_API_BASE}/screenshots/${encodeURIComponent(
                trade.screenshotPath.split("/").pop()
            )}`
        };
    }

    return trade;
}


export async function getLocalTrades() {

    const result = await request("/trades?limit=1000");
    return result.trades.map(withScreenshotUrl);
}


export async function getLocalExperiments() {
    const result = await request("/experiments");
    return result.experiments;
}


export async function createLocalExperiment(payload) {
    const result = await request("/experiments", { method: "POST", body: JSON.stringify(payload) });
    return result.experiment;
}


export async function updateLocalExperimentStatus(experimentId, status) {
    const result = await request(`/experiments/${encodeURIComponent(experimentId)}`, { method: "PATCH", body: JSON.stringify({ status }) });
    return result.experiment;
}

export async function getStorageStatus() {
    return request("/storage/status");
}

export async function selectStorageProvider(provider) {
    return request("/storage/provider", { method: "POST", body: JSON.stringify({ provider }) });
}

export async function connectNotion(token) {
    return request("/storage/notion/connect", { method: "POST", body: JSON.stringify({ token }) });
}

export async function getNotionDatabases(query = "") {
    const result = await request(`/storage/notion/databases?query=${encodeURIComponent(query)}`);
    return result.databases || [];
}

export async function getNotionDatabase(databaseId) {
    return request(`/storage/notion/databases/${encodeURIComponent(databaseId)}`);
}

export async function getNotionDataSource(dataSourceId) {
    return request(`/storage/notion/data-sources/${encodeURIComponent(dataSourceId)}`);
}

export async function configureNotion(payload) {
    return request("/storage/notion/configure", { method: "POST", body: JSON.stringify(payload) });
}

export async function createNotionFields(dataSourceId) {
    return request(`/storage/notion/data-sources/${encodeURIComponent(dataSourceId)}/create-fields`, { method: "POST" });
}

export async function disconnectNotion() {
    return request("/storage/notion/disconnect", { method: "POST" });
}

export async function clearStorageCache() {
    return request("/storage/cache", { method: "DELETE" });
}

export async function retryStorageOutbox() {
    return request("/storage/outbox/retry", { method: "POST" });
}


export async function getLocalAnalytics() {
    return request("/analytics/summary");
}


export async function getLocalPatterns() {
    return request("/patterns");
}


export async function getLocalEdgeMap(dimensionA, dimensionB) {
    const params = new URLSearchParams({
        dimension_a: dimensionA,
        dimension_b: dimensionB,
    });

    return request(`/edge-map?${params.toString()}`);
}


export async function analyzeLocalPatterns() {
    const result = await request("/ai/analyze-patterns", { method: "POST" });
    return result;
}


export async function searchLocalTrades(query) {
    const result = await request(
        `/trades/search?q=${encodeURIComponent(query)}&limit=200`
    );
    return result.trades.map(withScreenshotUrl);
}


export async function getLocalStorageUsage() {

    const result = await request("/health");
    return {
        bytes: result.bytes || 0,
        limitBytes: Number.POSITIVE_INFINITY,
        percent: 0,
        tradeCount: result.tradeCount || result.storage?.tradeCount || 0,
        provider: result.storage?.provider || "local"
    };
}


export async function saveLocalTrade(trade) {

    const result = await request(
        "/trade-event",
        {
            method: "POST",
            body: JSON.stringify(trade)
        }
    );

    return withScreenshotUrl(result.trade);
}


export async function deleteLocalTrade(tradeId) {
    return request(`/trades/${encodeURIComponent(tradeId)}`, { method: "DELETE" });
}


export async function updateLocalTrade(trade) {

    const result = await request(
        `/trades/${encodeURIComponent(trade.id)}`,
        {
            method: "PUT",
            body: JSON.stringify(trade)
        }
    );

    return withScreenshotUrl(result.trade);
}


export async function getLocalAIHealth() {

    return request("/ai/health");
}


export async function compareLocalTrade(tradeId) {
    const result = await request(`/ai/compare/${encodeURIComponent(tradeId)}`, { method: "POST" });
    return result.insight;
}


export async function getSimilarLocalTrades(tradeId) {
    const result = await request(`/trades/${encodeURIComponent(tradeId)}/similar`);
    return result.trades.map(withScreenshotUrl);
}

export async function getHistoricalLocalContext(tradeId) {
    const result = await request(
        `/trades/${encodeURIComponent(tradeId)}/historical-context`
    );

    return result.historical;
}


export async function getLocalInsight(tradeId) {

    const result = await request(
        `/ai/insights/${encodeURIComponent(tradeId)}`
    );
    return result.insight;
}


export async function analyzeLocalTrade(tradeId) {

    const result = await request(
        `/ai/analyze/${encodeURIComponent(tradeId)}`,
        { method: "POST" }
    );
    return result.insight;
}


export async function getLocalLeakMap() {
    return request("/leak-map");
}


export async function getLocalCompare(currentCount, previousCount) {
    const params = new URLSearchParams({
        current_count: String(currentCount),
        previous_count: String(previousCount),
    });

    return request(`/compare?${params.toString()}`);
}


export async function getLocalMemory() {
    return request("/memory");
}

export async function getLocalMemoryFinding(findingId) {
    return request(`/memory/${encodeURIComponent(findingId)}`);
}

export async function challengeLocalMemory(findingId) {
    return request(`/memory/${encodeURIComponent(findingId)}/challenge`, {
        method: "POST",
    });
}

export async function updateLocalMemory(findingId, statement) {
    return request(`/memory/${encodeURIComponent(findingId)}`, {
        method: "PATCH",
        body: JSON.stringify({ statement }),
    });
}

export async function recheckLocalMemory(findingId, payload) {
    return request(`/memory/${encodeURIComponent(findingId)}/recheck`, {
        method: "POST",
        body: JSON.stringify(payload),
    });
}

export async function retireLocalMemory(findingId) {
    return request(`/memory/${encodeURIComponent(findingId)}/retire`, {
        method: "POST",
    });
}
