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
    getLocalCurrentUnderstanding,
    getLocalAnalytics,
    getLocalPatterns,
    getLocalEdgeMap,
    getLocalLeakMap,
    getLocalCompare,
    getLocalMemory,
    createLocalMemory,
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
let insightsPatternPayload = null;
let insightsTradeCount = 0;
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
const memorySearch = document.getElementById("memorySearch");
const memoryTypeFilter = document.getElementById("memoryTypeFilter");
const memoryStatusFilter = document.getElementById("memoryStatusFilter");
const memoryEvidenceFilter = document.getElementById("memoryEvidenceFilter");
const clearMemoryFilters = document.getElementById("clearMemoryFilters");
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
    const conclusionContent = document.getElementById("edgeConclusionContent");

    if (conclusionContent) {
        conclusionContent.replaceChildren();

        const labels = {
            setup: "Setup",
            session: "Session",
            direction: "Direction",
            market_regime: "Regime",
            structure_state: "Market structure"
        };

        const evidenceRank = {
            STRONG: 3,
            MODERATE: 2,
            LIMITED: 1,
            LOW: 1,
            UNKNOWN: 0
        };

        const performanceValue = cell => {
            if (cell.expectancy != null) {
                return Number(cell.expectancy);
            }

            if (cell.averageR != null) {
                return Number(cell.averageR);
            }

            return null;
        };

        const supportedEdges = [...cells]
            .filter(cell =>
                ["STRONG", "MODERATE"].includes(
                    cell.evidenceStrength?.level
                ) &&
                performanceValue(cell) != null &&
                performanceValue(cell) > 0
            )
            .sort((left, right) => {
                const evidenceDifference =
                    (evidenceRank[right.evidenceStrength?.level] || 0) -
                    (evidenceRank[left.evidenceStrength?.level] || 0);

                if (evidenceDifference !== 0) {
                    return evidenceDifference;
                }

                const performanceDifference =
                    performanceValue(right) - performanceValue(left);

                if (performanceDifference !== 0) {
                    return performanceDifference;
                }

                return (right.sampleSize || 0) - (left.sampleSize || 0);
            });

        const positiveConditions = [...cells]
            .filter(cell =>
                performanceValue(cell) != null &&
                performanceValue(cell) > 0
            )
            .sort((left, right) => {
                const evidenceDifference =
                    (evidenceRank[right.evidenceStrength?.level] || 0) -
                    (evidenceRank[left.evidenceStrength?.level] || 0);

                if (evidenceDifference !== 0) {
                    return evidenceDifference;
                }

                const performanceDifference =
                    performanceValue(right) - performanceValue(left);

                if (performanceDifference !== 0) {
                    return performanceDifference;
                }

                return (right.sampleSize || 0) - (left.sampleSize || 0);
            })
            .slice(0, 3);

        const intro = document.createElement("div");
        intro.className = "edge-conclusion-intro";

        const heading = document.createElement("h3");
        const description = document.createElement("p");

        if (supportedEdges.length) {
            const primary = supportedEdges[0];
            const value = performanceValue(primary);

            heading.textContent = "Something is starting to stand out.";
            description.textContent =
                `${labels[primary.dimensionA] || primary.dimensionA} · ` +
                `${primary.valueA} × ` +
                `${labels[primary.dimensionB] || primary.dimensionB} · ` +
                `${primary.valueB} is showing positive historical performance with ` +
                `${primary.sampleSize || 0} trades.`;
        } else if (positiveConditions.length) {
            heading.textContent = "No clear edge is standing out yet.";
            description.textContent =
                "Some conditions are performing positively, but the evidence isn't strong enough yet to treat them as a reliable edge.";
        } else {
            heading.textContent = "No clear edge is standing out yet.";
            description.textContent =
                "YCT hasn't found a condition with enough positive historical evidence to call an edge yet.";
        }

        intro.append(heading, description);
        conclusionContent.appendChild(intro);

        if (supportedEdges.length) {
            const primary = supportedEdges[0];
            const primaryRow = document.createElement("div");
            primaryRow.className = "edge-conclusion-primary";

            const context = document.createElement("strong");
            context.textContent =
                `${labels[primary.dimensionA] || primary.dimensionA} · ${primary.valueA} × ` +
                `${labels[primary.dimensionB] || primary.dimensionB} · ${primary.valueB}`;

            const evidence = document.createElement("span");
            evidence.textContent =
                `${primary.sampleSize || 0} trades · ` +
                `${performanceValue(primary).toFixed(2)}R expectancy · ` +
                `${primary.evidenceStrength?.level || "Unknown"} evidence`;

            primaryRow.append(context, evidence);
            conclusionContent.appendChild(primaryRow);
        }

        const watchList = supportedEdges.length
            ? supportedEdges.slice(1, 4)
            : positiveConditions;

        if (watchList.length) {
            const watchHeading = document.createElement("h4");
            watchHeading.className = "edge-conclusion-heading";
            watchHeading.textContent = supportedEdges.length
                ? "Other conditions worth watching"
                : "Conditions worth watching";
            conclusionContent.appendChild(watchHeading);

            const list = document.createElement("div");
            list.className = "edge-conclusion-list";

            watchList.forEach(cell => {
                const item = document.createElement("article");
                item.className = "edge-conclusion-item";

                const context = document.createElement("div");
                context.className = "edge-conclusion-context";
                context.textContent =
                    `${labels[cell.dimensionA] || cell.dimensionA} · ${cell.valueA} × ` +
                    `${labels[cell.dimensionB] || cell.dimensionB} · ${cell.valueB}`;

                const metrics = document.createElement("div");
                metrics.className = "edge-conclusion-evidence";

                const sample = document.createElement("span");
                sample.textContent = `${cell.sampleSize || 0} trades`;

                const performance = document.createElement("span");
                performance.textContent =
                    performanceValue(cell) == null
                        ? "No R measure"
                        : `${performanceValue(cell).toFixed(2)}R expectancy`;

                const evidence = document.createElement("span");
                evidence.textContent =
                    `${cell.evidenceStrength?.level || "Unknown"} evidence`;

                metrics.append(sample, performance, evidence);

                const action = document.createElement("button");
                action.type = "button";
                action.className = "edge-conclusion-link";
                action.textContent = "See supporting trades →";
                action.disabled = !Array.isArray(cell.sourceTradeIds) ||
                    !cell.sourceTradeIds.length;

                action.addEventListener("click", event => {
                    event.stopPropagation();

                    const tradeId = cell.sourceTradeIds?.[0];

                    if (tradeId) {
                        openTrade(tradeId);
                    }
                });

                item.append(context, metrics, action);
                list.appendChild(item);
            });

            conclusionContent.appendChild(list);
        }

        const footer = document.createElement("p");
        footer.className = "edge-conclusion-footer";
        footer.textContent =
            `${cells.length} conditions meet the minimum sample · ` +
            `minimum sample ${payload?.minimumSample || 3}`;

        conclusionContent.appendChild(footer);
    }
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

        const memoryCandidate = edgeToMemoryCandidate(cell);

        if (memoryCandidate) {
            const rememberButton = document.createElement("button");
            rememberButton.type = "button";
            rememberButton.className = "edge-map-remember-button";
            rememberButton.textContent = "Remember this";

            rememberButton.addEventListener("click", async event => {
                event.stopPropagation();

                if (rememberButton.disabled) {
                    return;
                }

                const confirmed = window.confirm(
                    "Remember this edge in Trading Memory?"
                );

                if (!confirmed) {
                    return;
                }

                rememberButton.disabled = true;
                rememberButton.textContent = "Saving…";

                try {
                    await createLocalMemory(memoryCandidate);
                    rememberButton.textContent = "Remembered";
                    rememberButton.classList.add("is-remembered");
                } catch (error) {
                    console.error(
                        "Failed to save Edge to Memory:",
                        error
                    );

                    rememberButton.disabled = false;
                    rememberButton.textContent = "Remember this";

                    alert(
                        "Could not save this edge to Trading Memory."
                    );
                }
            });

            card.appendChild(rememberButton);
        }

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
        renderInsightsHybrid();
        renderEvidenceOverview();
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

        const memoryCandidate = leakToMemoryCandidate(leak);

        if (memoryCandidate) {
            const rememberButton = document.createElement("button");
            rememberButton.type = "button";
            rememberButton.className = "leak-map-remember-button";
            rememberButton.textContent = "Remember this";

            rememberButton.addEventListener("click", async event => {
                event.stopPropagation();

                if (rememberButton.disabled) {
                    return;
                }

                const confirmed = window.confirm(
                    "Remember this leak in Trading Memory?"
                );

                if (!confirmed) {
                    return;
                }

                rememberButton.disabled = true;
                rememberButton.textContent = "Saving…";

                try {
                    await createLocalMemory(memoryCandidate);
                    rememberButton.textContent = "Remembered";
                    rememberButton.classList.add("is-remembered");
                } catch (error) {
                    console.error(
                        "Failed to save Leak to Memory:",
                        error
                    );

                    rememberButton.disabled = false;
                    rememberButton.textContent = "Remember this";

                    alert(
                        "Could not save this leak to Trading Memory."
                    );
                }
            });

            card.appendChild(rememberButton);
        }

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
        renderInsightsHybrid();
        renderEvidenceOverview();
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

    const historySection = document.createElement("section");
    historySection.className = "memory-details-history";

    const historyHeading = document.createElement("h3");
    historyHeading.textContent =
        `Verification history · ${verificationHistory.length}`;
    historySection.appendChild(historyHeading);

    if (!verificationHistory.length) {
        const emptyHistory = document.createElement("p");
        emptyHistory.className = "pattern-empty";
        emptyHistory.textContent =
            "This finding has been observed, but it has not been rechecked yet.";
        historySection.appendChild(emptyHistory);
    } else {
        const historyList = document.createElement("div");
        historyList.className = "memory-details-history-list";

        verificationHistory.forEach(verification => {
            const row = document.createElement("article");
            row.className = "memory-details-history-row";

            const date = document.createElement("strong");
            date.textContent = verification.verifiedAt
                ? formatDate(verification.verifiedAt)
                : "Unknown date";

            const meta = document.createElement("div");
            meta.className = "memory-details-history-meta";

            [
                ["Status", verification.status || "—"],
                ["Sample", verification.sampleSize ?? "—"],
                ["Evidence", verification.evidenceStrength || "—"],
                [
                    "Supporting trades",
                    verification.supportingTradeCount ?? "—",
                ],
            ].forEach(([label, value]) => {
                const item = document.createElement("span");
                item.textContent = `${label}: ${value}`;
                meta.appendChild(item);
            });

            const tradeIds = Array.isArray(verification.supportingTradeIds)
                ? verification.supportingTradeIds
                : [];

            const tradeReference = document.createElement("p");
            tradeReference.textContent = tradeIds.length
                ? `Trade IDs: ${tradeIds.join(", ")}`
                : "Trade IDs: none recorded";

            row.append(date, meta, tradeReference);
            historyList.appendChild(row);
        });

        historySection.appendChild(historyList);
    }

    memoryDetailsContent.appendChild(historySection);

    const actionsIntro = document.createElement("p");
    actionsIntro.className = "memory-details-actions-intro";
    actionsIntro.textContent =
        "Rechecking compares this finding with newer evidence and records the result.";
    memoryDetailsContent.appendChild(actionsIntro);

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
                id: crypto.randomUUID(),
                verifiedAt: new Date().toISOString(),
                status: resolvedFinding.status || "OBSERVED",
                sampleSize,
                evidenceStrength: resolvedFinding.evidenceStrength || "INSUFFICIENT",
                supportingTradeIds: Array.isArray(resolvedFinding.supportingTradeIds)
                    ? resolvedFinding.supportingTradeIds
                    : [],
                contractVersion: 1,
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

    const findings = Array.isArray(payload?.findings)
        ? payload.findings
        : [];

    const searchValue = String(memorySearch?.value || "")
        .trim()
        .toLowerCase();

    const typeValue = String(memoryTypeFilter?.value || "").trim();
    const statusValue = String(memoryStatusFilter?.value || "").trim();
    const evidenceValue = String(memoryEvidenceFilter?.value || "").trim();

    const filteredFindings = findings.filter(finding => {
        const statement = String(finding.statement || "").toLowerCase();
        const type = String(finding.type || "");
        const status = String(finding.status || "");
        const evidence = String(finding.evidenceStrength || "");

        return (
            (!searchValue || statement.includes(searchValue))
            && (!typeValue || type === typeValue)
            && (!statusValue || status === statusValue)
            && (!evidenceValue || evidence === evidenceValue)
        );
    });

    const hasFilters = Boolean(
        searchValue || typeValue || statusValue || evidenceValue
    );

    memoryStatus.textContent = hasFilters
        ? `${filteredFindings.length} of ${findings.length} finding${findings.length === 1 ? "" : "s"}`
        : `${findings.length} finding${findings.length === 1 ? "" : "s"}`;

    memoryContent.replaceChildren();

    if (!findings.length) {
        const empty = document.createElement("div");
        empty.className = "memory-empty-state";

        const title = document.createElement("h3");
        title.textContent = "Nothing worth remembering yet.";

        const description = document.createElement("p");
        description.textContent =
            "YCT will keep findings here when patterns become worth carrying forward — with the evidence attached.";

        const loop = document.createElement("span");
        loop.className = "memory-empty-loop";
        loop.textContent = "Trade → Observe → Measure → Remember";

        empty.append(title, description, loop);
        memoryContent.appendChild(empty);
        return;
    }

    if (!filteredFindings.length) {
        const empty = document.createElement("p");
        empty.className = "pattern-empty";
        empty.textContent = "No memory findings match the current filters.";
        memoryContent.appendChild(empty);
        return;
    }

    const formatDateValue = value => value ? formatDate(value) : "—";

    const activeFindings = filteredFindings.filter(
        finding => String(finding.status || "OBSERVED") !== "RETIRED"
    );

    const retiredFindings = filteredFindings.filter(
        finding => String(finding.status || "OBSERVED") === "RETIRED"
    );

    const createFindingRow = finding => {
        const row = document.createElement("article");
        row.className = `memory-row ${String(
            finding.status || "OBSERVED"
        ).toLowerCase()}`;

        const identity = document.createElement("div");
        identity.className = "memory-row-identity";

        const type = document.createElement("span");
        type.className = "memory-row-type";
        type.textContent = String(finding.type || "FINDING");

        const status = document.createElement("span");
        status.className = "memory-row-status";
        status.textContent = String(finding.status || "OBSERVED");

        identity.append(type, status);

        const statement = document.createElement("h3");
        statement.className = "memory-row-statement";
        statement.textContent = finding.statement || "Untitled finding";

        const evidence = document.createElement("div");
        evidence.className = "memory-row-evidence";

        const evidenceLabel = document.createElement("span");
        evidenceLabel.textContent = "Evidence";

        const evidenceValue = document.createElement("strong");
        evidenceValue.textContent = String(
            finding.evidenceStrength || "—"
        );

        evidence.append(evidenceLabel, evidenceValue);

        const sample = document.createElement("div");
        sample.className = "memory-row-metric";

        const sampleLabel = document.createElement("span");
        sampleLabel.textContent = "Sample";

        const sampleValue = document.createElement("strong");
        sampleValue.textContent = String(finding.sampleSize ?? "—");

        sample.append(sampleLabel, sampleValue);

        const firstObserved = document.createElement("div");
        firstObserved.className = "memory-row-metric";

        const firstObservedLabel = document.createElement("span");
        firstObservedLabel.textContent = "First observed";

        const firstObservedValue = document.createElement("strong");
        firstObservedValue.textContent =
            formatDateValue(finding.firstObserved);

        firstObserved.append(firstObservedLabel, firstObservedValue);

        const lastVerified = document.createElement("div");
        lastVerified.className = "memory-row-metric";

        const lastVerifiedLabel = document.createElement("span");
        lastVerifiedLabel.textContent = "Last verified";

        const lastVerifiedValue = document.createElement("strong");
        lastVerifiedValue.textContent =
            formatDateValue(finding.lastVerified);

        lastVerified.append(lastVerifiedLabel, lastVerifiedValue);

        const tradeCount = Array.isArray(finding.supportingTradeIds)
            ? finding.supportingTradeIds.length
            : 0;

        const supporting = document.createElement("div");
        supporting.className = "memory-row-supporting";
        supporting.textContent =
            `${tradeCount} supporting trade${tradeCount === 1 ? "" : "s"}`;

        const metadata = document.createElement("div");
        metadata.className = "memory-row-metadata";
        metadata.append(
            evidence,
            sample,
            firstObserved,
            lastVerified,
            supporting
        );

        row.append(identity, statement, metadata);

        row.tabIndex = 0;
        row.setAttribute("role", "button");

        const openDetails = () => openMemoryDetails(finding);

        row.addEventListener("click", openDetails);

        row.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openDetails();
            }
        });

        return row;
    };

    const appendSection = (titleText, sectionFindings, sectionClass) => {
        if (!sectionFindings.length) {
            return;
        }

        const section = document.createElement("section");
        section.className = `memory-section ${sectionClass}`;

        const header = document.createElement("div");
        header.className = "memory-section-header";

        const title = document.createElement("h3");
        title.textContent = titleText;

        const count = document.createElement("span");
        count.textContent =
            `${sectionFindings.length} finding${sectionFindings.length === 1 ? "" : "s"}`;

        header.append(title, count);

        const ledger = document.createElement("div");
        ledger.className = "memory-ledger";

        sectionFindings.forEach(finding => {
            ledger.appendChild(createFindingRow(finding));
        });

        section.append(header, ledger);
        memoryContent.appendChild(section);
    };

    appendSection(
        "Active memory",
        activeFindings,
        "memory-section-active"
    );

    appendSection(
        "Retired memory",
        retiredFindings,
        "memory-section-retired"
    );
}


function refreshMemoryFilters() {
    if (memoryPayload) {
        renderMemory(memoryPayload);
    }
}

memorySearch?.addEventListener("input", refreshMemoryFilters);
memoryTypeFilter?.addEventListener("change", refreshMemoryFilters);
memoryStatusFilter?.addEventListener("change", refreshMemoryFilters);
memoryEvidenceFilter?.addEventListener("change", refreshMemoryFilters);

clearMemoryFilters?.addEventListener("click", () => {
    if (memorySearch) {
        memorySearch.value = "";
    }
    if (memoryTypeFilter) {
        memoryTypeFilter.value = "";
    }
    if (memoryStatusFilter) {
        memoryStatusFilter.value = "";
    }
    if (memoryEvidenceFilter) {
        memoryEvidenceFilter.value = "";
    }
    refreshMemoryFilters();
});


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
        renderInsightsHybrid();
        renderEvidenceOverview();
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




function renderEvidenceOverview() {
    const setText = (id, value) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    };

    const patterns = Array.isArray(insightsPatternPayload?.patterns)
        ? [...insightsPatternPayload.patterns]
        : [];

    const edges = Array.isArray(edgeMapPayload?.cells)
        ? [...edgeMapPayload.cells]
        : [];

    const leaks = Array.isArray(leakMapPayload?.leaks)
        ? [...leakMapPayload.leaks]
        : [];

    const current = comparePayload?.periods?.current;
    const previous = comparePayload?.periods?.previous;

    const evidenceRank = {
        STRONG: 3,
        MODERATE: 2,
        LIMITED: 1,
        LOW: 1,
        UNKNOWN: 0,
    };

    const patternLevel = finding =>
        finding?.evidenceStrength?.level ||
        finding?.evidenceStrength ||
        "UNKNOWN";

    const leakLevel = leak =>
        leak?.evidenceStrength?.level ||
        leak?.evidenceStrength ||
        "UNKNOWN";

    const sample = finding =>
        Number(finding?.sampleSize || 0);

    const totalTrades = Number(
        insightsTradeCount ||
        insightsPatternPayload?.totalTrades ||
        leakMapPayload?.sampleSize ||
        0
    );

    const reliableEdges = edges
        .filter(cell =>
            ["STRONG", "MODERATE"].includes(
                cell?.evidenceStrength?.level
            ) &&
            Number(cell?.expectancy) > 0
        );

    const repeatedLeaks = leaks
        .filter(leak =>
            Number(
                leak?.occurrenceCount ??
                leak?.occurrences ??
                leak?.count ??
                0
            ) > 0 &&
            ["STRONG", "MODERATE"].includes(leakLevel(leak))
        );

    // --------------------------------------------------------
    // Summary
    // --------------------------------------------------------

    setText("evidenceStatTrades", String(totalTrades));
    setText("evidenceStatPatterns", String(patterns.length));
    setText("evidenceStatEdges", String(reliableEdges.length));
    setText("evidenceStatLeaks", String(repeatedLeaks.length));

    // --------------------------------------------------------
    // Patterns
    // --------------------------------------------------------

    const patternList =
        document.getElementById("evidencePatternList");

    if (patternList) {
        patternList.replaceChildren();

        const ranked = patterns
            .sort((a, b) =>
                (evidenceRank[patternLevel(b)] || 0) -
                (evidenceRank[patternLevel(a)] || 0) ||
                sample(b) - sample(a)
            );

        const maxVisible = 12;

        ranked.slice(0, maxVisible).forEach(finding => {
            const row = document.createElement("button");
            row.type = "button";
            row.className = "evidence-pattern-row";

            const left = document.createElement("span");
            left.className = "evidence-pattern-name";

            const dimension = document.createElement("small");
            dimension.textContent =
                String(finding.dimension || "Condition")
                    .replaceAll("_", " ");

            const value = document.createElement("strong");
            value.textContent =
                finding.value || "—";

            left.append(dimension, value);

            const middle = document.createElement("span");
            middle.className = "evidence-pattern-sample";
            middle.textContent =
                `${sample(finding)} trades`;

            const right = document.createElement("span");
            right.className = "evidence-pattern-level";
            right.textContent =
                `${patternLevel(finding)} evidence`;

            row.append(left, middle, right);

            row.addEventListener("click", () => {
                const sourceId =
                    Array.isArray(finding.sourceTradeIds)
                        ? finding.sourceTradeIds[0]
                        : null;

                if (sourceId && typeof openTradeCaseFile === "function") {
                    openTradeCaseFile(sourceId);
                }
            });

            patternList.appendChild(row);
        });

        if (!ranked.length) {
            const empty = document.createElement("p");
            empty.className = "pattern-empty";
            empty.textContent =
                "No recurring observations have enough data to show yet.";
            patternList.appendChild(empty);
        }

        setText(
            "evidencePatternMeta",
            `${patterns.length} observations`
        );

        setText(
            "evidencePatternTitle",
            patterns.length
                ? "These are the conditions YCT keeps seeing."
                : "Nothing is repeating reliably yet."
        );
    }

    // --------------------------------------------------------
    // Edge visual
    // --------------------------------------------------------

    setText(
        "evidenceEdgeTitle",
        reliableEdges.length
            ? "Some conditions are starting to stand out."
            : "Nothing reliable yet."
    );

    setText(
        "evidenceEdgeMeta",
        `${reliableEdges.length} reliable condition${reliableEdges.length === 1 ? "" : "s"}`
    );

    const edgeGrid =
        document.getElementById("evidenceEdgeGrid");

    if (edgeGrid) {
        edgeGrid.replaceChildren();

        const visibleEdges = reliableEdges.slice(0, 9);

        for (let index = 0; index < 9; index += 1) {
            const cell = document.createElement("span");
            const edge = visibleEdges[index];

            if (edge) {
                cell.textContent =
                    Number(edge.expectancy).toFixed(1) + "R";
                cell.className =
                    Number(edge.expectancy) > 0
                        ? "evidence-edge-positive"
                        : "";
            } else {
                cell.textContent = "—";
            }

            edgeGrid.appendChild(cell);
        }
    }

    setText(
        "evidenceEdgeNote",
        reliableEdges.length
            ? "These conditions have enough historical evidence to investigate."
            : "Not enough evidence yet."
    );

    // --------------------------------------------------------
    // Leak visual
    // --------------------------------------------------------

    const leakList =
        document.getElementById("evidenceLeakList");

    if (leakList) {
        const rows =
            Array.from(
                leakList.querySelectorAll(
                    ".evidence-leak-row"
                )
            );

        const values = leaks.map(leak => ({
            label:
                leak?.label ||
                leak?.type ||
                "Leak",
            count: Number(
                leak?.occurrenceCount ??
                leak?.occurrences ??
                leak?.count ??
                0
            ),
        }));

        const maxCount =
            Math.max(
                1,
                ...values.map(item => item.count)
            );

        rows.forEach((row, index) => {
            const item = values[index];

            if (!item) {
                return;
            }

            const label = row.querySelector("span");
            const bar = row.querySelector("i");
            const count = row.querySelector("strong");

            if (label) {
                label.textContent = item.label;
            }

            if (bar) {
                bar.style.width =
                    `${Math.min(100, (item.count / maxCount) * 100)}%`;
            }

            if (count) {
                count.textContent = String(item.count);
            }
        });
    }

    setText(
        "evidenceLeakTitle",
        repeatedLeaks.length
            ? "A few behaviours are showing up repeatedly."
            : "Nothing repeated yet."
    );

    setText(
        "evidenceLeakMeta",
        `${repeatedLeaks.length} repeated leak${repeatedLeaks.length === 1 ? "" : "s"}`
    );

    // --------------------------------------------------------
    // Compare
    // --------------------------------------------------------

    const currentCount =
        Number(current?.actualCount || 0);

    const previousCount =
        Number(previous?.actualCount || 0);

    setText(
        "evidenceCurrentTrades",
        currentCount ? String(currentCount) : "—"
    );

    setText(
        "evidencePreviousTrades",
        previousCount ? String(previousCount) : "—"
    );

    setText(
        "evidenceChangeMeta",
        previousCount
            ? `${currentCount} current · ${previousCount} previous`
            : `${currentCount} current · no previous period`
    );

    if (previousCount) {
        setText(
            "evidenceChangeTitle",
            "There is enough history to compare the two periods."
        );

        setText(
            "evidenceChangeCopy",
            "Open the detailed comparison when you want to inspect what actually moved."
        );
    } else {
        setText(
            "evidenceChangeTitle",
            "Not enough history for comparison yet."
        );

        setText(
            "evidenceChangeCopy",
            "YCT needs a previous period before it can say what actually changed."
        );
    }

}


function renderInsightsHybrid() {
    const setText = (id, value) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    };

    const patterns = Array.isArray(insightsPatternPayload?.patterns)
        ? [...insightsPatternPayload.patterns]
        : [];

    const edges = Array.isArray(edgeMapPayload?.cells)
        ? [...edgeMapPayload.cells]
        : [];

    const leaks = Array.isArray(leakMapPayload?.leaks)
        ? [...leakMapPayload.leaks]
        : [];

    const current = comparePayload?.periods?.current;
    const previous = comparePayload?.periods?.previous;

    const evidenceRank = {
        STRONG: 3,
        MODERATE: 2,
        LIMITED: 1,
        LOW: 1,
        UNKNOWN: 0,
    };

    const patternLevel = finding =>
        finding?.evidenceStrength?.level ||
        finding?.evidenceStrength ||
        "UNKNOWN";

    const leakLevel = leak =>
        leak?.evidenceStrength?.level ||
        leak?.evidenceStrength ||
        "UNKNOWN";

    const patternSample = finding =>
        Number(finding?.sampleSize || 0);

    const reliablePatterns = patterns
        .filter(finding =>
            ["STRONG", "MODERATE"].includes(patternLevel(finding))
        )
        .sort((a, b) =>
            (evidenceRank[patternLevel(b)] || 0) -
            (evidenceRank[patternLevel(a)] || 0) ||
            patternSample(b) - patternSample(a)
        );

    const recurringPatterns = patterns
        .sort((a, b) =>
            (evidenceRank[patternLevel(b)] || 0) -
            (evidenceRank[patternLevel(a)] || 0) ||
            patternSample(b) - patternSample(a)
        )
        .slice(0, 3);

    const reliableEdges = edges
        .filter(cell =>
            ["STRONG", "MODERATE"].includes(
                cell?.evidenceStrength?.level
            ) &&
            Number(cell?.expectancy) > 0
        );

    const repeatedLeaks = leaks
        .filter(leak =>
            Number(
                leak?.occurrenceCount ??
                leak?.occurrences ??
                leak?.count ??
                0
            ) > 0 &&
            ["STRONG", "MODERATE"].includes(leakLevel(leak))
        );

    const totalTrades = Number(
        insightsTradeCount ||
        insightsPatternPayload?.totalTrades ||
        leakMapPayload?.sampleSize ||
        0
    );

    // --------------------------------------------------------
    // Summary numbers
    // --------------------------------------------------------

    setText("insightsStatTrades", String(totalTrades));
    setText("insightsStatPatterns", String(patterns.length));
    setText("insightsStatEdges", String(reliableEdges.length));
    setText("insightsStatLeaks", String(repeatedLeaks.length));

    // --------------------------------------------------------
    // Pattern conclusion
    // --------------------------------------------------------

    const noticingTitle =
        document.getElementById("insightsNoticingTitle");

    const noticingNote =
        document.getElementById("insightsNoticingNote");

    if (noticingTitle) {
        if (reliablePatterns.length) {
            noticingTitle.textContent =
                "Something is starting to stand out.";
        } else if (recurringPatterns.length) {
            noticingTitle.textContent =
                "A few things are beginning to repeat.";
        } else {
            noticingTitle.textContent =
                "Nothing reliable is standing out yet.";
        }
    }

    if (noticingNote) {
        if (reliablePatterns.length) {
            const primary = reliablePatterns[0];
            noticingNote.textContent =
                `${primary.dimension?.replaceAll("_", " ") || "This condition"} · ` +
                `${primary.value} has enough evidence to be worth investigating.`;
        } else if (recurringPatterns.length) {
            noticingNote.textContent =
                "They're worth watching, but YCT doesn't have enough evidence to call any of them reliable yet.";
        } else {
            noticingNote.textContent =
                "YCT needs more repeated evidence before it can tell you that a pattern actually matters.";
        }
    }

    // --------------------------------------------------------
    // Three compact observations
    // --------------------------------------------------------

    const signalSlots = [
        ["insightsSignalOneTitle", "insightsSignalOneSample", "insightsSignalOneEvidence"],
        ["insightsSignalTwoTitle", "insightsSignalTwoSample", "insightsSignalTwoEvidence"],
        ["insightsSignalThreeTitle", "insightsSignalThreeSample", "insightsSignalThreeEvidence"],
    ];

    const dimensionLabels = {
        day: "Day",
        direction: "Direction",
        setup: "Setup",
        session: "Session",
        market_regime: "Market regime",
        structure_state: "Market structure",
        setup_session: "Setup + session",
        setup_direction: "Setup + direction",
        setup_regime: "Setup + regime",
        structure_session: "Structure + session",
        direction_session: "Direction + session",
        setup_session_regime: "Setup + session + regime",
        time: "Time",
        fingerprint_feature: "Market condition",
        fingerprint_tag: "Market condition",
    };

    signalSlots.forEach(([titleId, sampleId, evidenceId], index) => {
        const finding = recurringPatterns[index];

        if (!finding) {
            setText(titleId, "—");
            setText(sampleId, "No data");
            setText(evidenceId, "—");
            return;
        }

        const label =
            dimensionLabels[finding.dimension] ||
            finding.dimension ||
            "Condition";

        setText(
            titleId,
            finding.value || label
        );

        setText(
            sampleId,
            label
        );

        setText(
            evidenceId,
            `${patternSample(finding)} trades · ${finding.evidenceStrength?.level || "UNKNOWN"} evidence`
        );
    });

    // --------------------------------------------------------
    // Edge preview
    // --------------------------------------------------------

    const edgeTitle =
        document.getElementById("insightsEdgeTitle");

    const edgeMeta =
        document.getElementById("insightsEdgeMeta");

    if (edgeTitle) {
        if (reliableEdges.length) {
            const edge = reliableEdges[0];

            edgeTitle.textContent =
                `${edge.valueA} × ${edge.valueB} is standing out.`;
        } else {
            edgeTitle.textContent =
                "Nothing reliable yet.";
        }
    }

    if (edgeMeta) {
        edgeMeta.textContent =
            reliableEdges.length
                ? `${reliableEdges.length} reliable condition${reliableEdges.length === 1 ? "" : "s"}`
                : "0 reliable conditions";
    }

    // --------------------------------------------------------
    // Leak preview
    // --------------------------------------------------------

    const leakTitle =
        document.getElementById("insightsLeakTitle");

    const leakMeta =
        document.getElementById("insightsLeakMeta");

    const leakRows =
        Array.from(
            document.querySelectorAll(
                "#insightsIntro .insights-leak-row"
            )
        );

    const leakValues = leaks.map(leak => ({
        leak,
        count: Number(
            leak?.occurrenceCount ??
            leak?.occurrences ??
            leak?.count ??
            0
        ),
    }));

    const maxLeak =
        Math.max(
            1,
            ...leakValues.map(item => item.count)
        );

    leakRows.forEach((row, index) => {
        const item = leakValues[index];

        if (!item) {
            return;
        }

        const bar = row.querySelector(
            ".insights-leak-track span"
        );

        const number = row.querySelector("strong");

        if (bar) {
            bar.style.width =
                `${Math.min(100, (item.count / maxLeak) * 100)}%`;
        }

        if (number) {
            number.textContent = String(item.count);
        }
    });

    if (leakTitle) {
        if (repeatedLeaks.length) {
            const primaryLeak =
                [...repeatedLeaks].sort(
                    (a, b) =>
                        Number(
                            b?.occurrenceCount ??
                            b?.occurrences ??
                            b?.count ??
                            0
                        ) -
                        Number(
                            a?.occurrenceCount ??
                            a?.occurrences ??
                            a?.count ??
                            0
                        )
                )[0];

            leakTitle.textContent =
                `${primaryLeak.label || primaryLeak.type || "A behaviour"} is showing up repeatedly.`;
        } else {
            leakTitle.textContent =
                "Nothing repeated yet.";
        }
    }

    if (leakMeta) {
        leakMeta.textContent =
            repeatedLeaks.length
                ? `${repeatedLeaks.length} repeated leak${repeatedLeaks.length === 1 ? "" : "s"}`
                : "No repeated leak detected";
    }

    // --------------------------------------------------------
    // Compare preview
    // --------------------------------------------------------

    const currentCount =
        Number(current?.actualCount || 0);

    const previousCount =
        Number(previous?.actualCount || 0);

    setText(
        "insightsCurrentTrades",
        currentCount ? String(currentCount) : "—"
    );

    setText(
        "insightsPreviousTrades",
        previousCount ? String(previousCount) : "—"
    );

    const changeTitle =
        document.getElementById("insightsChangeTitle");

    const changeCopy =
        document.getElementById("insightsChangeCopy");

    if (changeTitle && changeCopy) {
        if (!previousCount) {
            changeTitle.textContent =
                "Not enough history for a meaningful comparison yet.";

            changeCopy.textContent =
                "YCT needs a previous period to compare against before it can say what has actually changed.";
        } else {
            changeTitle.textContent =
                "Your recent trading has something to compare.";

            changeCopy.textContent =
                `${currentCount} recent trades compared with ${previousCount} previous trades. Explore the evidence to see what actually changed.`;
        }
    }
}



function leakToMemoryCandidate(leak) {
    if (!leak) {
        return null;
    }

    const evidenceStrength =
        leak.evidenceStrength?.level ||
        leak.evidenceStrength;

    if (!["MODERATE", "STRONG"].includes(evidenceStrength)) {
        return null;
    }

    const sourceTradeIds = Array.isArray(leak.supportingTradeIds)
        ? leak.supportingTradeIds.filter(Boolean)
        : [];

    if (!sourceTradeIds.length) {
        return null;
    }

    const supportingTrades = trades.filter(trade =>
        sourceTradeIds.includes(trade.id) &&
        typeof trade.timestamp === "string" &&
        trade.timestamp.trim()
    );

    if (!supportingTrades.length) {
        return null;
    }

    const firstObserved = supportingTrades
        .map(trade => trade.timestamp)
        .sort()[0];

    const rImpact =
        leak.rImpact == null
            ? null
            : Number(leak.rImpact);

    const rImpactText =
        rImpact == null
            ? ""
            : ` ${rImpact.toFixed(2)}R historical impact.`;

    return {
        id: crypto.randomUUID(),
        type: "LEAK",
        statement:
            `${leak.label || leak.type} shows a repeated historical leak.` +
            rImpactText,
        sampleSize:
            Number(leak.occurrenceCount) || sourceTradeIds.length,
        evidenceStrength,
        firstObserved,
        lastVerified: null,
        status: "OBSERVED",
        contractVersion: 1,
        supportingTradeIds: sourceTradeIds,
    };
}

function edgeToMemoryCandidate(cell) {
    if (!cell) {
        return null;
    }

    const evidenceStrength = cell.evidenceStrength?.level;

    if (!["MODERATE", "STRONG"].includes(evidenceStrength)) {
        return null;
    }

    const sourceTradeIds = Array.isArray(cell.sourceTradeIds)
        ? cell.sourceTradeIds.filter(Boolean)
        : [];

    if (!sourceTradeIds.length) {
        return null;
    }

    const supportingTrades = trades.filter(trade =>
        sourceTradeIds.includes(trade.id) &&
        typeof trade.timestamp === "string" &&
        trade.timestamp.trim()
    );

    if (!supportingTrades.length) {
        return null;
    }

    const firstObserved = supportingTrades
        .map(trade => trade.timestamp)
        .sort()[0];

    const labels = {
        setup: "Setup",
        session: "Session",
        direction: "Direction",
        market_regime: "Regime",
        structure_state: "Market structure",
    };

    const dimensionA =
        labels[cell.dimensionA] || cell.dimensionA || "Condition";

    const dimensionB =
        labels[cell.dimensionB] || cell.dimensionB || "Condition";

    const performance =
        cell.expectancy != null
            ? Number(cell.expectancy)
            : cell.averageR != null
                ? Number(cell.averageR)
                : null;

    const performanceText =
        performance == null
            ? ""
            : ` ${performance.toFixed(2)}R expectancy.`;

    return {
        id: crypto.randomUUID(),
        type: "EDGE",
        statement:
            `${dimensionA} · ${cell.valueA} × ` +
            `${dimensionB} · ${cell.valueB} shows positive historical performance.` +
            performanceText,
        sampleSize: Number(cell.sampleSize) || sourceTradeIds.length,
        evidenceStrength,
        firstObserved,
        lastVerified: null,
        status: "OBSERVED",
        contractVersion: 1,
        supportingTradeIds: sourceTradeIds,
    };
}

function patternToMemoryCandidate(pattern) {
    if (!pattern || !pattern.dimension) {
        return null;
    }

    const evidenceStrength = pattern.evidenceStrength?.level;

    if (!["MODERATE", "STRONG"].includes(evidenceStrength)) {
        return null;
    }

    const typeByDimension = {
        setup: "SETUP",
        setup_session: "SETUP",
        setup_direction: "SETUP",
        setup_regime: "SETUP",
        setup_session_regime: "SETUP",

        session: "CONTEXT",
        day: "CONTEXT",
        time: "CONTEXT",
        market_regime: "CONTEXT",
        structure_state: "CONTEXT",
        structure_session: "CONTEXT",
        fingerprint_feature: "CONTEXT",
        fingerprint_tag: "CONTEXT",

        direction: "BEHAVIOR",
        direction_session: "BEHAVIOR",
    };

    const type = typeByDimension[pattern.dimension];

    if (!type || !pattern.firstObserved) {
        return null;
    }

    const sourceTradeIds = Array.isArray(pattern.sourceTradeIds)
        ? pattern.sourceTradeIds.filter(Boolean)
        : [];

    if (!sourceTradeIds.length) {
        return null;
    }

    const statement = [
        `${pattern.dimension}: ${pattern.value}`,
        pattern.conclusion || pattern.observation || "",
    ]
        .filter(Boolean)
        .join(" — ");

    return {
        id: crypto.randomUUID(),
        type,
        statement,
        sampleSize: Number(pattern.sampleSize) || sourceTradeIds.length,
        evidenceStrength,
        firstObserved: pattern.firstObserved,
        lastVerified: null,
        status: "OBSERVED",
        contractVersion: 1,
        supportingTradeIds: sourceTradeIds,
    };
}

function renderPatternReview(analytics, patternPayload) {

    patternReviewContent.replaceChildren();

    if (!analytics) {
        patternReviewContent.innerHTML =
            '<p class="pattern-empty">Start the local service to load your verified pattern summary.</p>';
        return;
    }

    const findings = Array.isArray(patternPayload?.patterns)
        ? [...patternPayload.patterns]
        : [];

    const evidenceRank = {
        STRONG: 3,
        MODERATE: 2,
        LIMITED: 1,
        LOW: 1,
        UNKNOWN: 0
    };

    const rankedFindings = findings.sort((left, right) => {
        const evidenceDifference =
            (evidenceRank[right.evidenceStrength?.level] || 0) -
            (evidenceRank[left.evidenceStrength?.level] || 0);

        if (evidenceDifference !== 0) {
            return evidenceDifference;
        }

        const sampleDifference =
            (right.sampleSize || 0) - (left.sampleSize || 0);

        if (sampleDifference !== 0) {
            return sampleDifference;
        }

        const coverageDifference =
            (right.evidenceStrength?.actualRCoverage || 0) -
            (left.evidenceStrength?.actualRCoverage || 0);

        if (coverageDifference !== 0) {
            return coverageDifference;
        }

        return new Date(right.recency?.lastObserved || 0).getTime() -
            new Date(left.recency?.lastObserved || 0).getTime();
    });

    const supportedFindings = rankedFindings.filter(finding =>
        ["STRONG", "MODERATE"].includes(finding.evidenceStrength?.level)
    );

    const recurringFindings = rankedFindings
        .filter(finding => !["STRONG", "MODERATE"].includes(finding.evidenceStrength?.level))
        .slice(0, 3);

    const intro = document.createElement("div");
    intro.className = "pattern-conclusion-intro";

    const heading = document.createElement("h3");
    const description = document.createElement("p");

    if (supportedFindings.length) {
        const primary = supportedFindings[0];

        heading.textContent = "Something is starting to stand out.";
        description.textContent =
            primary.observation ||
            primary.conclusion ||
            `${primary.dimension}: ${primary.value} is showing stronger evidence in your journal.`;
    } else {
        heading.textContent = "Nothing reliable is standing out yet.";
        description.textContent =
            findings.length
                ? "A few conditions are recurring, but the evidence is still limited. Keep capturing trades before treating them as reliable patterns."
                : "There aren't enough recurring findings yet. Keep capturing trades and YCT will surface them here.";
    }

    intro.append(heading, description);
    patternReviewContent.appendChild(intro);

    if (supportedFindings.length) {
        const primary = supportedFindings[0];

        const primaryEvidence = document.createElement("div");
        primaryEvidence.className = "pattern-conclusion-primary";

        const context = document.createElement("strong");
        context.textContent = `${primary.dimension}: ${primary.value}`;

        const evidence = document.createElement("span");
        evidence.textContent =
            `${primary.sampleSize || 0} supporting trades · Evidence: ${primary.evidenceStrength?.level || "Unknown"}`;

        primaryEvidence.append(context, evidence);
        patternReviewContent.appendChild(primaryEvidence);
    }

    if (recurringFindings.length) {
        const recurringHeading = document.createElement("h4");
        recurringHeading.className = "pattern-recurring-heading";
        recurringHeading.textContent = supportedFindings.length
            ? "Other recurring observations"
            : "Recurring observations";
        patternReviewContent.appendChild(recurringHeading);

        const recurringList = document.createElement("div");
        recurringList.className = "pattern-conclusion-list";

        recurringFindings.forEach(finding => {
            const item = document.createElement("article");
            item.className = "pattern-conclusion-item";

            const dimensionLabels = {
                day: "Day",
                direction: "Direction",
                setup: "Setup",
                session: "Session",
                market_regime: "Market regime",
                structure_state: "Market structure",
                setup_session: "Setup + session",
                setup_direction: "Setup + direction",
                setup_regime: "Setup + regime",
                structure_session: "Structure + session",
                direction_session: "Direction + session",
                setup_session_regime: "Setup + session + regime",
                time: "Time",
                fingerprint_feature: "Market condition",
                fingerprint_tag: "Market condition"
            };

            const context = document.createElement("div");
            context.className = "pattern-conclusion-context";
            context.textContent =
                `${dimensionLabels[finding.dimension] || finding.dimension || "Condition"} · ${finding.value}`;

            const evidence = document.createElement("div");
            evidence.className = "pattern-conclusion-evidence";

            const sample = document.createElement("span");
            sample.textContent = `${finding.sampleSize || 0} trades`;

            const level = document.createElement("span");
            level.textContent =
                `${finding.evidenceStrength?.level || "Unknown"} evidence`;

            evidence.append(sample, level);

            const action = document.createElement("button");
            action.type = "button";
            action.className = "pattern-conclusion-link";
            action.textContent = "See supporting trades →";
            action.disabled = !finding.sourceTradeIds?.length;

            action.addEventListener("click", () => {
                const tradeId = finding.sourceTradeIds?.[0];
                if (tradeId) {
                    openTrade(tradeId);
                }
            });

            item.append(context, evidence, action);
            recurringList.appendChild(item);
        });

        patternReviewContent.appendChild(recurringList);
    }

    const footer = document.createElement("p");
    footer.className = "pattern-conclusion-footer";
    footer.textContent =
        `${analytics.totalTrades || 0} captured · ${analytics.reviewedTrades || 0} reviewed · ${findings.length} recurring findings found`;

    patternReviewContent.appendChild(footer);

    if (analytics.sampleWarning) {
        const warning = document.createElement("p");
        warning.className = "pattern-warning";
        warning.textContent = analytics.sampleWarning;
        patternReviewContent.appendChild(warning);
    }

    patternReviewStatus.textContent =
        `${analytics.totalTrades || 0} captured · ${analytics.reviewedTrades || 0} reviewed`;
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

        const memoryCandidate = patternToMemoryCandidate(finding);

        if (memoryCandidate) {
            const rememberButton = document.createElement("button");
            rememberButton.type = "button";
            rememberButton.className = "pattern-remember";
            rememberButton.textContent = "Remember this";

            rememberButton.addEventListener("click", async () => {
                if (rememberButton.disabled) {
                    return;
                }

                const confirmed = window.confirm(
                    "Remember this finding in Trading Memory?"
                );

                if (!confirmed) {
                    return;
                }

                rememberButton.disabled = true;
                rememberButton.textContent = "Saving…";

                try {
                    await createLocalMemory(memoryCandidate);
                    rememberButton.textContent = "Remembered";
                    rememberButton.classList.add("is-remembered");
                } catch (error) {
                    console.error("Failed to save Memory finding:", error);
                    rememberButton.disabled = false;
                    rememberButton.textContent = "Remember this";
                    alert("Could not save this finding to Trading Memory.");
                }
            });

            card.appendChild(rememberButton);
        }

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

        insightsPatternPayload = patterns;
        insightsTradeCount = Number(analytics?.totalTrades || 0);

        renderPatternReview(analytics, patterns);
        renderPatternDiscovery(patterns);
        renderInsightsHybrid();
        renderEvidenceOverview();
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
            if (item.sampleComplete) {
                const completionNote = document.createElement("p");
                completionNote.className = "experiment-completion-note";
                completionNote.textContent =
                    "Observation window complete. Review behaviour separately from R/performance.";
                card.appendChild(completionNote);

                const complete = document.createElement("button");
                complete.className = "clear-filters experiment-complete";
                complete.type = "button";
                complete.textContent = "Complete experiment";
                complete.addEventListener("click", async () => {
                    const confirmed = window.confirm(
                        "Complete this experiment? The observation history will remain recorded."
                    );
                    if (!confirmed) {
                        return;
                    }
                    await updateLocalExperimentStatus(item.id, "COMPLETED");
                    await loadExperiments();
                });
                card.appendChild(complete);
            }

            const abandon = document.createElement("button");
            abandon.className = "clear-filters experiment-abandon";
            abandon.type = "button";
            abandon.textContent = "Abandon experiment";
            abandon.addEventListener("click", async () => {
                const confirmed = window.confirm(
                    "Abandon this experiment? Its history will remain recorded."
                );
                if (!confirmed) {
                    return;
                }
                await updateLocalExperimentStatus(item.id, "ABANDONED");
                await loadExperiments();
            });
            card.appendChild(abandon);
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
    card.setAttribute(
        "role",
        "button"
    );
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

    const date = document.createElement("div");
    date.className = "card-date";
    date.textContent = formatDate(trade.chartAnchorTime || trade.timestamp);

    const topline = document.createElement("div");
    topline.className = "card-topline";

    const title = document.createElement("h3");
    title.className = "card-title";
    title.textContent = trade.symbol || "Untitled trade";

    const result = document.createElement("span");
    result.className = getResultClass(trade.result);
    result.textContent = getResultLabel(trade.result).toUpperCase();

    topline.append(title, result);

    const meta = document.createElement("p");
    meta.className = "card-meta";
    meta.textContent = [
        trade.timeframe || "No timeframe",
        trade.direction || "No direction",
        trade.setup || null
    ].filter(Boolean).join(" · ");

    const footer = document.createElement("div");
    footer.className = "card-footer";

    const plannedR = document.createElement("span");
    plannedR.textContent = `Plan ${formatR(calculatePlannedR(trade))}`;

    const actualR = document.createElement("span");
    actualR.textContent = `Actual ${formatR(calculateActualR(trade))}`;

    footer.append(plannedR, actualR);
    content.append(date, topline, meta, footer);
    card.appendChild(content);

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "card-delete-button";
    deleteButton.textContent = "Delete";
    deleteButton.setAttribute(
        "aria-label",
        `Delete ${trade.symbol || "trade"}`
    );

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



function createHomeBlock(className, label, title, copy) {
    const block = document.createElement("article");
    block.className = `home-understanding-block ${className || ""}`.trim();

    if (label) {
        const eyebrow = document.createElement("p");
        eyebrow.className = "eyebrow";
        eyebrow.textContent = label;
        block.appendChild(eyebrow);
    }

    if (title) {
        const heading = document.createElement("h3");
        heading.textContent = title;
        block.appendChild(heading);
    }

    if (copy) {
        const paragraph = document.createElement("p");
        paragraph.textContent = copy;
        block.appendChild(paragraph);
    }

    return block;
}


function renderHomeUnderstanding(payload, tradeCount) {
    const container = document.getElementById("homeUnderstandingContent");
    const meta = document.getElementById("homeEvidenceMeta");

    if (!container || !meta) {
        return;
    }

    container.replaceChildren();

    const count = Number(payload?.tradeCount ?? tradeCount ?? 0);
    const status = payload?.status || (count ? "LEARNING" : "NO_TRADES");

    if (status === "NO_TRADES" || !count) {
        container.appendChild(
            createHomeBlock(
                "home-primary",
                null,
                "I haven't seen a trade yet.",
                "Capture your first trade from TradingView and I'll start building a picture of how you trade."
            )
        );

        meta.textContent = "No trades captured yet";
        return;
    }

    if (!payload) {
        container.appendChild(
            createHomeBlock(
                "home-primary",
                null,
                "I'm still building your trading picture.",
                "Your trades are safe. I'll show the current understanding as soon as the local intelligence service is available."
            )
        );

        meta.textContent = `${count} ${count === 1 ? "trade" : "trades"} captured`;
        return;
    }

    if (status === "LEARNING") {
        container.appendChild(
            createHomeBlock(
                "home-primary",
                null,
                "I'm still learning your trading.",
                `You've captured ${count} ${count === 1 ? "trade" : "trades"}. I don't have enough repeated evidence yet to tell you what consistently matters.`
            )
        );

        container.appendChild(
            createHomeBlock(
                "home-secondary",
                "WHAT HAPPENS NEXT",
                "Keep capturing your decisions.",
                "As the evidence builds, I'll start showing you the patterns that are actually supported by your trades."
            )
        );

        meta.textContent = `${count} ${count === 1 ? "trade" : "trades"} captured`;
        return;
    }

    const observation = payload.observation;
    const watch = payload.watch;
    const recentChange = payload.recentChange;

    if (observation?.statement) {
        container.appendChild(
            createHomeBlock(
                "home-primary",
                null,
                observation.statement,
                null
            )
        );
    }

    if (watch) {
        container.appendChild(
            createHomeBlock(
                "home-secondary",
                "Worth keeping an eye on",
                watch.statement,
                null
            )
        );
    }

    if (recentChange?.statement) {
        container.appendChild(
            createHomeBlock(
                "home-focus",
                "Recently",
                recentChange.statement,
                null
            )
        );
    }

    const findingCount = [observation, watch, recentChange].filter(Boolean).length;
    const tradeLabel = `${count} ${count === 1 ? "trade" : "trades"}`;

    meta.textContent =
        findingCount === 1
            ? `Based on ${tradeLabel} · one supported finding`
            : `Based on ${tradeLabel} · ${findingCount} supported findings`;
}

async function loadHomeUnderstanding(tradeCount) {
    try {
        const currentTradeIds = trades
            .map(trade => trade?.id)
            .filter(Boolean);

        const payload = await getLocalCurrentUnderstanding(currentTradeIds);
        renderHomeUnderstanding(payload, tradeCount);
    } catch (error) {
        console.error("❌ HOME UNDERSTANDING FAILED", error);
        renderHomeUnderstanding(null, tradeCount);
    }
}


async function loadTrades() {

    const [storedTrades, storageUsage] = await Promise.all([
        getTrades(),
        getStorageUsage()
    ]);

    trades = storedTrades;
    populateFilters();
    renderStorageUsage(storageUsage);
    onboarding.hidden = trades.length >= 3;
    renderWeeklyReview();
    renderTradeGrid();
    await loadPatternReview();
    await loadExperiments();
    await loadStorageSettings();

    // Home understanding is secondary UI.
    // Never let analytics availability block the core dashboard.
    void loadHomeUnderstanding(trades.length);
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

// ============================================================
// YCT APPLICATION VIEWS
// ============================================================

const YCT_VIEW_CONFIG = {
    home: {
        title: "Here's what I'm seeing.",
        subtitle: "A clear picture of your trading, built from the trades you've actually taken.",
        sections: ["homeUnderstanding", "onboarding"]
    },

    trades: {
        title: "Your trades.",
        subtitle: "Every captured decision, with the chart evidence attached.",
        sections: ["library"]
    },

    insights: {
        title: "Insights.",
        subtitle: "What is your trading telling you?",
        sections: ["insightsIntro"]
    },

    "insights-evidence": {
        title: "The evidence.",
        subtitle: "What YCT is seeing, and why.",
        sections: ["evidenceOverview"]
    },

    experiments: {
        title: "Let's test it.",
        subtitle: "Turn something you've noticed into a measurable experiment.",
        sections: ["experiments"]
    },

    memory: {
        title: "Here's what I've learned.",
        subtitle: "What You Can't Trade has learned from the evidence you've accumulated.",
        sections: ["memory", "memoryDetails"]
    },

    review: {
        title: "Let's look back.",
        subtitle: "A concise reflection on what changed in your recent trading.",
        sections: ["weekly"]
    },

    settings: {
        title: "How YCT works.",
        subtitle: "Control where your journal lives and how it is stored.",
        sections: ["settings"]
    }
};

const YCT_VIEW_SURFACES = [
    "homeUnderstanding",
    "insightsIntro",
    "evidenceOverview",
    "onboarding",
    "settings",
    "metrics",
    "weekly",
    "experiments",
    "patterns",
    "edgeMap",
    "leakMap",
    "leakDetails",
    "compare",
    "memory",
    "memoryDetails",
    "library"
];

function getEvidenceSectionFromHash() {
    const hash = window.location.hash.replace(/^#/, "");

    const targets = {
        "insights-evidence-patterns": "patterns",
        "insights-evidence-edges": "edges",
        "insights-evidence-leaks": "leaks",
        "insights-evidence-compare": "compare"
    };

    return targets[hash] || null;
}


function getYctViewFromHash() {
    const hash = window.location.hash.replace(/^#/, "");

    if (hash.startsWith("insights-evidence-")) {
        return "insights-evidence";
    }

    return YCT_VIEW_CONFIG[hash] ? hash : "home";
}


function scrollToEvidenceSection(section) {
    const targets = {
        patterns: "evidencePatternList",
        edges: "evidenceEdgeGrid",
        leaks: "evidenceLeakList",
        compare: "evidenceChangeCopy"
    };

    const targetId = targets[section];

    if (!targetId) {
        return;
    }

    const target = document.getElementById(targetId);

    if (!target) {
        return;
    }

    window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => {
            target.scrollIntoView({
                behavior: "auto",
                block: "start",
                inline: "nearest"
            });
        });
    });
}

function setYctView(
    view,
    {
        updateHash = true,
        evidenceSection = null
    } = {}
) {
    const config = YCT_VIEW_CONFIG[view] || YCT_VIEW_CONFIG.home;
    const activeView = YCT_VIEW_CONFIG[view] ? view : "home";

    YCT_VIEW_SURFACES.forEach(id => {
        const section = document.getElementById(id);

        if (!section) {
            return;
        }

        section.classList.toggle(
            "yct-view-hidden",
            !config.sections.includes(id)
        );
    });

    document.querySelectorAll("[data-yct-view]").forEach(link => {
        link.classList.toggle(
            "active",
            link.dataset.yctView === activeView
        );
    });

    const title = document.getElementById("pageTitle");
    const subtitle = document.getElementById("pageSubtitle");

    if (title) {
        title.textContent = config.title;
    }

    if (subtitle) {
        subtitle.textContent = config.subtitle;
    }

    document.body.dataset.yctView = activeView;

    const hashSection =
        activeView === "insights-evidence"
            ? getEvidenceSectionFromHash()
            : null;

    const targetSection = evidenceSection || hashSection;

    if (updateHash) {
        let targetHash = `#${activeView}`;

        if (activeView === "insights-evidence" && targetSection) {
            targetHash = `#insights-evidence-${targetSection}`;
        }

        if (window.location.hash !== targetHash) {
            history.pushState(
                {
                    yctView: activeView,
                    evidenceSection: targetSection
                },
                "",
                targetHash
            );
        }
    }

    if (activeView === "insights-evidence" && targetSection) {
        scrollToEvidenceSection(targetSection);
    } else {
        window.scrollTo({
            top: 0,
            behavior: "auto"
        });
    }
}


function bindYctViews() {
    document.querySelectorAll("[data-yct-view]").forEach(link => {
        link.addEventListener("click", event => {
            event.preventDefault();

            setYctView(
                link.dataset.yctView,
                {
                    evidenceSection: link.dataset.evidenceSection || null
                }
            );
        });
    });

    window.addEventListener("hashchange", () => {
        setYctView(
            getYctViewFromHash(),
            { updateHash: false }
        );
    });

    window.addEventListener("popstate", () => {
        setYctView(
            getYctViewFromHash(),
            { updateHash: false }
        );
    });

    setYctView(
        getYctViewFromHash(),
        { updateHash: false }
    );
}


bindYctViews();
bindEdgeMapControls();
loadEdgeMap();

bindCompareControls();

loadTrades()
    .then(() => {
        const tradeId = new URLSearchParams(window.location.search).get("tradeId");

        if (tradeId) {
            openTrade(tradeId);
        }

        return loadCompare();
    })
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
