import {
    getTrades,
    getStorageUsage,
    updateTrade,
    deleteTrade
} from "../services/storageService.js";
import {
    analyzeLocalTrade,
    getLocalInsight,
    LocalApiUnavailableError,
    searchLocalTrades,
    getLocalAnalytics,
    getLocalPatterns,
    getLocalEdgeMap,
    getLocalLeakMap,
    getLocalCompare,
    getLocalMemory,
    getLocalMemoryFinding,
    challengeLocalMemory,
    updateLocalMemory,
    recheckLocalMemory,
    retireLocalMemory,
    analyzeLocalPatterns,
    getSimilarLocalTrades,
    compareLocalTrade,
    getLocalExperiments,
    createLocalExperiment,
    updateLocalExperimentStatus,
    getStorageStatus,
    selectStorageProvider,
    connectNotion,
    getNotionDatabases,
    getNotionDatabase,
    configureNotion,
    createNotionFields,
    disconnectNotion,
    clearStorageCache,
    retryStorageOutbox
} from "../services/localApiService.js";

let trades = [];
let selectedTradeId = null;
let selectedResult = null;
let searchQuery = "";
let searchResultIds = null;
let searchTimer = null;
let outboxRetryInFlight = false;
let edgeMapPayload = null;
let edgeMapSelectedTradeIds = null;
let edgeMapComparisonCells = [];
let leakMapPayload = null;
let comparePayload = null;
let memoryPayload = null;

const modal = document.getElementById("tradeModal");
const tradeGrid = document.getElementById("tradeGrid");
const emptyState = document.getElementById("emptyState");
const weeklyReviewContent = document.getElementById("weeklyReviewContent");
const onboarding = document.getElementById("onboarding");
const tradeSearch = document.getElementById("tradeSearch");
const clearSearch = document.getElementById("clearSearch");
const searchStatus = document.getElementById("searchStatus");
const patternReviewContent = document.getElementById("patternReviewContent");
const patternReviewStatus = document.getElementById("patternReviewStatus");
const edgeMapContent = document.getElementById("edgeMapContent");
const edgeMapStatus = document.getElementById("edgeMapStatus");
const edgeMapDimensionSelect = document.getElementById("edgeMapDimensionSelect");
const leakMapContent = document.getElementById("leakMapContent");
const leakMapStatus = document.getElementById("leakMapStatus");
const compareContent = document.getElementById("compareContent");
const compareStatus = document.getElementById("compareStatus");
const compareCurrentCount = document.getElementById("compareCurrentCount");
const comparePreviousCount = document.getElementById("comparePreviousCount");
const memoryContent = document.getElementById("memoryContent");
const memoryStatus = document.getElementById("memoryStatus");
const memoryDetails = document.getElementById("memoryDetails");
const memoryDetailsTitle = document.getElementById("memoryDetailsTitle");
const memoryDetailsContent = document.getElementById("memoryDetailsContent");
const closeMemoryDetails = document.getElementById("closeMemoryDetails");
const leakDetails = document.getElementById("leakDetails");
const leakDetailsTitle = document.getElementById("leakDetailsTitle");
const leakDetailsContent = document.getElementById("leakDetailsContent");
const closeLeakDetails = document.getElementById("closeLeakDetails");

function renderEdgeMapComparison(container) {
    if (!container || edgeMapComparisonCells.length !== 2) {
        return;
    }

    const [first, second] = edgeMapComparisonCells;

    const section = document.createElement("section");
    section.className = "edge-map-comparison";
    section.setAttribute("aria-labelledby", "edgeMapComparisonTitle");

    const title = document.createElement("h3");
    title.id = "edgeMapComparisonTitle";
    title.textContent = "Comparison";
    section.appendChild(title);

    const table = document.createElement("table");
    table.className = "edge-map-comparison-table";

    const head = document.createElement("thead");
    const headRow = document.createElement("tr");

    ["Metric", `${first.valueA} × ${first.valueB}`, `${second.valueA} × ${second.valueB}`]
        .forEach(text => {
            const cell = document.createElement("th");
            cell.scope = "col";
            cell.textContent = text;
            headRow.appendChild(cell);
        });

    head.appendChild(headRow);
    table.appendChild(head);

    const body = document.createElement("tbody");
    const formatValue = (value, formatter) =>
        value == null ? "—" : formatter(value);

    const rows = [
        ["Sample", first.sampleSize, second.sampleSize, value => String(value)],
        ["Win rate", first.winRate, second.winRate, value => `${(Number(value) * 100).toFixed(1)}%`],
        ["Average R", first.averageR, second.averageR, value => `${Number(value).toFixed(2)}R`],
        ["Expectancy", first.expectancy, second.expectancy, value => `${Number(value).toFixed(2)}R`],
        [
            "Actual R coverage",
            first.evidenceStrength?.actualRCoverage,
            second.evidenceStrength?.actualRCoverage,
            value => `${(Number(value) * 100).toFixed(0)}%`
        ],
        [
            "Evidence",
            first.evidenceStrength?.level,
            second.evidenceStrength?.level,
            value => String(value)
        ],
    ];

    rows.forEach(([label, firstValue, secondValue, formatter]) => {
        const row = document.createElement("tr");

        const labelCell = document.createElement("th");
        labelCell.scope = "row";
        labelCell.textContent = label;
        row.appendChild(labelCell);

        [firstValue, secondValue].forEach(value => {
            const cell = document.createElement("td");
            cell.textContent = formatValue(value, formatter);
            row.appendChild(cell);
        });

        body.appendChild(row);
    });

    table.appendChild(body);
    section.appendChild(table);
    container.appendChild(section);
}

function renderEdgeMap(payload) {
    if (!edgeMapContent || !edgeMapStatus) {
        return;
    }

    edgeMapContent.replaceChildren();

    const cells = Array.isArray(payload?.cells) ? payload.cells : [];
    const minimumSample = payload?.minimumSample || 3;

    const labels = {
        setup: "Setup",
        session: "Session",
        direction: "Direction",
        market_regime: "Regime",
        structure_state: "Structure",
    };

    edgeMapStatus.textContent =
        `${cells.length} condition${cells.length === 1 ? "" : "s"} · minimum sample ${minimumSample}`;

    if (!cells.length) {
        const empty = document.createElement("p");
        empty.className = "pattern-empty";
        empty.textContent = "No Edge Map cells meet the minimum sample yet.";
        edgeMapContent.appendChild(empty);
        return;
    }

    const grid = document.createElement("div");
    grid.className = "edge-map-grid";

    cells.forEach(cell => {
        const card = document.createElement("article");
        card.className = "edge-map-cell";
        card.tabIndex = 0;
        card.setAttribute("role", "button");
        card.setAttribute(
            "aria-label",
            `Open supporting trade for ${cell.valueA} × ${cell.valueB}`
        );

        const openSupportingTrade = () => {
            const tradeIds = Array.isArray(cell.sourceTradeIds)
                ? cell.sourceTradeIds
                : [];

            if (!tradeIds.length) {
                return;
            }

            edgeMapSelectedTradeIds = new Set(tradeIds);
            renderTradeGrid();

            const firstTradeId = tradeIds[0];
            if (firstTradeId) {
                openTrade(firstTradeId);
            }
        };

        card.addEventListener("click", openSupportingTrade);
        card.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openSupportingTrade();
            }
        });

        const heading = document.createElement("div");
        heading.className = "edge-map-cell-heading";

        const title = document.createElement("h3");
        title.className = "edge-map-cell-title";
        title.textContent =
            `${cell.valueA} × ${cell.valueB}`;

        const evidence = document.createElement("span");
        evidence.className = "review-period";
        evidence.textContent =
            cell.evidenceStrength?.level || "UNKNOWN";

        heading.append(title, evidence);
        card.appendChild(heading);

        const dimensions = document.createElement("p");
        dimensions.className = "edge-map-cell-meta";
        dimensions.textContent =
            `${labels[cell.dimensionA] || cell.dimensionA} × ${labels[cell.dimensionB] || cell.dimensionB}`;
        card.appendChild(dimensions);

        const metrics = document.createElement("div");
        metrics.className = "edge-map-cell-metrics";

        const addMetric = (label, value) => {
            const metric = document.createElement("div");
            metric.className = "edge-map-cell-metric";

            const metricLabel = document.createElement("span");
            metricLabel.textContent = label;

            const metricValue = document.createElement("strong");
            metricValue.textContent = value;

            metric.append(metricLabel, metricValue);
            metrics.appendChild(metric);
        };

        addMetric(
            "Sample",
            String(cell.sampleSize ?? "—")
        );

        addMetric(
            "Win rate",
            cell.winRate == null
                ? "—"
                : `${(Number(cell.winRate) * 100).toFixed(1)}%`
        );

        addMetric(
            "Average R",
            cell.averageR == null
                ? "—"
                : `${Number(cell.averageR).toFixed(2)}R`
        );

        addMetric(
            "Expectancy",
            cell.expectancy == null
                ? "—"
                : `${Number(cell.expectancy).toFixed(2)}R`
        );

        metrics.appendChild(document.createElement("div"));
        card.appendChild(metrics);

        const coverage = document.createElement("p");
        coverage.className = "edge-map-cell-evidence";
        coverage.textContent =
            `Actual R coverage: ${
                cell.evidenceStrength?.actualRCoverage == null
                    ? "—"
                    : `${(Number(cell.evidenceStrength.actualRCoverage) * 100).toFixed(0)}%`
            }`;

        card.appendChild(coverage);

        const compareButton = document.createElement("button");
        compareButton.type = "button";
        compareButton.className = "edge-map-compare-button";
        compareButton.textContent = "Compare";
        compareButton.addEventListener("click", event => {
            event.stopPropagation();

            const index = edgeMapComparisonCells.indexOf(cell);
            if (index >= 0) {
                edgeMapComparisonCells.splice(index, 1);
            } else if (edgeMapComparisonCells.length < 2) {
                edgeMapComparisonCells.push(cell);
            }

            renderEdgeMap(edgeMapPayload);
        });

        card.appendChild(compareButton);
        grid.appendChild(card);
    });

    edgeMapContent.appendChild(grid);
    renderEdgeMapComparison(edgeMapContent);
}


async function loadEdgeMap() {
    if (!edgeMapContent || !edgeMapStatus || !edgeMapDimensionSelect) {
        return;
    }

    const [dimensionA, dimensionB] = edgeMapDimensionSelect.value.split("|");

    if (
        edgeMapPayload &&
        (
            edgeMapPayload.dimensionA !== dimensionA ||
            edgeMapPayload.dimensionB !== dimensionB
        )
    ) {
        edgeMapComparisonCells = [];
    }

    edgeMapStatus.textContent = "Loading historical conditions…";
    edgeMapContent.replaceChildren();

    const loading = document.createElement("p");
    loading.className = "pattern-empty";
    loading.textContent = "Loading deterministic Edge Map…";
    edgeMapContent.appendChild(loading);

    try {
        const payload = await getLocalEdgeMap(dimensionA, dimensionB);
        edgeMapPayload = payload;
        renderEdgeMap(payload);
    } catch (error) {
        edgeMapPayload = null;
        edgeMapStatus.textContent = "Local service unavailable";
        edgeMapContent.replaceChildren();

        const empty = document.createElement("p");
        empty.className = "pattern-empty";
        empty.textContent = "Start the local service to load the Edge Map.";
        edgeMapContent.appendChild(empty);
    }
}



function renderLeakMap(payload) {
    if (!leakMapContent || !leakMapStatus) {
        return;
    }

    leakMapContent.replaceChildren();

    const leaks = Array.isArray(payload?.leaks) ? payload.leaks : [];
    const sampleSize = Number(payload?.sampleSize || 0);

    leakMapStatus.textContent =
        `${sampleSize} trade${sampleSize === 1 ? "" : "s"} analysed`;

    if (!leaks.length) {
        const empty = document.createElement("p");
        empty.className = "pattern-empty";
        empty.textContent = "No leak measurements are available yet.";
        leakMapContent.appendChild(empty);
        return;
    }

    const grid = document.createElement("div");
    grid.className = "leak-map-grid";

    leaks.forEach(leak => {
        const card = document.createElement("article");
        card.className = "leak-map-card";
        card.tabIndex = 0;
        card.setAttribute("role", "button");

        const heading = document.createElement("div");
        heading.className = "leak-map-card-heading";

        const title = document.createElement("h3");
        title.className = "leak-map-card-title";
        title.textContent = leak.label || leak.type;

        const evidence = document.createElement("span");
        evidence.className = "review-period";
        evidence.textContent = leak.evidenceStrength || "UNKNOWN";

        heading.append(title, evidence);
        card.appendChild(heading);

        const trend = document.createElement("p");
        trend.className = "leak-map-card-trend";
        trend.textContent = `Trend: ${formatLeakTrend(leak.trend)}`;
        card.appendChild(trend);

        const count = document.createElement("div");
        count.className = "leak-map-card-count";
        count.innerHTML = `<strong>${Number(leak.occurrenceCount || 0)}</strong><span>occurrences</span>`;
        card.appendChild(count);

        const metrics = document.createElement("div");
        metrics.className = "leak-map-card-metrics";

        const addMetric = (label, value) => {
            const item = document.createElement("div");
            item.className = "leak-map-card-metric";

            const itemLabel = document.createElement("span");
            itemLabel.textContent = label;

            const itemValue = document.createElement("strong");
            itemValue.textContent = value;

            item.append(itemLabel, itemValue);
            metrics.appendChild(item);
        };

        addMetric(
            "R impact",
            leak.rImpact == null ? "—" : `${Number(leak.rImpact).toFixed(2)}R`
        );

        addMetric(
            "R coverage",
            `${(Number(leak.actualRCoverage || 0) * 100).toFixed(0)}%`
        );

        addMetric(
            "Trades",
            String(Array.isArray(leak.supportingTradeIds) ? leak.supportingTradeIds.length : 0)
        );

        card.appendChild(metrics);

        const note = document.createElement("p");
        note.className = "leak-map-card-note";

        if (leak.occurrenceCount === 0) {
            note.textContent = "No explicit occurrences recorded.";
        } else if (leak.rImpact == null) {
            note.textContent = "R impact unavailable from current trade data.";
        } else {
            note.textContent = "Historical measurement only.";
        }

        card.appendChild(note);

        const openDetails = () => openLeakDetails(leak);
        card.addEventListener("click", openDetails);
        card.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openDetails();
            }
        });

        grid.appendChild(card);
    });

    leakMapContent.appendChild(grid);
}



async function loadCompare() {
    if (
        !compareContent ||
        !compareStatus ||
        !compareCurrentCount ||
        !comparePreviousCount
    ) {
        return;
    }

    const currentCount = Number(compareCurrentCount.value);
    const previousCount = Number(comparePreviousCount.value);

    compareStatus.textContent = "Loading historical comparison…";
    compareContent.replaceChildren();

    const loading = document.createElement("p");
    loading.className = "pattern-empty";
    loading.textContent = "Loading deterministic comparison…";
    compareContent.appendChild(loading);

    try {
        comparePayload = await getLocalCompare(
            currentCount,
            previousCount,
        );

        renderCompare(comparePayload);
    } catch (error) {
        comparePayload = null;
        compareStatus.textContent = "Local service unavailable";
        compareContent.replaceChildren();

        const empty = document.createElement("p");
        empty.className = "pattern-empty";
        empty.textContent = "Start the local service to load the comparison.";
        compareContent.appendChild(empty);
    }
}


function bindCompareControls() {
    if (!compareCurrentCount || !comparePreviousCount) {
        return;
    }

    compareCurrentCount.addEventListener("change", loadCompare);
    comparePreviousCount.addEventListener("change", loadCompare);
}


function formatComparePercent(value) {
    return value == null ? "—" : `${(Number(value) * 100).toFixed(1)}%`;
}


function formatCompareR(value) {
    return value == null ? "—" : `${Number(value).toFixed(2)}R`;
}


function formatCompareChange(value, formatter = formatComparePercent) {
    return value == null ? "—" : formatter(value);
}


function renderCompareMetric(label, current, previous, change, formatter) {
    const card = document.createElement("article");
    card.className = "compare-metric-card";

    const title = document.createElement("span");
    title.className = "compare-metric-label";
    title.textContent = label;

    const values = document.createElement("div");
    values.className = "compare-metric-values";

    const currentValue = document.createElement("strong");
    currentValue.textContent = formatter(current);

    const previousValue = document.createElement("span");
    previousValue.textContent = `Previous ${formatter(previous)}`;

    const delta = document.createElement("span");
    delta.className = "compare-metric-change";
    delta.textContent = `Δ ${formatCompareChange(change, formatter)}`;

    values.append(currentValue, previousValue, delta);
    card.append(title, values);

    return card;
}


function renderCompareTradeLinks(container, tradeIds, label = "Supporting trades") {
    if (!container || !Array.isArray(tradeIds) || !tradeIds.length) {
        return;
    }

    const section = document.createElement("section");
    section.className = "compare-supporting";

    const heading = document.createElement("h4");
    heading.textContent = `${label} · ${tradeIds.length}`;
    section.appendChild(heading);

    const list = document.createElement("div");
    list.className = "compare-trade-list";

    tradeIds.forEach(tradeId => {
        const trade = trades.find(item => item.id === tradeId);
        const button = document.createElement("button");
        button.type = "button";
        button.className = "compare-trade-row";

        const identity = document.createElement("span");
        identity.textContent = trade
            ? `${trade.symbol || "Trade"} · ${trade.direction || "—"}`
            : tradeId;

        const meta = document.createElement("span");
        meta.textContent = trade
            ? `${trade.result || "UNREVIEWED"} · ${formatDate(trade.timestamp)}`
            : tradeId;

        button.append(identity, meta);
        button.addEventListener("click", () => openTrade(tradeId));
        list.appendChild(button);
    });

    section.appendChild(list);
    container.appendChild(section);
}


function renderCompareChangeSummary(payload, container) {
    const changes = payload?.changes || {};

    const section = document.createElement("section");
    section.className = "compare-highlights";

    const title = document.createElement("h3");
    title.textContent = "Largest changes";
    section.appendChild(title);

    const grid = document.createElement("div");
    grid.className = "compare-highlight-grid";

    const formatMetricValue = (field, value) => {
        if (field === "winRate") {
            return formatComparePercent(value);
        }

        if (field === "averageR" || field === "expectancy") {
            return formatCompareR(value);
        }

        return value == null ? "—" : String(value);
    };

    const formatMetricLabel = field => {
        const labels = {
            winRate: "Win rate",
            averageR: "Average R",
            expectancy: "Expectancy",
        };

        return labels[field] || field || "Metric";
    };

    const addMetricChange = (label, change) => {
        const card = document.createElement("article");
        card.className = "compare-highlight-card";

        const heading = document.createElement("span");
        heading.className = "compare-highlight-label";
        heading.textContent = label;
        card.appendChild(heading);

        if (!change) {
            const empty = document.createElement("p");
            empty.className = "compare-highlight-empty";
            empty.textContent = "No comparable change.";
            card.appendChild(empty);
            grid.appendChild(card);
            return;
        }

        const name = document.createElement("strong");
        name.textContent = formatMetricLabel(change.field);
        card.appendChild(name);

        const delta = document.createElement("span");
        delta.className = "compare-highlight-delta";
        delta.textContent =
            `${change.change > 0 ? "+" : ""}${formatMetricValue(change.field, change.change)}`;
        card.appendChild(delta);

        const values = document.createElement("span");
        values.className = "compare-highlight-values";
        values.textContent =
            `Current ${formatMetricValue(change.field, change.current)} · ` +
            `Previous ${formatMetricValue(change.field, change.previous)}`;
        card.appendChild(values);

        grid.appendChild(card);
    };

    const addDistributionChange = (label, change) => {
        const card = document.createElement("article");
        card.className = "compare-highlight-card";

        const heading = document.createElement("span");
        heading.className = "compare-highlight-label";
        heading.textContent = label;
        card.appendChild(heading);

        if (!change) {
            const empty = document.createElement("p");
            empty.className = "compare-highlight-empty";
            empty.textContent = "No comparable change.";
            card.appendChild(empty);
            grid.appendChild(card);
            return;
        }

        const name = document.createElement("strong");
        name.textContent = `${change.field || "Composition"} · ${change.value || "—"}`;
        card.appendChild(name);

        const delta = document.createElement("span");
        delta.className = "compare-highlight-delta";
        delta.textContent =
            `${change.percentagePointChange > 0 ? "+" : ""}` +
            `${(Number(change.percentagePointChange) * 100).toFixed(1)}pp`;
        card.appendChild(delta);

        const values = document.createElement("span");
        values.className = "compare-highlight-values";
        values.textContent =
            `Current ${formatComparePercent(change.current?.percentage)} · ` +
            `Previous ${formatComparePercent(change.previous?.percentage)}`;
        card.appendChild(values);

        grid.appendChild(card);
    };

    addMetricChange(
        "Largest metric increase",
        changes.largestMetricIncrease,
    );

    addMetricChange(
        "Largest metric decrease",
        changes.largestMetricDecrease,
    );

    addDistributionChange(
        "Largest composition increase",
        changes.largestDistributionIncrease,
    );

    addDistributionChange(
        "Largest composition decrease",
        changes.largestDistributionDecrease,
    );

    section.appendChild(grid);
    container.appendChild(section);
}


function renderCompareDistribution(field, payload, container) {
    const section = document.createElement("section");
    section.className = "compare-distribution";

    const title = document.createElement("h3");
    title.textContent = field.charAt(0).toUpperCase() + field.slice(1);
    section.appendChild(title);

    const values = Array.isArray(payload?.values) ? payload.values : [];

    if (!values.length) {
        const empty = document.createElement("p");
        empty.className = "pattern-empty";
        empty.textContent = "No explicit observations available.";
        section.appendChild(empty);
        container.appendChild(section);
        return;
    }

    const table = document.createElement("table");
    table.className = "compare-table";

    const head = document.createElement("thead");
    const headRow = document.createElement("tr");

    ["Value", "Current", "Previous", "Change", "Supporting trades"].forEach(label => {
        const cell = document.createElement("th");
        cell.scope = "col";
        cell.textContent = label;
        headRow.appendChild(cell);
    });

    head.appendChild(headRow);
    table.appendChild(head);

    const body = document.createElement("tbody");

    values.forEach(item => {
        const row = document.createElement("tr");

        const valueCell = document.createElement("th");
        valueCell.scope = "row";
        valueCell.textContent = item.value;
        row.appendChild(valueCell);

        const currentCell = document.createElement("td");
        currentCell.textContent =
            `${item.current?.count || 0} · ${formatComparePercent(item.current?.percentage)}`;
        row.appendChild(currentCell);

        const previousCell = document.createElement("td");
        previousCell.textContent =
            `${item.previous?.count || 0} · ${formatComparePercent(item.previous?.percentage)}`;
        row.appendChild(previousCell);

        const changeCell = document.createElement("td");
        changeCell.textContent =
            item.percentagePointChange == null
                ? "—"
                : `${item.percentagePointChange > 0 ? "+" : ""}${(Number(item.percentagePointChange) * 100).toFixed(1)}pp`;
        row.appendChild(changeCell);

        const supportingIds = [
            ...(item.current?.tradeIds || []),
            ...(item.previous?.tradeIds || []),
        ];

        const uniqueIds = [...new Set(supportingIds)];

        if (uniqueIds.length) {
            const supportingCell = document.createElement("td");
            const supportingList = document.createElement("div");
            supportingList.className = "compare-inline-trade-list";

            uniqueIds.forEach(tradeId => {
                const trade = trades.find(candidate => candidate.id === tradeId);
                const button = document.createElement("button");
                button.type = "button";
                button.className = "compare-inline-trade";
                button.textContent = trade
                    ? `${trade.symbol || "Trade"} · ${trade.direction || "—"}`
                    : tradeId;
                button.title = tradeId;
                button.addEventListener("click", () => openTrade(tradeId));
                supportingList.appendChild(button);
            });

            supportingCell.appendChild(supportingList);
            row.appendChild(supportingCell);
        } else {
            const supportingCell = document.createElement("td");
            supportingCell.textContent = "—";
            row.appendChild(supportingCell);
        }

        body.appendChild(row);
    });

    table.appendChild(body);
    section.appendChild(table);
    container.appendChild(section);
}


function renderComparePatterns(payload, container) {
    const patterns = payload?.patterns || {};

    const section = document.createElement("section");
    section.className = "compare-patterns";

    const title = document.createElement("h3");
    title.textContent = "Pattern changes";
    section.appendChild(title);

    const groups = [
        ["New patterns", patterns.newPatterns],
        ["Disappearing patterns", patterns.disappearingPatterns],
    ];

    let rendered = false;

    groups.forEach(([label, items]) => {
        if (!Array.isArray(items) || !items.length) {
            return;
        }

        rendered = true;

        const group = document.createElement("div");
        group.className = "compare-pattern-group";

        const heading = document.createElement("h4");
        heading.textContent = label;
        group.appendChild(heading);

        items.forEach(pattern => {
            const card = document.createElement("article");
            card.className = "compare-pattern-card";

            const name = document.createElement("strong");
            name.textContent = `${pattern.dimension || "Pattern"} · ${pattern.value || "—"}`;

            const meta = document.createElement("span");
            meta.textContent =
                `${pattern.sampleSize || 0} trades · ` +
                `Win rate ${formatComparePercent(pattern.winRate)} · ` +
                `Expectancy ${formatCompareR(pattern.expectancy)}`;

            card.append(name, meta);

            const tradeIds = Array.isArray(pattern.sourceTradeIds)
                ? pattern.sourceTradeIds
                : [];

            if (tradeIds.length) {
                const links = document.createElement("div");
                renderCompareTradeLinks(links, tradeIds, "Supporting trades");
                card.appendChild(links);
            }

            group.appendChild(card);
        });

        section.appendChild(group);
    });

    if (!rendered) {
        const empty = document.createElement("p");
        empty.className = "pattern-empty";
        empty.textContent = "No new or disappearing patterns meet the minimum sample.";
        section.appendChild(empty);
    }

    container.appendChild(section);
}


function renderCompare(payload) {
    if (!compareContent || !compareStatus) {
        return;
    }

    compareContent.replaceChildren();

    const current = payload?.periods?.current;
    const previous = payload?.periods?.previous;
    const performance = payload?.performance;

    const currentCount = Number(current?.actualCount || 0);
    const previousCount = Number(previous?.actualCount || 0);

    compareStatus.textContent =
        `${currentCount} current · ${previousCount} previous trades`;

    const periodNote = document.createElement("p");
    periodNote.className = "compare-period-note";

    if (!previousCount) {
        periodNote.textContent =
            "Previous period has insufficient history. Changes requiring a previous period are shown as unknown.";
    } else {
        periodNote.textContent =
            `Current: last ${current?.requestedCount || 0} trades · ` +
            `Previous: preceding ${previous?.requestedCount || 0} trades.`;
    }

    compareContent.appendChild(periodNote);

    const performanceSection = document.createElement("section");
    performanceSection.className = "compare-performance";

    const performanceTitle = document.createElement("h3");
    performanceTitle.textContent = "Performance";
    performanceSection.appendChild(performanceTitle);

    const metrics = document.createElement("div");
    metrics.className = "compare-metrics";

    metrics.appendChild(
        renderCompareMetric(
            "Win rate",
            performance?.winRate?.current,
            performance?.winRate?.previous,
            performance?.winRate?.change,
            formatComparePercent,
        ),
    );

    metrics.appendChild(
        renderCompareMetric(
            "Average R",
            performance?.averageR?.current,
            performance?.averageR?.previous,
            performance?.averageR?.change,
            formatCompareR,
        ),
    );

    metrics.appendChild(
        renderCompareMetric(
            "Expectancy",
            performance?.expectancy?.current,
            performance?.expectancy?.previous,
            performance?.expectancy?.change,
            formatCompareR,
        ),
    );

    metrics.appendChild(
        renderCompareMetric(
            "Actual R coverage",
            performance?.actualR?.current?.coverage,
            performance?.actualR?.previous?.coverage,
            null,
            formatComparePercent,
        ),
    );

    metrics.appendChild(
        renderCompareMetric(
            "Sample size",
            performance?.sampleSize?.current,
            performance?.sampleSize?.previous,
            performance?.sampleSize?.change,
            value => value == null ? "—" : String(value),
        ),
    );

    performanceSection.appendChild(metrics);
    compareContent.appendChild(performanceSection);

    renderCompareChangeSummary(payload, compareContent);

    const distributionsSection = document.createElement("section");
    distributionsSection.className = "compare-distributions";

    const distributionsTitle = document.createElement("h3");
    distributionsTitle.textContent = "Trading composition";
    distributionsSection.appendChild(distributionsTitle);

    Object.entries(payload?.distributions || {}).forEach(([field, distribution]) => {
        renderCompareDistribution(
            field,
            distribution,
            distributionsSection,
        );
    });

    compareContent.appendChild(distributionsSection);

    renderComparePatterns(payload, compareContent);
}


function formatLeakTrend(value) {
    const labels = {
        TRENDING_UP: "TRENDING UP",
        TRENDING_DOWN: "TRENDING DOWN",
        STABLE: "STABLE",
        INSUFFICIENT_HISTORY: "INSUFFICIENT HISTORY",
    };

    return labels[value] || "UNKNOWN";
}

function formatLeakR(value) {
    return value == null ? "—" : `${Number(value).toFixed(2)}R`;
}

function openLeakDetails(leak) {
    if (!leakDetails || !leakDetailsContent) {
        return;
    }

    leakDetails.hidden = false;
    leakDetailsTitle.textContent = leak.label || leak.type;
    leakDetailsContent.replaceChildren();

    const summary = document.createElement("div");
    summary.className = "leak-details-summary";

    const addSummaryMetric = (label, value) => {
        const card = document.createElement("div");
        card.className = "leak-details-summary-card";

        const metricLabel = document.createElement("span");
        metricLabel.textContent = label;

        const metricValue = document.createElement("strong");
        metricValue.textContent = value;

        card.append(metricLabel, metricValue);
        summary.appendChild(card);
    };

    addSummaryMetric("Occurrences", String(leak.occurrenceCount || 0));
    addSummaryMetric("R impact", formatLeakR(leak.rImpact));
    addSummaryMetric(
        "Actual R coverage",
        `${(Number(leak.actualRCoverage || 0) * 100).toFixed(0)}%`
    );
    addSummaryMetric("Evidence", leak.evidenceStrength || "UNKNOWN");
    addSummaryMetric("Trend", formatLeakTrend(leak.trend));

    leakDetailsContent.appendChild(summary);

    const supporting = document.createElement("section");
    supporting.className = "leak-supporting-trades";

    const heading = document.createElement("div");
    heading.className = "leak-details-subheading";

    const title = document.createElement("h3");
    title.textContent = "Supporting trades";

    const count = document.createElement("span");
    const tradeIds = Array.isArray(leak.supportingTradeIds)
        ? leak.supportingTradeIds
        : [];
    count.textContent = `${tradeIds.length} trade${tradeIds.length === 1 ? "" : "s"}`;

    heading.append(title, count);
    supporting.appendChild(heading);

    if (!tradeIds.length) {
        const empty = document.createElement("p");
        empty.className = "pattern-empty";
        empty.textContent = "No supporting trades recorded for this leak.";
        supporting.appendChild(empty);
    } else {
        const list = document.createElement("div");
        list.className = "leak-trade-list";

        tradeIds.forEach(tradeId => {
            const trade = trades.find(item => item.id === tradeId);

            const row = document.createElement("button");
            row.type = "button";
            row.className = "leak-trade-row";

            const identity = document.createElement("span");
            identity.className = "leak-trade-identity";
            identity.textContent = trade
                ? `${trade.symbol || "Trade"} · ${trade.direction || "—"}`
                : tradeId;

            const meta = document.createElement("span");
            meta.className = "leak-trade-meta";
            meta.textContent = trade
                ? `${trade.result || "UNREVIEWED"} · ${formatDate(trade.timestamp)}`
                : tradeId;

            row.append(identity, meta);

            row.addEventListener("click", () => {
                edgeMapSelectedTradeIds = null;
                openTrade(tradeId);
            });

            list.appendChild(row);
        });

        supporting.appendChild(list);
    }

    leakDetailsContent.appendChild(supporting);
    leakDetails.scrollIntoView({ behavior: "smooth", block: "start" });
}


async function openMemoryDetails(finding) {
    if (!memoryDetails || !memoryDetailsContent || !memoryDetailsTitle) {
        return;
    }

    let detail = {
        finding,
        verificationHistory: [],
    };

    const currentFinding = finding;

    try {
        detail = await getLocalMemoryFinding(currentFinding.id);
    } catch (error) {
        // Fall back to the already-loaded finding if the detail request fails.
    }

    const resolvedFinding = detail?.finding || currentFinding;
    const verificationHistory = Array.isArray(detail?.verificationHistory)
        ? detail.verificationHistory
        : [];

    memoryDetails.hidden = false;
    memoryDetailsTitle.textContent =
        resolvedFinding.statement || "Selected finding";
    memoryDetailsContent.replaceChildren();

    const summary = document.createElement("div");
    summary.className = "memory-details-summary";

    [
        ["Type", resolvedFinding.type || "—"],
        ["Status", resolvedFinding.status || "—"],
        ["Sample size", resolvedFinding.sampleSize ?? "—"],
        ["Evidence strength", resolvedFinding.evidenceStrength || "—"],
        ["First observed", resolvedFinding.firstObserved ? formatDate(resolvedFinding.firstObserved) : "—"],
        ["Last verified", resolvedFinding.lastVerified ? formatDate(resolvedFinding.lastVerified) : "—"],
    ].forEach(([label, value]) => {
        const item = document.createElement("div");
        item.className = "memory-details-summary-item";

        const labelElement = document.createElement("span");
        labelElement.textContent = label;

        const valueElement = document.createElement("strong");
        valueElement.textContent = String(value);

        item.append(labelElement, valueElement);
        summary.appendChild(item);
    });

    memoryDetailsContent.appendChild(summary);

    const supporting = document.createElement("section");
    supporting.className = "memory-details-supporting";

    const heading = document.createElement("h3");
    const tradeIds = Array.isArray(resolvedFinding.supportingTradeIds)
        ? resolvedFinding.supportingTradeIds
        : [];
    heading.textContent =
        `Supporting trades · ${tradeIds.length}`;

    supporting.appendChild(heading);

    if (!tradeIds.length) {
        const empty = document.createElement("p");
        empty.className = "pattern-empty";
        empty.textContent = "No supporting trades are linked to this finding.";
        supporting.appendChild(empty);
    } else {
        const list = document.createElement("div");
        list.className = "memory-details-trade-list";

        tradeIds.forEach(tradeId => {
            const trade = trades.find(item => item.id === tradeId);
            const item = document.createElement("div");
            item.className = "memory-details-trade-row";

            const identity = document.createElement("strong");
            identity.textContent = trade
                ? `${trade.symbol || "Trade"} · ${trade.direction || "—"}`
                : tradeId;

            const meta = document.createElement("span");
            meta.textContent = trade
                ? `${trade.result || "UNREVIEWED"} · ${formatDate(trade.timestamp)}`
                : "Trade not currently loaded";

            item.append(identity, meta);
            list.appendChild(item);
        });

        supporting.appendChild(list);
    }

    memoryDetailsContent.appendChild(supporting);

    const actions = document.createElement("div");
    actions.className = "memory-details-actions";

    const actionStatus = document.createElement("p");
    actionStatus.className = "memory-details-action-status";
    actionStatus.setAttribute("aria-live", "polite");

    const refreshMemoryView = async () => {
        await loadMemory();
        const refreshed = memoryPayload?.findings?.find(item => item.id === resolvedFinding.id);
        if (refreshed) {
            openMemoryDetails(refreshed);
        } else {
            memoryDetails.hidden = true;
        }
    };

    const runAction = async (action, successMessage) => {
        actionStatus.textContent = "Updating memory…";
        actions.querySelectorAll("button").forEach(button => {
            button.disabled = true;
        });

        try {
            await action();
            actionStatus.textContent = successMessage;
            await refreshMemoryView();
        } catch (error) {
            actionStatus.textContent =
                error?.message || "Memory update failed.";
            actions.querySelectorAll("button").forEach(button => {
                button.disabled = false;
            });
        }
    };

    const addActionButton = (label, handler) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "clear-filters";
        button.textContent = label;
        button.addEventListener("click", handler);
        actions.appendChild(button);
    };

    const status = String(resolvedFinding.status || "OBSERVED");

    if (status === "OBSERVED" || status === "ACTIVE") {
        addActionButton("Challenge", () => runAction(
            () => challengeLocalMemory(resolvedFinding.id),
            "Finding challenged."
        ));
    }

    if (status !== "RETIRED") {
        addActionButton("Update", () => {
            const statement = window.prompt(
                "Update this finding statement:",
                resolvedFinding.statement || ""
            );

            if (statement === null) {
                return;
            }

            const trimmed = statement.trim();
            if (!trimmed) {
                actionStatus.textContent = "Finding statement cannot be empty.";
                return;
            }

            return runAction(
                () => updateLocalMemory(resolvedFinding.id, trimmed),
                "Finding updated."
            );
        });

        addActionButton("Retire", () => runAction(
            () => retireLocalMemory(resolvedFinding.id),
            "Finding retired."
        ));
    }

    addActionButton("Recheck", () => {
        const sampleSize = Number(window.prompt(
            "Recheck sample size:",
            String(resolvedFinding.sampleSize ?? 0)
        ));

        if (!Number.isInteger(sampleSize) || sampleSize < 0) {
            actionStatus.textContent =
                "Sample size must be a non-negative integer.";
            return;
        }

        return runAction(
            () => recheckLocalMemory(resolvedFinding.id, {
                status: resolvedFinding.status || "OBSERVED",
                sampleSize,
                evidenceStrength: resolvedFinding.evidenceStrength || "INSUFFICIENT",
                supportingTradeIds: Array.isArray(resolvedFinding.supportingTradeIds)
                    ? resolvedFinding.supportingTradeIds
                    : [],
            }),
            "Finding rechecked."
        );
    });

    actions.appendChild(actionStatus);
    memoryDetailsContent.appendChild(actions);
    memoryDetails.scrollIntoView({ behavior: "smooth", block: "start" });
}


function renderMemory(payload) {
    if (!memoryContent || !memoryStatus) {
        return;
    }

    memoryContent.replaceChildren();

    const findings = Array.isArray(payload?.findings) ? payload.findings : [];

    memoryStatus.textContent =
        `${findings.length} finding${findings.length === 1 ? "" : "s"}`;

    if (!findings.length) {
        const empty = document.createElement("p");
        empty.className = "pattern-empty";
        empty.textContent = "No trading memory has been recorded yet.";
        memoryContent.appendChild(empty);
        return;
    }

    const grid = document.createElement("div");
    grid.className = "memory-grid";

    const formatDateValue = value => value ? formatDate(value) : "—";

    findings.forEach(finding => {
        const card = document.createElement("article");
        card.className = `memory-card ${String(finding.status || "OBSERVED").toLowerCase()}`;

        const heading = document.createElement("div");
        heading.className = "memory-card-heading";

        const type = document.createElement("span");
        type.className = "memory-card-type";
        type.textContent = String(finding.type || "FINDING");

        const status = document.createElement("span");
        status.className = "memory-card-status";
        status.textContent = String(finding.status || "OBSERVED");

        heading.append(type, status);

        const statement = document.createElement("h3");
        statement.className = "memory-card-statement";
        statement.textContent = finding.statement || "Untitled finding";

        const metrics = document.createElement("div");
        metrics.className = "memory-card-metrics";

        [
            ["Sample", finding.sampleSize ?? "—"],
            ["Evidence", finding.evidenceStrength || "—"],
            ["First observed", formatDateValue(finding.firstObserved)],
            ["Last verified", formatDateValue(finding.lastVerified)],
        ].forEach(([label, value]) => {
            const metric = document.createElement("div");
            metric.className = "memory-card-metric";

            const labelElement = document.createElement("span");
            labelElement.textContent = label;

            const valueElement = document.createElement("strong");
            valueElement.textContent = String(value);

            metric.append(labelElement, valueElement);
            metrics.appendChild(metric);
        });

        const supporting = document.createElement("p");
        supporting.className = "memory-card-supporting";
        const tradeCount = Array.isArray(finding.supportingTradeIds)
            ? finding.supportingTradeIds.length
            : 0;
        supporting.textContent =
            `${tradeCount} supporting trade${tradeCount === 1 ? "" : "s"}`;

        card.append(heading, statement, metrics, supporting);
        card.tabIndex = 0;
        card.setAttribute("role", "button");

        const openDetails = () => openMemoryDetails(finding);
        card.addEventListener("click", openDetails);
        card.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openDetails();
            }
        });

        grid.appendChild(card);
    });

    memoryContent.appendChild(grid);
}


async function loadMemory() {
    if (!memoryContent || !memoryStatus) {
        return;
    }

    memoryStatus.textContent = "Loading trading memory…";
    memoryContent.replaceChildren();

    const loading = document.createElement("p");
    loading.className = "pattern-empty";
    loading.textContent = "Loading deterministic trading memory…";
    memoryContent.appendChild(loading);

    try {
        const payload = await getLocalMemory();
        memoryPayload = payload;
        renderMemory(payload);
    } catch (error) {
        memoryPayload = null;
        memoryStatus.textContent = "Local service unavailable";
        memoryContent.replaceChildren();

        const empty = document.createElement("p");
        empty.className = "pattern-empty";
        empty.textContent = "Start the local service to load Trading Memory.";
        memoryContent.appendChild(empty);
    }
}


async function loadLeakMap() {
    if (!leakMapContent || !leakMapStatus) {
        return;
    }

    leakMapStatus.textContent = "Loading historical leaks…";
    leakMapContent.replaceChildren();

    const loading = document.createElement("p");
    loading.className = "pattern-empty";
    loading.textContent = "Loading deterministic Leak Map…";
    leakMapContent.appendChild(loading);

    try {
        const payload = await getLocalLeakMap();
        leakMapPayload = payload;
        renderLeakMap(payload);
    } catch (error) {
        leakMapPayload = null;
        leakMapStatus.textContent = "Local service unavailable";
        leakMapContent.replaceChildren();

        const empty = document.createElement("p");
        empty.className = "pattern-empty";
        empty.textContent = "Start the local service to load the Leak Map.";
        leakMapContent.appendChild(empty);
    }
}


function renderStorageStatus(status) {
    const label = document.getElementById("storageProviderStatus");
    const notionSetup = document.getElementById("notionSetup");
    const active = status?.provider || "local";
    label.textContent = `${active === "notion" ? "Notion" : "You Can't Trade Local"} · ${status?.state || "OFFLINE"}`;
    document.querySelectorAll("[data-provider-card]").forEach(card => card.classList.toggle("active", card.dataset.providerCard === active));
    notionSetup.hidden = active !== "notion" && !status?.notionConnected && status?.state !== "NOT_CONNECTED";
    document.getElementById("disconnectNotionButton").hidden = !status?.tokenStored;
    const recovery = document.getElementById("storageRecovery");
    const isNotion = active === "notion";
    recovery.hidden = !isNotion;
    if (isNotion) {
        const freshness = document.getElementById("storageFreshness");
        const cacheSummary = document.getElementById("storageCacheSummary");
        freshness.textContent = status?.lastSyncedAt
            ? `Last synced ${formatDate(status.lastSyncedAt)}`
            : "Notion has not synced yet";
        const cache = status?.cache || {};
        const outbox = status?.outbox || {};
        cacheSummary.textContent = `Cache: ${cache.records || 0} records · ${formatBytes(cache.bytes || 0)}${outbox.pending ? ` · ${outbox.pending} pending save${outbox.pending === 1 ? "" : "s"}` : ""}`;
        document.getElementById("retryStorageButton").hidden = !outbox.pending;
    }
}

function formatBytes(bytes) {
    const value = Number(bytes) || 0;
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

async function loadStorageSettings() {
    try {
        const status = await getStorageStatus();
        renderStorageStatus(status);
        if (status.provider === "notion" && status.state === "CONNECTED" && status.outbox?.pending && !outboxRetryInFlight) {
            outboxRetryInFlight = true;
            retryStorageOutbox().catch(() => {}).finally(async () => {
                outboxRetryInFlight = false;
                try { renderStorageStatus(await getStorageStatus()); } catch (_) { /* status already rendered */ }
            });
        }
        if (status.notionConnected && status.provider === "local") {
            try { await populateNotionDatabases(); document.getElementById("notionSetupStatus").textContent = "Notion is connected. Choose your trading database."; }
            catch (error) { document.getElementById("notionSetupStatus").textContent = error.message || "Could not load Notion databases."; }
        }
    } catch (error) {
        document.getElementById("storageProviderStatus").textContent = "Service unavailable";
    }
}

async function populateNotionDatabases() {
    const select = document.getElementById("notionDatabaseSelect");
    select.replaceChildren(new Option("Select a database", ""));
    const databases = await getNotionDatabases();
    databases.forEach(database => select.appendChild(new Option(database.title?.[0]?.plain_text || "Untitled database", database.id)));
    document.getElementById("notionDatabaseStep").hidden = false;
}

async function connectNotionFromSettings() {
    const status = document.getElementById("notionSetupStatus");
    const tokenInput = document.getElementById("notionToken");
    if (!tokenInput.value.trim()) {
        status.textContent = "Using the securely stored connection…";
        try { await populateNotionDatabases(); status.textContent = "Connected. Choose the database shared with You Can't Trade."; }
        catch (error) { status.textContent = error.message || "Connect Notion first."; }
        return;
    }
    status.textContent = "Validating connection…";
    try {
        await connectNotion(tokenInput.value.trim());
        tokenInput.value = "";
        await populateNotionDatabases();
        status.textContent = "Connected. Choose the database shared with You Can't Trade.";
        document.getElementById("notionSetup").hidden = false;
    } catch (error) { tokenInput.value = ""; status.textContent = error.message || "Notion connection failed."; }
}

async function configureNotionFromSettings() {
    const status = document.getElementById("notionSetupStatus");
    const database = document.getElementById("notionDatabaseSelect");
    const source = document.getElementById("notionDataSourceSelect");
    if (!database.value || !source.value) { status.textContent = "Choose a database and data source."; return; }
    status.textContent = "Checking schema…";
    try {
        const result = await configureNotion({ databaseId: database.value, dataSourceId: source.value, databaseName: database.selectedOptions[0].textContent, dataSourceName: source.selectedOptions[0].textContent });
        status.textContent = Object.keys(result.schema || {}).some(name => name.toLowerCase() === "vf trade id") ? "Schema ready. Notion storage is ready to enable." : "Create the You Can't Trade fields, then enable Notion storage.";
        if (Object.keys(result.schema || {}).some(name => name.toLowerCase() === "vf trade id")) await selectStorageProvider("notion");
        await loadStorageSettings();
    } catch (error) { status.textContent = error.message || "Could not configure Notion."; }
}

const filterControls = {
    symbol: document.getElementById("filterSymbol"),
    timeframe: document.getElementById("filterTimeframe"),
    result: document.getElementById("filterResult"),
    setup: document.getElementById("filterSetup"),
    session: document.getElementById("filterSession"),
    dateRange: document.getElementById("filterDateRange")
};

const customDateRange = document.getElementById("customDateRange");
const dateRangeMonthSelect = document.getElementById("dateRangeMonthSelect");
const dateRangeYearSelect = document.getElementById("dateRangeYearSelect");
const dateRangePreviousMonth = document.getElementById("dateRangePreviousMonth");
const dateRangeNextMonth = document.getElementById("dateRangeNextMonth");
const dateRangeCalendar = document.getElementById("dateRangeCalendar");
const dateRangeStartLabel = document.getElementById("dateRangeStartLabel");
const dateRangeEndLabel = document.getElementById("dateRangeEndLabel");
const applyCustomDateRange = document.getElementById("applyCustomDateRange");

let customRangeStart = null;
let customRangeEnd = null;
let appliedCustomRangeStart = null;
let appliedCustomRangeEnd = null;
let customRangeMonth = new Date(
    new Date().getFullYear(),
    new Date().getMonth(),
    1
);



function calculatePlannedR(trade) {

    if (
        trade.entry == null ||
        trade.stopLoss == null ||
        trade.takeProfit == null
    ) {
        return null;
    }

    const risk = Math.abs(trade.entry - trade.stopLoss);

    if (risk === 0) {
        return null;
    }

    return Math.abs(trade.takeProfit - trade.entry) / risk;
}


function calculateActualR(trade) {

    if (
        trade.entry == null ||
        trade.stopLoss == null ||
        trade.exitPrice == null ||
        !trade.direction
    ) {
        return null;
    }

    const risk = Math.abs(trade.entry - trade.stopLoss);

    if (risk === 0) {
        return null;
    }

    const profit = trade.direction === "LONG"
        ? trade.exitPrice - trade.entry
        : trade.entry - trade.exitPrice;

    return profit / risk;
}


function formatNumber(value) {

    return value == null
        ? "—"
        : Number(value).toLocaleString(undefined, {
            maximumFractionDigits: 6
        });
}


function formatR(value) {

    return value == null
        ? "—"
        : `${value.toFixed(2)}R`;
}


function formatDate(value) {

    if (!value) {
        return "Unknown date";
    }

    const date = new Date(value);

    return Number.isNaN(date.getTime())
        ? "Unknown date"
        : date.toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
            year: "numeric"
        });
}


function formatDateTime(value) {

    if (value == null) {
        return "Unavailable";
    }

    const date = new Date(value);

    return Number.isNaN(date.getTime())
        ? "Unavailable"
        : date.toLocaleString(undefined, {
            month: "short",
            day: "numeric",
            year: "numeric",
            hour: "numeric",
            minute: "2-digit"
        });
}


function formatMegabytes(bytes) {

    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}


function resetAIInsight() {

    document.getElementById("aiInsightStatus").textContent =
        "Uses Ollama on this computer.";
    document.getElementById("aiInsightContent").hidden = true;
    document.getElementById("aiInsightSummary").textContent = "";
    document.getElementById("aiInsightAction").textContent = "";
    document.getElementById("aiInsightMeta").textContent = "";
}


function renderAIInsight(insight) {

    const content = document.getElementById("aiInsightContent");
    const status = document.getElementById("aiInsightStatus");

    if (!insight) {
        content.hidden = true;
        status.textContent = "No local reflection yet. Analyze after saving your review.";
        return;
    }

    document.getElementById("aiInsightSummary").textContent = insight.summary;
    document.getElementById("aiInsightAction").textContent = insight.action
        ? `Next journaling experiment: ${insight.action}`
        : "No additional journaling experiment was suggested.";
    document.getElementById("aiInsightMeta").textContent =
        `Generated locally with ${insight.model} · ${insight.promptVersion}`;
    status.textContent = "Local reflection grounded in this trade's saved fields.";
    content.hidden = false;
}


async function loadAIInsight(tradeId) {

    resetAIInsight();

    try {
        renderAIInsight(await getLocalInsight(tradeId));
    } catch (error) {
        if (error instanceof LocalApiUnavailableError) {
            document.getElementById("aiInsightStatus").textContent =
                "Start the local service and Ollama to enable private reflection.";
            return;
        }

        document.getElementById("aiInsightStatus").textContent =
            "The local reflection could not be loaded.";
    }
}


async function analyzeSelectedTrade() {

    if (!selectedTradeId) {
        return;
    }

    const button = document.getElementById("analyzeTradeButton");
    const status = document.getElementById("aiInsightStatus");
    button.disabled = true;
    status.textContent = "Reflecting locally…";

    try {
        renderAIInsight(await analyzeLocalTrade(selectedTradeId));
    } catch (error) {
        status.textContent = error instanceof LocalApiUnavailableError
            ? "Start the local service and Ollama, then try again."
            : error?.message || "Local reflection failed. Try again.";
    } finally {
        button.disabled = false;
    }
}


function getResultLabel(result) {

    if (result === "WIN") {
        return "Win";
    }

    if (result === "LOSS") {
        return "Loss";
    }

    if (result === "BE") {
        return "Break even";
    }

    return "Captured";
}


function getResultClass(result) {

    if (result === "WIN") {
        return "badge badge-win";
    }

    if (result === "LOSS") {
        return "badge badge-loss";
    }

    if (result === "BE") {
        return "badge badge-be";
    }

    return "badge badge-captured";
}


function getWeekTrades() {

    const cutoff = Date.now() - (7 * 24 * 60 * 60 * 1000);

    return trades.filter(trade => {
        const timestamp = new Date(trade.timestamp).getTime();

        return Number.isFinite(timestamp) && timestamp >= cutoff;
    });
}


function createReviewBlock(className, label, text) {

    const block = document.createElement("article");
    block.className = className;

    const heading = document.createElement("span");
    heading.className = "review-label";
    heading.textContent = label;

    const content = document.createElement("p");
    content.textContent = text;

    block.append(heading, content);

    return block;
}


function renderWeeklyReview() {

    const weekTrades = getWeekTrades();
    const reviewedTrades = weekTrades.filter(
        trade => trade.result !== null
    );

    weeklyReviewContent.replaceChildren();

    if (weekTrades.length < 3) {
        weeklyReviewContent.append(
            createReviewBlock(
                "review-insight",
                "Evidence status",
                `You captured ${weekTrades.length} trade${weekTrades.length === 1 ? "" : "s"} in the last 7 days. Capture and review at least 3 trades before looking for a pattern.`
            ),
            createReviewBlock(
                "review-focus",
                "This week’s focus",
                "Capture the finished chart and add one short review while the reason for the trade is still fresh."
            )
        );

        return;
    }

    const deviations = reviewedTrades.filter(
        trade =>
            trade.planAdherence === "DEVIATED" ||
            (
                trade.executionTag &&
                trade.executionTag !== "FOLLOWED_PLAN"
            )
    );

    if (deviations.length >= 2) {
        weeklyReviewContent.append(
            createReviewBlock(
                "review-insight",
                "Observed pattern",
                `${deviations.length} of ${reviewedTrades.length} reviewed trades this week were marked as a plan deviation or execution issue. This is based on your own review tags, not inferred from P&L.`
            ),
            createReviewBlock(
                "review-focus",
                "This week’s focus",
                "Before your next trade, name the setup and decide whether you followed the plan when reviewing it. Aim to reduce untagged deviations."
            )
        );

        return;
    }

    const setupCounts = new Map();

    reviewedTrades.forEach(trade => {
        if (!trade.setup) {
            return;
        }

        setupCounts.set(
            trade.setup,
            (setupCounts.get(trade.setup) || 0) + 1
        );
    });

    const mostReviewedSetup = [...setupCounts.entries()]
        .sort(([, firstCount], [, secondCount]) => secondCount - firstCount)[0];

    if (mostReviewedSetup && mostReviewedSetup[1] >= 2) {
        weeklyReviewContent.append(
            createReviewBlock(
                "review-insight",
                "Most reviewed setup",
                `“${mostReviewedSetup[0]}” appears in ${mostReviewedSetup[1]} of ${reviewedTrades.length} reviewed trades this week. That is a sample to study—not proof that the setup is profitable.`
            ),
            createReviewBlock(
                "review-focus",
                "This week’s focus",
                "Keep naming this setup consistently and record whether you followed the plan. Consistent labels create evidence for a useful review."
            )
        );

        return;
    }

    weeklyReviewContent.append(
        createReviewBlock(
            "review-insight",
            "Review consistency",
            `${reviewedTrades.length} of ${weekTrades.length} captured trades have a recorded outcome this week. More structured tags are needed before You Can't Trade can identify a reliable behaviour pattern.`
        ),
        createReviewBlock(
            "review-focus",
            "This week’s focus",
            "For each completed trade, add an outcome plus one setup or execution tag. Keep the reflection short and consistent."
        )
    );
}


function patternMetric(label, value) {
    const item = document.createElement("div");
    item.className = "pattern-metric";
    const name = document.createElement("span");
    name.textContent = label;
    const number = document.createElement("strong");
    number.textContent = value;
    item.append(name, number);
    return item;
}


function renderPatternReview(analytics) {
    patternReviewContent.replaceChildren();
    if (!analytics) {
        patternReviewContent.innerHTML = '<p class="pattern-empty">Start the local service to load your verified pattern summary.</p>';
        return;
    }

    const outcomes = analytics.outcomes || {};
    const actualR = analytics.actualR || {};
    const metrics = document.createElement("div");
    metrics.className = "pattern-metrics";
    metrics.append(
        patternMetric("Reviewed", String(analytics.reviewedTrades || 0)),
        patternMetric("Wins", String(outcomes.wins || 0)),
        patternMetric("Losses", String(outcomes.losses || 0)),
        patternMetric("Total R", actualR.total == null ? "—" : `${Number(actualR.total).toFixed(2)}R`)
    );
    patternReviewContent.appendChild(metrics);

    const details = document.createElement("p");
    details.className = "pattern-details";
    const emotions = (analytics.topEmotions || []).map(item => `${item.value} (${item.count})`).join(", ");
    details.textContent = emotions ? `Recorded emotions: ${emotions}` : "No repeated setup, emotion, or execution tags recorded yet.";
    patternReviewContent.appendChild(details);

    if (analytics.sampleWarning) {
        const warning = document.createElement("p");
        warning.className = "pattern-warning";
        warning.textContent = analytics.sampleWarning;
        patternReviewContent.appendChild(warning);
    }
    patternReviewStatus.textContent = `${analytics.totalTrades || 0} captured · ${analytics.reviewedTrades || 0} reviewed`;
}


function renderPatternDiscovery(payload) {
    const container = document.getElementById("patternDiscoveryContent");
    const status = document.getElementById("patternDiscoveryStatus");
    const sortSelect = document.getElementById("patternSortSelect");
    const dimensionFilter = document.getElementById("patternDimensionFilter");

    if (!container || !status) {
        return;
    }

    container.replaceChildren();

    const allFindings = Array.isArray(payload?.patterns) ? [...payload.patterns] : [];
    const selectedDimension = dimensionFilter?.value || "";
    const findings = allFindings.filter(finding => {
        if (!selectedDimension) {
            return true;
        }

        if (selectedDimension === "combined") {
            return [
                "setup_session",
                "setup_direction",
                "setup_regime",
                "setup_session_regime",
                "structure_session",
                "direction_session",
            ].includes(finding.dimension);
        }

        return finding.dimension === selectedDimension;
    });

    const sortBy = sortSelect?.value || "sampleSize";

    findings.sort((left, right) => {
        if (sortBy === "winRate") {
            return (right.winRate ?? -Infinity) - (left.winRate ?? -Infinity);
        }

        if (sortBy === "averageR") {
            return (
                (right.actualR?.average ?? -Infinity) -
                (left.actualR?.average ?? -Infinity)
            );
        }

        if (sortBy === "recency") {
            return (
                new Date(right.recency?.lastObserved || 0).getTime() -
                new Date(left.recency?.lastObserved || 0).getTime()
            );
        }

        if (sortBy === "dimension") {
            return `${left.dimension}:${left.value}`.localeCompare(
                `${right.dimension}:${right.value}`
            );
        }

        return (right.sampleSize || 0) - (left.sampleSize || 0);
    });

    const filterLabel = selectedDimension
        ? ` · ${selectedDimension === "combined" ? "combined" : selectedDimension}`
        : "";

    status.textContent = `${findings.length} finding${findings.length === 1 ? "" : "s"}${filterLabel} · minimum sample ${payload?.minimumSample || 3}`;

    if (!findings.length) {
        const empty = document.createElement("p");
        empty.className = "pattern-empty";
        empty.textContent = "No recurring patterns meet the minimum sample yet.";
        container.appendChild(empty);
        return;
    }

    findings.forEach(finding => {
        const card = document.createElement("article");
        card.className = "pattern-finding";

        const heading = document.createElement("div");
        heading.className = "pattern-finding-heading";

        const title = document.createElement("h4");
        title.className = "pattern-finding-title";
        title.textContent = `${finding.dimension}: ${finding.value}`;

        const evidence = document.createElement("span");
        evidence.className = "review-period";
        evidence.textContent = finding.evidenceStrength?.level || "UNKNOWN";

        heading.append(title, evidence);
        card.appendChild(heading);

        const meta = document.createElement("p");
        meta.className = "pattern-finding-meta";
        meta.textContent = `${finding.sampleSize} supporting trades`;
        card.appendChild(meta);

        const metrics = document.createElement("div");
        metrics.className = "pattern-finding-metrics";

        const addMetric = (label, value) => {
            const metric = document.createElement("div");
            metric.className = "pattern-finding-metric";

            const metricLabel = document.createElement("span");
            metricLabel.textContent = label;

            const metricValue = document.createElement("strong");
            metricValue.textContent = value;

            metric.append(metricLabel, metricValue);
            metrics.appendChild(metric);
        };

        addMetric(
            "Win rate",
            finding.winRate == null ? "—" : `${(Number(finding.winRate) * 100).toFixed(1)}%`
        );

        addMetric(
            "Average R",
            finding.actualR?.average == null ? "—" : `${Number(finding.actualR.average).toFixed(2)}R`
        );

        addMetric(
            "Actual R coverage",
            finding.evidenceStrength?.actualRCoverage == null
                ? "—"
                : `${(Number(finding.evidenceStrength.actualRCoverage) * 100).toFixed(0)}%`
        );

        metrics.appendChild(document.createElement("div"));
        card.appendChild(metrics);

        const evidenceText = document.createElement("p");
        evidenceText.className = "pattern-evidence";
        evidenceText.textContent = `${finding.observation || "Observation unavailable"} ${finding.conclusion || ""}`;
        card.appendChild(evidenceText);

        const supportingTrades = document.createElement("button");
        supportingTrades.type = "button";
        supportingTrades.className = "pattern-supporting-trades";
        supportingTrades.textContent = `Open supporting trades (${finding.sourceTradeIds?.length || 0})`;
        supportingTrades.disabled = !finding.sourceTradeIds?.length;
        supportingTrades.addEventListener("click", () => {
            const tradeId = finding.sourceTradeIds?.[0];
            if (tradeId) {
                openTrade(tradeId);
            }
        });
        card.appendChild(supportingTrades);

        const evidenceDetails = document.createElement("div");
        evidenceDetails.className = "pattern-evidence-details";

        const evidenceItems = [
            [
                "Sample size",
                finding.evidenceStrength?.sampleSize == null
                    ? "—"
                    : String(finding.evidenceStrength.sampleSize),
            ],
            [
                "Actual R coverage",
                finding.evidenceStrength?.actualRCoverage == null
                    ? "—"
                    : `${(Number(finding.evidenceStrength.actualRCoverage) * 100).toFixed(0)}%`,
            ],
            [
                "Observed periods",
                finding.stability?.observedPeriods == null
                    ? "—"
                    : String(finding.stability.observedPeriods),
            ],
            [
                "Periods with Actual R",
                finding.stability?.periodsWithActualR == null
                    ? "—"
                    : String(finding.stability.periodsWithActualR),
            ],
            [
                "Recent",
                finding.evidenceStrength?.recent == null
                    ? "—"
                    : finding.evidenceStrength.recent ? "Yes" : "No",
            ],
            [
                "Reliability",
                finding.reliability?.level || "—",
            ],
        ];

        evidenceItems.forEach(([label, value]) => {
            const item = document.createElement("div");
            item.className = "pattern-evidence-item";

            const itemLabel = document.createElement("span");
            itemLabel.textContent = label;

            const itemValue = document.createElement("strong");
            itemValue.textContent = value;

            item.append(itemLabel, itemValue);
            evidenceDetails.appendChild(item);
        });

        card.appendChild(evidenceDetails);

        container.appendChild(card);
    });
}


function bindPatternDiscoverySorting() {
    const sortSelect = document.getElementById("patternSortSelect");
    const dimensionFilter = document.getElementById("patternDimensionFilter");

    if (sortSelect && sortSelect.dataset.bound !== "true") {
        sortSelect.dataset.bound = "true";
        sortSelect.addEventListener("change", () => {
            loadPatternReview();
        });
    }

    if (dimensionFilter && dimensionFilter.dataset.bound !== "true") {
        dimensionFilter.dataset.bound = "true";
        dimensionFilter.addEventListener("change", () => {
            loadPatternReview();
        });
    }
}


async function analyzePatterns() {
    const button = document.getElementById("analyzePatternsButton");
    let output = document.getElementById("patternAIInsight");
    if (!output) {
        output = document.createElement("p");
        output.id = "patternAIInsight";
        output.className = "pattern-ai-insight";
        document.querySelector(".pattern-review")?.appendChild(output);
    }
    if (!button) {
        return;
    }
    button.disabled = true;
    button.textContent = "Reflecting…";
    output.textContent = "Connecting to your private local AI…";
    output.hidden = false;
    try {
        const result = await analyzeLocalPatterns();
        output.textContent = result.insight.action
            ? `${result.insight.summary} Next experiment: ${result.insight.action}`
            : result.insight.summary;
        output.hidden = false;
    } catch (error) {
        output.textContent = "Start the local service and Ollama, then try again.";
        output.hidden = false;
    } finally {
        button.disabled = false;
        button.textContent = "Coach me locally";
    }
}


function bindEdgeMapControls() {
    if (!edgeMapDimensionSelect) {
        return;
    }

    edgeMapDimensionSelect.addEventListener("change", () => {
        loadEdgeMap();
    });
}


async function loadPatternReview() {
    bindPatternDiscoverySorting();

    try {
        const [analytics, patterns] = await Promise.all([
            getLocalAnalytics(),
            getLocalPatterns(),
        ]);

        renderPatternReview(analytics);
        renderPatternDiscovery(patterns);
    } catch (error) {
        patternReviewStatus.textContent = "Local service unavailable";
        renderPatternReview(null);

        const discoveryStatus = document.getElementById("patternDiscoveryStatus");
        const discoveryContent = document.getElementById("patternDiscoveryContent");

        if (discoveryStatus) {
            discoveryStatus.textContent = "Local service unavailable";
        }

        if (discoveryContent) {
            discoveryContent.replaceChildren();

            const empty = document.createElement("p");
            empty.className = "pattern-empty";
            empty.textContent = "Start the local service to load deterministic pattern findings.";
            discoveryContent.appendChild(empty);
        }
    }
}


function renderExperiments(items) {
    const container = document.getElementById("experimentsContent");
    container.replaceChildren();
    const active = items.filter(item => item.status === "ACTIVE");
    if (!items.length) {
        const empty = document.createElement("p");
        empty.className = "pattern-empty";
        empty.textContent = "No active experiment yet. Choose one behaviour to test.";
        container.appendChild(empty);
        return;
    }
    items.slice(0, 6).forEach(item => {
        const card = document.createElement("article");
        card.className = `experiment-card ${item.status.toLowerCase()}`;
        const heading = document.createElement("div");
        heading.className = "experiment-card-heading";
        const title = document.createElement("h3");
        title.textContent = item.title;
        const status = document.createElement("span");
        status.className = "experiment-status";
        status.textContent = item.status;
        heading.append(title, status);
        const hypothesis = document.createElement("p");
        hypothesis.textContent = item.hypothesis || `Test: ${item.behavior}`;
        const progress = document.createElement("div");
        progress.className = "experiment-progress";
        const bar = document.createElement("span");
        bar.style.width = `${Math.min(100, (item.progress / item.sample_target) * 100)}%`;
        progress.appendChild(bar);
        const meta = document.createElement("div");
        meta.className = "experiment-meta";
        meta.textContent = `${item.progress} / ${item.sample_target} reviewed trades · observation, not proof`;
        card.append(heading, hypothesis, progress, meta);
        if (item.status === "ACTIVE") {
            const pause = document.createElement("button");
            pause.className = "clear-filters experiment-pause";
            pause.type = "button";
            pause.textContent = "Pause";
            pause.addEventListener("click", async () => {
                await updateLocalExperimentStatus(item.id, "PAUSED");
                await loadExperiments();
            });
            card.appendChild(pause);
        }
        container.appendChild(card);
    });
}


async function loadExperiments() {
    try {
        renderExperiments(await getLocalExperiments());
    } catch (error) {
        const container = document.getElementById("experimentsContent");
        container.textContent = "Start the local service to load your experiments.";
    }
}


function renderStats() {

    const wins = trades.filter(trade => trade.result === "WIN").length;
    const losses = trades.filter(trade => trade.result === "LOSS").length;
    const reviewed = trades.filter(trade => trade.result !== null).length;
    const decidedTrades = wins + losses;
    const plannedTrades = trades.filter(
        trade => calculatePlannedR(trade) !== null
    );
    const totalPlannedR = plannedTrades.reduce(
        (sum, trade) => sum + calculatePlannedR(trade),
        0
    );
    const avgPlannedR = plannedTrades.length > 0
        ? totalPlannedR / plannedTrades.length
        : 0;

    document.getElementById("totalTrades").textContent = trades.length;
    document.getElementById("winRate").textContent = decidedTrades > 0
        ? `${((wins / decidedTrades) * 100).toFixed(1)}%`
        : "0.0%";
    document.getElementById("avgPlannedR").textContent =
        `${avgPlannedR.toFixed(2)}R`;
    document.getElementById("reviewedTrades").textContent = reviewed;
}


function renderStorageUsage(usage) {

    document.getElementById("storageUsage").textContent =
        Number.isFinite(usage.limitBytes)
            ? `${formatMegabytes(usage.bytes)} of ${formatMegabytes(usage.limitBytes)} stored locally`
            : `${formatMegabytes(usage.bytes)} stored in local database`;
}


function setFilterOptions(select, values, fallbackLabel) {

    const currentValue = select.value;

    while (select.options.length > 1) {
        select.remove(1);
    }

    [...values]
        .sort((first, second) => first.localeCompare(second))
        .forEach(value => {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = value || fallbackLabel;
            select.appendChild(option);
        });

    select.value = currentValue;
}


function populateFilters() {

    setFilterOptions(
        filterControls.symbol,
        new Set(trades.map(trade => trade.symbol).filter(Boolean)),
        "Untitled"
    );
    setFilterOptions(
        filterControls.timeframe,
        new Set(trades.map(trade => trade.timeframe).filter(Boolean)),
        "No timeframe"
    );
    setFilterOptions(
        filterControls.setup,
        new Set(trades.map(trade => trade.setup).filter(Boolean)),
        "Not tagged"
    );
}


function formatCalendarDate(date) {
    return date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric"
    });
}


function toDateKey(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}


function initializeDateRangeSelectors() {
    const months = Array.from({ length: 12 }, (_, index) =>
        new Date(2000, index, 1).toLocaleDateString(undefined, { month: "long" })
    );

    dateRangeMonthSelect.replaceChildren();

    months.forEach((monthName, index) => {
        const option = document.createElement("option");
        option.value = String(index);
        option.textContent = monthName;
        dateRangeMonthSelect.appendChild(option);
    });

    dateRangeYearSelect.replaceChildren();

    const currentYear = new Date().getFullYear();
    for (let year = currentYear; year >= 1990; year -= 1) {
        const option = document.createElement("option");
        option.value = String(year);
        option.textContent = String(year);
        dateRangeYearSelect.appendChild(option);
    }
}

dateRangeMonthSelect.addEventListener("change", () => {
    customRangeMonth = new Date(
        Number(dateRangeYearSelect.value),
        Number(dateRangeMonthSelect.value),
        1
    );
    renderCustomDateCalendar();
});

dateRangeYearSelect.addEventListener("change", () => {
    customRangeMonth = new Date(
        Number(dateRangeYearSelect.value),
        Number(dateRangeMonthSelect.value),
        1
    );
    renderCustomDateCalendar();
});


function renderCustomDateCalendar() {
    const year = customRangeMonth.getFullYear();
    const month = customRangeMonth.getMonth();

    dateRangeMonthSelect.value = String(month);
    dateRangeYearSelect.value = String(year);

    dateRangeCalendar.replaceChildren();

    const firstDay = new Date(year, month, 1);
    const gridStart = new Date(year, month, 1 - firstDay.getDay());

    const todayKey = toDateKey(new Date());
    const startKey = customRangeStart ? toDateKey(customRangeStart) : null;
    const endKey = customRangeEnd ? toDateKey(customRangeEnd) : null;

    for (let index = 0; index < 42; index += 1) {
        const date = new Date(gridStart);
        date.setDate(gridStart.getDate() + index);

        const key = toDateKey(date);
        const button = document.createElement("button");

        button.type = "button";
        button.className = "date-range-day";
        button.textContent = String(date.getDate());
        button.dataset.date = key;
        button.setAttribute("role", "gridcell");
        button.setAttribute("aria-label", formatCalendarDate(date));

        if (date.getMonth() !== month) {
            button.classList.add("is-other-month");
        }

        if (key === todayKey) {
            button.classList.add("is-today");
        }

        if (startKey && endKey && key > startKey && key < endKey) {
            button.classList.add("is-in-range");
        }

        if (key === startKey) {
            button.classList.add("is-start");
        }

        if (key === endKey) {
            button.classList.add("is-end");
        }

        button.addEventListener("click", () => {
            const selected = new Date(
                date.getFullYear(),
                date.getMonth(),
                date.getDate()
            );

            if (!customRangeStart || (customRangeStart && customRangeEnd)) {
                customRangeStart = selected;
                customRangeEnd = null;
            } else if (selected < customRangeStart) {
                customRangeEnd = customRangeStart;
                customRangeStart = selected;
            } else {
                customRangeEnd = selected;
            }

            updateCustomDateRangeLabels();
            renderCustomDateCalendar();
        });

        dateRangeCalendar.appendChild(button);
    }

    applyCustomDateRange.disabled = !(customRangeStart && customRangeEnd);
}


function updateCustomDateRangeLabels() {
    dateRangeStartLabel.textContent = customRangeStart
        ? formatCalendarDate(customRangeStart)
        : "Select date";

    dateRangeEndLabel.textContent = customRangeEnd
        ? formatCalendarDate(customRangeEnd)
        : "Select date";
}


dateRangePreviousMonth.addEventListener("click", () => {
    customRangeMonth = new Date(
        customRangeMonth.getFullYear(),
        customRangeMonth.getMonth() - 1,
        1
    );
    renderCustomDateCalendar();
});


dateRangeNextMonth.addEventListener("click", () => {
    customRangeMonth = new Date(
        customRangeMonth.getFullYear(),
        customRangeMonth.getMonth() + 1,
        1
    );
    renderCustomDateCalendar();
});


initializeDateRangeSelectors();

function resetCustomDateRange() {
    customRangeStart = null;
    customRangeEnd = null;
    appliedCustomRangeStart = null;
    appliedCustomRangeEnd = null;
    customRangeMonth = new Date(
        new Date().getFullYear(),
        new Date().getMonth(),
        1
    );
    updateCustomDateRangeLabels();
    renderCustomDateCalendar();
}


function getTradeFilterDate(trade) {
    const rawAnchorTime = trade?.chartAnchorTime;

    if (rawAnchorTime != null && rawAnchorTime !== "") {
        const numericAnchorTime = Number(rawAnchorTime);
        const anchorDate = Number.isFinite(numericAnchorTime)
            ? new Date(
                Math.abs(numericAnchorTime) < 1e11
                    ? numericAnchorTime * 1000
                    : numericAnchorTime
            )
            : new Date(rawAnchorTime);

        if (!Number.isNaN(anchorDate.getTime())) {
            return anchorDate;
        }
    }

    const timestamp = typeof trade?.timestamp === "string"
        ? trade.timestamp.trim()
        : "";

    if (timestamp) {
        const tradeDate = new Date(timestamp);
        if (!Number.isNaN(tradeDate.getTime())) {
            return tradeDate;
        }
    }

    return null;
}


function getTradeFilterDateKey(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}


function getDateRangeBounds(range) {
    if (!range) {
        return null;
    }

    const now = new Date();
    const today = new Date(
        now.getFullYear(),
        now.getMonth(),
        now.getDate()
    );

    if (range === "today") {
        return { from: today, to: today };
    }

    if (range === "7" || range === "30") {
        const days = Number(range);
        const from = new Date(today);
        from.setDate(from.getDate() - (days - 1));
        return { from, to: today };
    }

    if (range === "month") {
        return {
            from: new Date(today.getFullYear(), today.getMonth(), 1),
            to: today
        };
    }

    if (range === "custom") {
        if (!appliedCustomRangeStart || !appliedCustomRangeEnd) {
            return null;
        }

        return {
            from: new Date(
                appliedCustomRangeStart.getFullYear(),
                appliedCustomRangeStart.getMonth(),
                appliedCustomRangeStart.getDate(),
                0, 0, 0, 0
            ),
            to: new Date(
                appliedCustomRangeEnd.getFullYear(),
                appliedCustomRangeEnd.getMonth(),
                appliedCustomRangeEnd.getDate(),
                23, 59, 59, 999
            )
        };
    }

    return null;
}


function getFilteredTrades() {

    const dateRange = getDateRangeBounds(filterControls.dateRange.value);

    return trades.filter(trade => {
        if (edgeMapSelectedTradeIds && !edgeMapSelectedTradeIds.has(trade.id)) {
            return false;
        }

        const filterDate = getTradeFilterDate(trade);

        if (dateRange) {
            if (!filterDate) {
                return false;
            }

            const tradeDateKey = getTradeFilterDateKey(filterDate);
            const fromKey = getTradeFilterDateKey(dateRange.from);
            const toKey = getTradeFilterDateKey(dateRange.to);

            if (tradeDateKey < fromKey || tradeDateKey > toKey) {
                return false;
            }
        }

        if (searchResultIds && !searchResultIds.has(trade.id)) {
            return false;
        }

        if (
            filterControls.symbol.value &&
            trade.symbol !== filterControls.symbol.value
        ) {
            return false;
        }

        if (
            filterControls.timeframe.value &&
            trade.timeframe !== filterControls.timeframe.value
        ) {
            return false;
        }

        if (filterControls.result.value === "CAPTURED" && trade.result) {
            return false;
        }

        if (
            filterControls.result.value &&
            filterControls.result.value !== "CAPTURED" &&
            trade.result !== filterControls.result.value
        ) {
            return false;
        }

        if (
            filterControls.setup.value &&
            trade.setup !== filterControls.setup.value
        ) {
            return false;
        }

        if (
            filterControls.session.value &&
            trade.session !== filterControls.session.value
        ) {
            return false;
        }

        return true;
    });
}

function createTradeCard(trade) {

    const card = document.createElement("article");
    card.className = "trade-card";
    card.tabIndex = 0;
    card.setAttribute("role", "button");
    card.setAttribute(
        "aria-label",
        `Open review for ${trade.symbol || "captured trade"}`
    );

    if (trade.screenshot) {
        const image = document.createElement("img");
        image.className = "card-image";
        image.src = trade.screenshot;
        image.alt = `Captured chart for ${trade.symbol || "trade"}`;
        card.appendChild(image);
    } else {
        const placeholder = document.createElement("div");
        placeholder.className = "image-placeholder";
        placeholder.textContent = "No chart screenshot";
        card.appendChild(placeholder);
    }

    const content = document.createElement("div");
    content.className = "card-content";

    const topline = document.createElement("div");
    topline.className = "card-topline";

    const title = document.createElement("h3");
    title.className = "card-title";
    title.textContent = trade.symbol || "Untitled trade";

    const result = document.createElement("span");
    result.className = getResultClass(trade.result);
    result.textContent = getResultLabel(trade.result);

    topline.append(title, result);

    const meta = document.createElement("p");
    meta.className = "card-meta";
    meta.textContent = [
        trade.timeframe || "No timeframe",
        trade.direction || "No direction",
        trade.setup || null,
        trade.chartAnchorTime
            ? `Chart ${formatDate(trade.chartAnchorTime)}`
            : null,
        formatDate(trade.timestamp)
    ].filter(Boolean).join(" · ");

    const footer = document.createElement("div");
    footer.className = "card-footer";

    const plannedR = document.createElement("span");
    plannedR.textContent = `Plan ${formatR(calculatePlannedR(trade))}`;

    const actualR = document.createElement("span");
    actualR.textContent = `Actual ${formatR(calculateActualR(trade))}`;

    footer.append(plannedR, actualR);
    content.append(topline, meta, footer);
    card.appendChild(content);

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "card-delete-button";
    deleteButton.textContent = "Delete";
    deleteButton.setAttribute("aria-label", `Delete ${trade.symbol || "trade"}`);
    deleteButton.addEventListener("click", event => {
        event.stopPropagation();
        deleteTradeById(trade.id);
    });
    card.appendChild(deleteButton);

    card.addEventListener("click", () => openTrade(trade.id));
    card.addEventListener("keydown", event => {

        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openTrade(trade.id);
        }
    });

    return card;
}


async function runJournalSearch() {
    const query = tradeSearch.value.trim();
    searchQuery = query;
    clearSearch.hidden = !query;

    if (!query) {
        searchResultIds = null;
        searchStatus.textContent = "";
        renderTradeGrid();
        return;
    }

    searchStatus.textContent = "Searching your local journal…";
    try {
        const results = await searchLocalTrades(query);
        searchResultIds = new Set(results.map(trade => trade.id));
        searchStatus.textContent = `${results.length} matching trade${results.length === 1 ? "" : "s"}`;
    } catch (error) {
        // Keep search useful when the service is offline by searching loaded fields.
        const lowered = query.toLowerCase();
        searchResultIds = new Set(
            trades.filter(trade => JSON.stringify(trade).toLowerCase().includes(lowered))
                .map(trade => trade.id)
        );
        searchStatus.textContent = "Local service unavailable; searched loaded records.";
    }
    renderTradeGrid();
}


function renderTradeGrid() {

    tradeGrid.replaceChildren();
    const filteredTrades = getFilteredTrades();

    emptyState.hidden = filteredTrades.length > 0;

    if (trades.length > 0 && filteredTrades.length === 0) {
        emptyState.querySelector("h3").textContent = "No trades match these filters.";
        emptyState.querySelector("p").textContent = "Clear one or more filters to return to your full trade library.";
    } else {
        emptyState.querySelector("h3").textContent = "Your first review starts on the chart.";
        emptyState.querySelector("p").textContent = "Finish a trade in TradingView, leave its Risk/Reward tool visible, then use Capture Trade from the extension.";
    }

    document.getElementById("libraryCount").textContent =
        filteredTrades.length === trades.length
            ? `${trades.length} ${trades.length === 1 ? "trade" : "trades"}`
            : `${filteredTrades.length} of ${trades.length} trades`;

    filteredTrades
        .forEach(trade => {
            tradeGrid.appendChild(createTradeCard(trade));
        });
}


async function loadTrades() {

    const [storedTrades, storageUsage] = await Promise.all([
        getTrades(),
        getStorageUsage()
    ]);

    trades = storedTrades;
    const pendingReviews = trades.filter(trade => !trade.result).length;
    document.getElementById("todaySignalTitle").textContent = pendingReviews
        ? `${pendingReviews} trade${pendingReviews === 1 ? "" : "s"} waiting for review.`
        : "Your trading memory is up to date.";
    document.getElementById("todaySignalCopy").textContent = pendingReviews
        ? "Your chart context is saved. Take a few seconds to record what happened."
        : "Capture the decision. Review the outcome. Let the evidence accumulate.";
    populateFilters();
    renderStats();
    renderStorageUsage(storageUsage);
    onboarding.hidden = trades.length >= 3;
    renderWeeklyReview();
    renderTradeGrid();
    await loadPatternReview();
    await loadExperiments();
    await loadStorageSettings();
}


function setResultButtons() {

    document
        .querySelectorAll(".result-button")
        .forEach(button => {
            const selected = button.dataset.result === selectedResult;
            button.classList.toggle("selected", selected);
            button.setAttribute("aria-pressed", String(selected));
        });
}


async function compareSimilarTrades() {
    if (!selectedTradeId) return;
    const button = document.getElementById("compareTradesButton");
    const output = document.getElementById("compareTradesInsight");
    button.disabled = true;
    button.textContent = "Comparing…";
    output.textContent = "Comparing with your similar journal records locally…";
    output.hidden = false;
    try {
        const insight = await compareLocalTrade(selectedTradeId);
        output.textContent = insight.action
            ? `${insight.summary} Question: ${insight.action}`
            : insight.summary;
    } catch (error) {
        output.textContent = "Start the local service and Ollama, then try again.";
    } finally {
        button.disabled = false;
        button.textContent = "Compare locally";
    }
}


async function loadSimilarTrades(tradeId) {
    const status = document.getElementById("similarTradesStatus");
    const list = document.getElementById("similarTradesList");
    list.replaceChildren();
    status.textContent = "Loading related records…";
    try {
        const matches = await getSimilarLocalTrades(tradeId);
        if (!matches.length) {
            status.textContent = "No comparable journal records yet.";
            return;
        }
        status.textContent = `${matches.length} related record${matches.length === 1 ? "" : "s"}`;
        matches.forEach(match => {
            const item = document.createElement("button");
            item.type = "button";
            item.className = "similar-trade-item";
            item.textContent = `${match.symbol || "Trade"} · ${match.timeframe || "—"} · ${getResultLabel(match.result)} · ${formatDate(match.timestamp)}`;
            item.addEventListener("click", () => openTrade(match.id));
            list.appendChild(item);
        });
    } catch (error) {
        status.textContent = "Start the local service to load related records.";
    }
}


function openTrade(tradeId) {

    const trade = trades.find(item => item.id === tradeId);

    if (!trade) {
        return;
    }

    selectedTradeId = trade.id;
    selectedResult = trade.result;
    resetAIInsight();

    document.getElementById("modalTitle").textContent =
        trade.symbol || "Trade";
    document.getElementById("detailHeaderResult").textContent =
        trade.result || "—";
    document.getElementById("detailHeaderDirection").textContent =
        trade.direction || "—";
    document.getElementById("detailHeaderTimeframe").textContent =
        trade.timeframe || "—";
    document.getElementById("detailHeaderDate").textContent =
        formatDateTime(trade.chartAnchorTime || trade.timestamp);
    document.getElementById("detailSymbol").textContent = trade.symbol || "—";
    document.getElementById("detailTimeframe").textContent = trade.timeframe || "—";
    document.getElementById("detailDirection").textContent = trade.direction || "—";
    document.getElementById("detailEntry").textContent = formatNumber(trade.entry);
    document.getElementById("detailSL").textContent = formatNumber(trade.stopLoss);
    document.getElementById("detailTP").textContent = formatNumber(trade.takeProfit);
    document.getElementById("detailPlannedR").textContent = formatR(calculatePlannedR(trade));
    const actualR = calculateActualR(trade);
    document.getElementById("detailActualR").textContent =
        actualR == null ? "Not recorded" : formatR(actualR);
    document.getElementById("detailChartTime").textContent = formatDateTime(
        trade.chartAnchorTime
    );
    document.getElementById("detailCaptureTime").textContent = formatDateTime(
        trade.timestamp
    );
    document.getElementById("tradeExitPrice").value = trade.exitPrice ?? "";
    document.getElementById("tradeSetup").value = trade.setup;
    document.getElementById("tradeSession").value = trade.session || "";
    document.getElementById("tradePlanAdherence").value = trade.planAdherence || "";
    document.getElementById("tradeExecutionTag").value = trade.executionTag || "";
    document.getElementById("tradeNotes").value = trade.notes;
    document.getElementById("tradeEmotions").value = trade.emotions.join(", ");

    const screenshot = document.getElementById("tradeScreenshot");
    const missingScreenshot = document.getElementById("missingScreenshot");

    screenshot.hidden = !trade.screenshot;
    missingScreenshot.hidden = Boolean(trade.screenshot);

    if (trade.screenshot) {
        screenshot.src = trade.screenshot;
    } else {
        screenshot.removeAttribute("src");
    }

    setResultButtons();
    modal.classList.add("active");
    modal.setAttribute("aria-hidden", "false");
    document.getElementById("closeModal").focus();
    loadAIInsight(trade.id);
    loadSimilarTrades(trade.id);
}


function closeModal() {

    modal.classList.remove("active");
    modal.setAttribute("aria-hidden", "true");
    selectedTradeId = null;
    selectedResult = null;
}


async function deleteTradeById(tradeId) {
    if (!tradeId) return;
    if (!window.confirm("Delete this trade and its saved screenshot? This cannot be undone.")) return;
    try {
        await deleteTrade(tradeId);
        trades = trades.filter(trade => trade.id !== tradeId);
        if (selectedTradeId === tradeId) closeModal();
        populateFilters();
        renderStats();
        renderWeeklyReview();
        renderTradeGrid();
        await loadPatternReview();
    } catch (error) {
        alert(error?.message || "You Can't Trade could not delete this trade. Restart the local service and try again.");
    }
}


async function deleteSelectedTrade() {
    await deleteTradeById(selectedTradeId);
}


async function saveCurrentTrade() {

    if (!selectedTradeId) {
        return;
    }

    const exitPriceText = document.getElementById("tradeExitPrice").value.trim();
    const exitPrice = exitPriceText === ""
        ? null
        : Number(exitPriceText);

    if (exitPrice !== null && !Number.isFinite(exitPrice)) {
        alert("Enter a valid exit price or leave the field blank.");
        return;
    }

    const changes = {
        result: selectedResult,
        exitPrice,
        setup: document.getElementById("tradeSetup").value.trim(),
        session: document.getElementById("tradeSession").value || null,
        planAdherence:
            document.getElementById("tradePlanAdherence").value || null,
        executionTag:
            document.getElementById("tradeExecutionTag").value || null,
        notes: document.getElementById("tradeNotes").value.trim(),
        emotions: document
            .getElementById("tradeEmotions")
            .value
            .split(",")
            .map(emotion => emotion.trim())
            .filter(Boolean)
    };

    try {

        const updatedTrade = await updateTrade(
            selectedTradeId,
            changes
        );

        if (!updatedTrade) {
            throw new Error("This trade no longer exists in local storage.");
        }

        trades = trades.map(trade =>
            trade.id === updatedTrade.id
                ? updatedTrade
                : trade
        );

        renderStats();
        populateFilters();
        renderWeeklyReview();
        renderTradeGrid();
        closeModal();

    } catch (error) {

        console.error("❌ TRADE REVIEW SAVE FAILED", error);
        alert(
            error?.message ||
            "You Can't Trade could not save this review."
        );
    }
}


document
    .querySelectorAll(".result-button")
    .forEach(button => {
        button.addEventListener("click", () => {
            selectedResult = button.dataset.result;
            setResultButtons();
        });
    });

document
    .getElementById("saveTradeButton")
    .addEventListener("click", saveCurrentTrade);

document
    .getElementById("deleteTradeButton")
    .addEventListener("click", deleteSelectedTrade);

document
    .getElementById("analyzeTradeButton")
    .addEventListener("click", analyzeSelectedTrade);

document
    .getElementById("compareTradesButton")
    .addEventListener("click", compareSimilarTrades);

document
    .getElementById("analyzePatternsButton")
    .addEventListener("click", analyzePatterns);

document
    .getElementById("closeModal")
    .addEventListener("click", closeModal);

tradeSearch.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(runJournalSearch, 220);
});

clearSearch.addEventListener("click", () => {
    tradeSearch.value = "";
    runJournalSearch();
    tradeSearch.focus();
});

Object.values(filterControls).forEach(control => {
    control.addEventListener("change", renderTradeGrid);
});

function updateCustomDateRangeVisibility() {
    const isCustom = filterControls.dateRange.value === "custom";
    customDateRange.hidden = !isCustom;

    if (isCustom) {
        renderCustomDateCalendar();
    }
}


filterControls.dateRange.addEventListener("change", () => {
    if (filterControls.dateRange.value === "custom") {
        resetCustomDateRange();
        customDateRange.hidden = false;
        return;
    }

    resetCustomDateRange();
    customDateRange.hidden = true;
    renderTradeGrid();
});


applyCustomDateRange.addEventListener("click", () => {
    if (!customRangeStart || !customRangeEnd) {
        return;
    }

    appliedCustomRangeStart = new Date(customRangeStart);
    appliedCustomRangeEnd = new Date(customRangeEnd);

    renderTradeGrid();
});


updateCustomDateRangeVisibility();




document.getElementById("newExperimentButton").addEventListener("click", () => {
    document.getElementById("experimentComposer").hidden = false;
    document.getElementById("experimentBehavior").focus();
});

document.getElementById("cancelExperimentButton").addEventListener("click", () => {
    document.getElementById("experimentComposer").hidden = true;
});

document.getElementById("saveExperimentButton").addEventListener("click", async () => {
    const behavior = document.getElementById("experimentBehavior").value.trim();
    const status = document.getElementById("experimentComposerStatus");
    if (!behavior) { status.textContent = "Add one behaviour to test."; return; }
    status.textContent = "Starting experiment…";
    try {
        await createLocalExperiment({ behavior, title: behavior, hypothesis: document.getElementById("experimentHypothesis").value.trim(), sampleTarget: Number(document.getElementById("experimentSample").value) });
        document.getElementById("experimentComposer").hidden = true;
        document.getElementById("experimentBehavior").value = "";
        document.getElementById("experimentHypothesis").value = "";
        await loadExperiments();
    } catch (error) { status.textContent = "Start the local service to save this experiment."; }
});

document.getElementById("useLocalStorageButton").addEventListener("click", async () => {
    const status = document.getElementById("notionSetupStatus");
    try {
        await selectStorageProvider("local");
        await loadStorageSettings();
        status.textContent = "You Can't Trade Local is active.";
    } catch (error) { status.textContent = error.message || "Could not switch to local storage."; }
});

document.getElementById("connectNotionButton").addEventListener("click", () => {
    document.getElementById("notionSetup").hidden = false;
    document.getElementById("notionToken").focus();
});

document.getElementById("validateNotionButton").addEventListener("click", connectNotionFromSettings);
document.getElementById("configureNotionButton").addEventListener("click", configureNotionFromSettings);
document.getElementById("disconnectNotionButton").addEventListener("click", async () => {
    try { await disconnectNotion(); await loadStorageSettings(); document.getElementById("notionSetupStatus").textContent = "Disconnected. Your Notion data was not deleted."; }
    catch (error) { document.getElementById("notionSetupStatus").textContent = error.message || "Could not disconnect Notion."; }
});

document.getElementById("retryStorageButton").addEventListener("click", async () => {
    const status = document.getElementById("notionSetupStatus");
    status.textContent = "Retrying pending Notion saves…";
    try {
        const result = await retryStorageOutbox();
        status.textContent = result.pending ? `${result.retried} saved. ${result.pending} still waiting.` : `${result.retried} pending save${result.retried === 1 ? "" : "s"} completed.`;
        await loadStorageSettings();
        await loadTrades();
    } catch (error) { status.textContent = error.message || "Could not retry pending saves."; }
});

document.getElementById("clearStorageCacheButton").addEventListener("click", async () => {
    const status = document.getElementById("notionSetupStatus");
    status.textContent = "Clearing You Can't Trade cache…";
    try {
        const result = await clearStorageCache();
        status.textContent = `${result.clearedRecords || 0} cached record${result.clearedRecords === 1 ? "" : "s"} cleared. Notion data was not deleted.`;
        renderStorageStatus(result.status);
    } catch (error) { status.textContent = error.message || "Could not clear the cache."; }
});

document.getElementById("notionDatabaseSelect").addEventListener("change", async event => {
    const sourceSelect = document.getElementById("notionDataSourceSelect");
    sourceSelect.replaceChildren(new Option("Select a data source", ""));
    if (!event.target.value) return;
    try {
        const result = await getNotionDatabase(event.target.value);
        (result.dataSources || []).forEach(source => sourceSelect.appendChild(new Option(source.name || source.title?.[0]?.plain_text || source.id, source.id)));
    } catch (error) { document.getElementById("notionSetupStatus").textContent = error.message || "Could not load data sources."; }
});

document.getElementById("createNotionFieldsButton").addEventListener("click", async () => {
    const sourceId = document.getElementById("notionDataSourceSelect").value;
    if (!sourceId) return;
    try { await createNotionFields(sourceId); document.getElementById("notionSetupStatus").textContent = "You Can't Trade fields created. Enable Notion storage when ready."; }
    catch (error) { document.getElementById("notionSetupStatus").textContent = error.message || "Could not create fields."; }
});

document
    .getElementById("clearFilters")
    .addEventListener("click", () => {
        tradeSearch.value = "";
        searchQuery = "";
        searchResultIds = null;
        clearSearch.hidden = true;
        searchStatus.textContent = "";

        Object.values(filterControls).forEach(control => {
            control.value = "";
        });

        resetCustomDateRange();
        customDateRange.hidden = true;
        edgeMapSelectedTradeIds = null;

        renderTradeGrid();
    });

document
    .getElementById("exportJournal")
    .addEventListener("click", async () => {
        const exportData = {
            product: "You Can't Trade",
            exportedAt: new Date().toISOString(),
            tradeCount: trades.length,
            trades: await getTrades()
        };
        const file = new Blob(
            [JSON.stringify(exportData, null, 2)],
            { type: "application/json" }
        );
        const downloadUrl = URL.createObjectURL(file);
        const link = document.createElement("a");

        link.href = downloadUrl;
        link.download = `you-cant-trade-journal-${new Date().toISOString().slice(0, 10)}.json`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(downloadUrl);
    });

modal.addEventListener("click", event => {

    if (event.target === modal) {
        closeModal();
    }
});

document.addEventListener("keydown", event => {

    if (event.key === "Escape" && modal.classList.contains("active")) {
        closeModal();
    }
});

bindEdgeMapControls();
loadEdgeMap();

bindCompareControls();

loadTrades()
    .then(() => loadCompare())
    .catch(error => {
    console.error("❌ DASHBOARD LOAD FAILED", error);
    const status = document.getElementById("searchStatus");
    status.textContent = "Could not load the local journal. Check that the service is running, then reload.";
    emptyState.hidden = false;
    emptyState.querySelector("h3").textContent = "Journal connection unavailable.";
    emptyState.querySelector("p").textContent = "Start the local service and reload this dashboard.";
});

loadLeakMap();
loadMemory();


if (closeMemoryDetails) {
    closeMemoryDetails.addEventListener("click", () => {
        if (memoryDetails) {
            memoryDetails.hidden = true;
        }
        memoryContent?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
}


if (closeLeakDetails) {
    closeLeakDetails.addEventListener("click", () => {
        if (leakDetails) {
            leakDetails.hidden = true;
        }
        document.getElementById("leakMap")?.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    });
}
