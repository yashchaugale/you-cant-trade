let pendingRRResponse = null;

console.log("✅ You Can't Trade content script loaded");

const YCT_CAPTURE_BUTTON_ID = "yct-tradingview-button";

const YCT_TOOLBAR_ANCHORS = [
    "Quick search",
    "Settings",
    "Fullscreen mode",
    "Take a snapshot"
];

function findTradingViewToolbarAnchor() {
    for (const label of YCT_TOOLBAR_ANCHORS) {
        const anchors = [...document.querySelectorAll('button,[role="button"]')]
            .filter(element =>
                element.getAttribute("aria-label") === label
            );

        if (!anchors.length) {
            continue;
        }

        return anchors.reduce((rightmost, element) => {
            const elementX = element.getBoundingClientRect().left;
            const rightmostX = rightmost.getBoundingClientRect().left;

            return elementX > rightmostX ? element : rightmost;
        });
    }

    return null;
}


function createYCTPanel(button) {
    const existing = document.getElementById("yct-capture-panel");

    if (existing) {
        existing.remove();
        return;
    }

    const panel = document.createElement("div");

    panel.id = "yct-capture-panel";

    Object.assign(panel.style, {
        position: "fixed",
        width: "286px",
        padding: "14px",
        background: "#111111",
        color: "#F5F1E8",
        border: "1px solid rgba(245, 241, 232, 0.14)",
        borderRadius: "12px",
        boxShadow: "0 12px 36px rgba(0, 0, 0, 0.35)",
        zIndex: "2147483647",
        boxSizing: "border-box",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        fontSize: "13px",
        lineHeight: "1.4"
    });

    const pageInfo = getPageInfo();

    const symbol = pageInfo.symbol || "Unknown symbol";
    const timeframe = pageInfo.timeframe || "Unknown timeframe";

    panel.innerHTML = `
        <div style="
            display:flex;
            align-items:center;
            justify-content:space-between;
            margin-bottom:10px;
        ">
            <div style="
                font-size:10px;
                font-weight:700;
                letter-spacing:0.12em;
                text-transform:uppercase;
                color:#FF5A1F;
            ">
                You Can't Trade
            </div>

            <button
                type="button"
                data-yct-close
                aria-label="Close"
                style="
                    width:22px;
                    height:22px;
                    padding:0;
                    border:0;
                    background:transparent;
                    color:#8F8B84;
                    font-size:18px;
                    line-height:20px;
                    cursor:pointer;
                "
            >
                ×
            </button>
        </div>

        <div style="
            font-size:17px;
            font-weight:650;
            letter-spacing:-0.02em;
            margin-bottom:2px;
        ">
            Capture a trade
        </div>

        <div style="
            color:#77736D;
            font-size:11px;
            margin-bottom:12px;
        ">
            ${symbol.replace(/</g, "&lt;")} · ${timeframe.replace(/</g, "&lt;")}
        </div>

        <div style="
            display:grid;
            grid-template-columns:1fr 1fr 1fr;
            gap:6px;
            margin-bottom:8px;
        ">
            <label style="display:block;">
                <span style="
                    display:block;
                    color:#77736D;
                    font-size:9px;
                    font-weight:700;
                    letter-spacing:0.08em;
                    text-transform:uppercase;
                    margin-bottom:4px;
                ">
                    Entry
                </span>

                <input
                    data-yct-field="entry"
                    type="number"
                    step="any"
                    placeholder="—"
                    style="
                        width:100%;
                        height:34px;
                        padding:0 8px;
                        box-sizing:border-box;
                        border:1px solid rgba(245,241,232,0.12);
                        border-radius:7px;
                        background:#191919;
                        color:#F5F1E8;
                        outline:none;
                        font:600 12px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                    "
                />
            </label>

            <label style="display:block;">
                <span style="
                    display:block;
                    color:#77736D;
                    font-size:9px;
                    font-weight:700;
                    letter-spacing:0.08em;
                    text-transform:uppercase;
                    margin-bottom:4px;
                ">
                    Stop
                </span>

                <input
                    data-yct-field="stop"
                    type="number"
                    step="any"
                    placeholder="—"
                    style="
                        width:100%;
                        height:34px;
                        padding:0 8px;
                        box-sizing:border-box;
                        border:1px solid rgba(245,241,232,0.12);
                        border-radius:7px;
                        background:#191919;
                        color:#F5F1E8;
                        outline:none;
                        font:600 12px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                    "
                />
            </label>

            <label style="display:block;">
                <span style="
                    display:block;
                    color:#77736D;
                    font-size:9px;
                    font-weight:700;
                    letter-spacing:0.08em;
                    text-transform:uppercase;
                    margin-bottom:4px;
                ">
                    Target
                </span>

                <input
                    data-yct-field="target"
                    type="number"
                    step="any"
                    placeholder="—"
                    style="
                        width:100%;
                        height:34px;
                        padding:0 8px;
                        box-sizing:border-box;
                        border:1px solid rgba(245,241,232,0.12);
                        border-radius:7px;
                        background:#191919;
                        color:#F5F1E8;
                        outline:none;
                        font:600 12px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                    "
                />
            </label>
        </div>

        <div style="
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:8px;
            margin-bottom:10px;
        ">
            <div style="
                display:flex;
                align-items:center;
                gap:3px;
                padding:3px;
                border-radius:7px;
                background:#191919;
                border:1px solid rgba(245,241,232,0.08);
            ">
                <button
                    type="button"
                    data-yct-direction="long"
                    style="
                        height:25px;
                        padding:0 9px;
                        border:0;
                        border-radius:5px;
                        background:#FF5A1F;
                        color:#111111;
                        font:700 10px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                        cursor:pointer;
                    "
                >
                    Long
                </button>

                <button
                    type="button"
                    data-yct-direction="short"
                    style="
                        height:25px;
                        padding:0 9px;
                        border:0;
                        border-radius:5px;
                        background:transparent;
                        color:#77736D;
                        font:700 10px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                        cursor:pointer;
                    "
                >
                    Short
                </button>
            </div>

            <div style="
                display:flex;
                align-items:center;
                gap:5px;
                color:#77736D;
                font-size:10px;
            ">
                <span>R:R</span>
                <strong
                    data-yct-rr
                    style="
                        color:#F5F1E8;
                        font-size:11px;
                        font-weight:650;
                    "
                >
                    —
                </strong>
            </div>
        </div>

        <button
            type="button"
            data-yct-capture
            style="
                width:100%;
                height:36px;
                border:0;
                border-radius:7px;
                background:#FF5A1F;
                color:#111111;
                font:700 11px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                letter-spacing:0.02em;
                cursor:pointer;
            "
        >
            Capture Trade
        </button>

        <button
            type="button"
            data-yct-dashboard
            style="
                width:100%;
                height:32px;
                margin-top:8px;
                border:1px solid rgba(245,241,232,0.16);
                border-radius:7px;
                background:transparent;
                color:#F5F1E8;
                font:700 10px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                letter-spacing:0.02em;
                cursor:pointer;
            "
        >
            Open Dashboard →
        </button>
    `;

    document.body.appendChild(panel);

    const buttonRect = button.getBoundingClientRect();

    const panelWidth = 286;
    const gap = 8;

    let left = buttonRect.left - panelWidth - gap;
    let top = buttonRect.top;

    if (left < 8) {
        left = 8;
    }

    if (top + panel.offsetHeight > window.innerHeight - 8) {
        top = window.innerHeight - panel.offsetHeight - 8;
    }

    if (top < 8) {
        top = 8;
    }

    panel.style.left = `${left}px`;
    panel.style.top = `${top}px`;

    function requestCurrentRR() {
        return new Promise(resolve => {
            let settled = false;

            const finish = value => {
                if (settled) return;
                settled = true;
                window.removeEventListener("message", handler);
                resolve(value || null);
            };

            const handler = event => {
                if (
                    event.source !== window ||
                    event.origin !== window.location.origin ||
                    event.data?.type !== "VANTAGE_CURRENT_RR_RESPONSE"
                ) {
                    return;
                }

                finish(event.data.rr || null);
            };

            window.addEventListener("message", handler);

            window.postMessage(
                { type: "VANTAGE_GET_CURRENT_RR" },
                window.location.origin
            );

            setTimeout(() => finish(null), 1200);
        });
    }

    const entryInput = panel.querySelector('[data-yct-field="entry"]');
    const stopInput = panel.querySelector('[data-yct-field="stop"]');
    const targetInput = panel.querySelector('[data-yct-field="target"]');
    const rrDisplay = panel.querySelector("[data-yct-rr]");
    const longButton = panel.querySelector('[data-yct-direction="long"]');
    const shortButton = panel.querySelector('[data-yct-direction="short"]');

    let direction = null;

    function updateRR() {
        const entry = Number(entryInput.value);
        const stop = Number(stopInput.value);
        const target = Number(targetInput.value);

        if (
            !Number.isFinite(entry) ||
            !Number.isFinite(stop) ||
            !Number.isFinite(target)
        ) {
            rrDisplay.textContent = "—";
            return;
        }

        const risk = direction === "long"
            ? entry - stop
            : stop - entry;

        const reward = direction === "long"
            ? target - entry
            : entry - target;

        if (risk <= 0 || reward <= 0) {
            rrDisplay.textContent = "—";
            return;
        }

        rrDisplay.textContent = `1 : ${(reward / risk).toFixed(2)}`;
    }

    function setDirection(nextDirection) {
        direction = nextDirection;

        const active = {
            background: "#FF5A1F",
            color: "#111111"
        };

        const inactive = {
            background: "transparent",
            color: "#77736D"
        };

        Object.assign(
            longButton.style,
            direction === "long" ? active : inactive
        );

        Object.assign(
            shortButton.style,
            direction === "short" ? active : inactive
        );

        updateRR();
    }

    [entryInput, stopInput, targetInput].forEach(input => {
        input.addEventListener("input", updateRR);

        input.addEventListener("focus", () => {
            input.style.borderColor = "#FF5A1F";
        });

        input.addEventListener("blur", () => {
            input.style.borderColor = "rgba(245,241,232,0.12)";
        });
    });

    longButton.addEventListener("click", () => {
        setDirection("long");
    });

    shortButton.addEventListener("click", () => {
        setDirection("short");
    });

    requestCurrentRR().then(rr => {
        if (!rr) {
            return;
        }

        entryInput.value = Number.isFinite(Number(rr.entry))
            ? rr.entry
            : "";

        stopInput.value = Number.isFinite(Number(rr.stopLoss))
            ? rr.stopLoss
            : "";

        targetInput.value = Number.isFinite(Number(rr.takeProfit))
            ? rr.takeProfit
            : "";

        if (rr.direction === "LONG") {
            setDirection("long");
        } else if (rr.direction === "SHORT") {
            setDirection("short");
        }

        updateRR();
    });

    const dashboardButton = panel.querySelector("[data-yct-dashboard]");

    dashboardButton.addEventListener("click", event => {
        event.stopPropagation();

        chrome.runtime.sendMessage({
            type: "OPEN_DASHBOARD"
        });
    });

    const captureButton = panel.querySelector("[data-yct-capture]");

    captureButton.addEventListener("click", event => {
        event.stopPropagation();

        captureButton.disabled = true;
        captureButton.textContent = "Capturing…";
        captureButton.style.opacity = "0.7";
        captureButton.style.cursor = "wait";

        setTimeout(() => {
            panel.style.visibility = "hidden";

            requestAnimationFrame(() => {
                chrome.runtime.sendMessage(
                    {
                        type: "CAPTURE_TRADE"
                    },
                response => {
                    panel.style.visibility = "visible";

                    if (chrome.runtime.lastError) {
                        captureButton.disabled = false;
                        captureButton.textContent = "Capture Trade";
                        captureButton.style.opacity = "1";
                        captureButton.style.cursor = "pointer";

                        console.error(
                            "❌ YCT CAPTURE MESSAGE FAILED",
                            chrome.runtime.lastError
                        );

                        return;
                    }

                    if (!response?.ok) {
                        captureButton.disabled = false;
                        captureButton.textContent = "Try Again";
                        captureButton.style.opacity = "1";
                        captureButton.style.cursor = "pointer";

                        const errorText =
                            response?.error || "Trade capture failed.";

                        console.error(
                            "❌ YCT TRADE CAPTURE FAILED",
                            errorText
                        );

                        const errorMessage = document.createElement("div");

                        errorMessage.style.cssText = `
                            margin-top: 8px;
                            color: #FF8A66;
                            font-size: 10px;
                            line-height: 1.4;
                        `;

                        errorMessage.textContent = errorText;

                        panel.appendChild(errorMessage);

                        return;
                    }

                    panel.innerHTML = `
                        <div style="
                            display:flex;
                            align-items:center;
                            justify-content:space-between;
                            margin-bottom:14px;
                        ">
                            <div style="
                                font-size:10px;
                                font-weight:700;
                                letter-spacing:0.12em;
                                text-transform:uppercase;
                                color:#FF5A1F;
                            ">
                                You Can't Trade
                            </div>

                            <button
                                type="button"
                                data-yct-close
                                aria-label="Close"
                                style="
                                    width:22px;
                                    height:22px;
                                    padding:0;
                                    border:0;
                                    background:transparent;
                                    color:#8F8B84;
                                    font-size:18px;
                                    line-height:20px;
                                    cursor:pointer;
                                "
                            >
                                ×
                            </button>
                        </div>

                        <div style="
                            display:flex;
                            align-items:center;
                            gap:10px;
                            margin-bottom:8px;
                        ">
                            <div style="
                                width:28px;
                                height:28px;
                                border-radius:50%;
                                display:flex;
                                align-items:center;
                                justify-content:center;
                                background:#FF5A1F;
                                color:#111111;
                                font-size:16px;
                                font-weight:800;
                            ">
                                ✓
                            </div>

                            <div style="
                                font-size:17px;
                                font-weight:650;
                                letter-spacing:-0.02em;
                            ">
                                Trade captured
                            </div>
                        </div>

                        <div style="
                            color:#77736D;
                            font-size:11px;
                            margin-bottom:14px;
                        ">
                            Saved with your chart evidence and deterministic analysis.
                        </div>

                        <div style="
                            padding:9px 10px;
                            border-radius:7px;
                            background:#191919;
                            border:1px solid rgba(245,241,232,0.08);
                            color:#9F9A91;
                            font-size:10px;
                        ">
                            Trade ID: ${String(response.tradeId || "").slice(0, 8)}
                        </div>
                    `;

                    panel
                        .querySelector("[data-yct-close]")
                        ?.addEventListener("click", event => {
                            event.stopPropagation();
                            panel.remove();
                        });

                    setTimeout(() => {
                        if (document.body.contains(panel)) {
                            panel.remove();
                        }
                    }, 1400);
                    }
                );
            });
        }, 450);
    });

    const closeButton = panel.querySelector("[data-yct-close]");

    closeButton.addEventListener("click", event => {
        event.stopPropagation();
        panel.remove();
    });

    const outsideClickHandler = event => {
        if (
            event.target !== button &&
            !button.contains(event.target) &&
            !panel.contains(event.target)
        ) {
            panel.remove();
            document.removeEventListener("mousedown", outsideClickHandler, true);
            document.removeEventListener("keydown", escapeHandler, true);
        }
    };

    const escapeHandler = event => {
        if (event.key === "Escape") {
            panel.remove();
            document.removeEventListener("mousedown", outsideClickHandler, true);
            document.removeEventListener("keydown", escapeHandler, true);
        }
    };

    setTimeout(() => {
        document.addEventListener("mousedown", outsideClickHandler, true);
        document.addEventListener("keydown", escapeHandler, true);
    }, 0);
}


function createYCTButton() {
    if (document.getElementById(YCT_CAPTURE_BUTTON_ID)) {
        return true;
    }

    const anchor = findTradingViewToolbarAnchor();

    if (!anchor) {
        return false;
    }

    const button = document.createElement("button");

    button.id = YCT_CAPTURE_BUTTON_ID;
    button.type = "button";
    button.setAttribute("aria-label", "You Can't Trade");
    button.setAttribute("title", "You Can't Trade");

    button.innerHTML = `
        <img
            src="${chrome.runtime.getURL("assets/yct-logo.svg")}"
            alt=""
            draggable="false"
        />
    `;

    Object.assign(button.style, {
        width: "32px",
        height: "32px",
        margin: "0 4px",
        padding: "0",
        border: "2px solid #FF5A1F",
        borderRadius: "50%",
        background: "#F5F1E8",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
        boxSizing: "border-box",
        flex: "0 0 auto",
        transition: "background 140ms ease, transform 140ms ease"
    });

    const logo = button.querySelector("img");

    Object.assign(logo.style, {
        width: "25px",
        height: "25px",
        display: "block",
        objectFit: "contain",
        pointerEvents: "none",
        userSelect: "none"
    });

    button.addEventListener("mouseenter", () => {
        button.style.background = "#FF5A1F";
        button.style.borderColor = "#FF5A1F";
        button.style.boxShadow = "0 0 0 3px rgba(255, 90, 31, 0.18)";
        button.style.transform = "scale(1.06)";
    });

    button.addEventListener("mouseleave", () => {
        button.style.background = "#F5F1E8";
        button.style.borderColor = "#FF5A1F";
        button.style.boxShadow = "none";
        button.style.transform = "none";
    });

    button.addEventListener("click", event => {
        event.stopPropagation();
        createYCTPanel(button);
    });

    anchor.insertAdjacentElement("beforebegin", button);

    return true;
}

function ensureYCTToolbarButton() {
    if (createYCTButton()) {
        return;
    }

    if (window.__yctToolbarObserver) {
        return;
    }

    const observer = new MutationObserver(() => {
        if (createYCTButton()) {
            observer.disconnect();
            window.__yctToolbarObserver = null;
        }
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    window.__yctToolbarObserver = observer;
}

if (document.body) {
    ensureYCTToolbarButton();
} else {
    document.addEventListener("DOMContentLoaded", ensureYCTToolbarButton, {
        once: true
    });
}

function getPageInfo() {

    const symbol =
        document
            .querySelector("#header-toolbar-symbol-search")
            ?.textContent
            .trim() || "";

    const activeTimeframe =
        document.querySelector(
            '#header-toolbar-intervals [role="radio"][aria-checked="true"]'
        );

    const timeframe =
        activeTimeframe
            ?.querySelector(".value-EzLGe8ai")
            ?.textContent
            .trim() || "";

    const exchange =
        document
            .querySelector(
                '[data-qa-id="title-wrapper legend-source-exchange"]'
            )
            ?.textContent
            .trim() || "";

    return {
        symbol,
        timeframe,
        exchange,
        title: document.title
    };
}


chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {

    if (request.type === "GET_PAGE_INFO") {

        sendResponse(getPageInfo());

        return;
    }

    if (request.type === "GET_CURRENT_PRICE") {
        const handler = event => {
            if (event.data?.type !== "VANTAGE_CURRENT_PRICE_RESPONSE") return;
            window.removeEventListener("message", handler);
            sendResponse({ price: Number.isFinite(event.data.price) ? event.data.price : null });
        };
        window.addEventListener("message", handler);
        window.postMessage({ type: "VANTAGE_GET_CURRENT_PRICE" }, window.location.origin);
        return true;
    }

    if (request.type === "GET_CURRENT_RR") {

        if (pendingRRResponse) {

            sendResponse({
                rr: null,
                error: "A Risk/Reward request is already in progress."
            });

            return;
        }

        pendingRRResponse = sendResponse;

        window.postMessage(
            { type: "VANTAGE_GET_CURRENT_RR" },
            window.location.origin
        );

        return true;
    }
});


window.addEventListener("message", event => {

    if (
        event.source !== window ||
        event.origin !== window.location.origin ||
        event.data?.type !== "VANTAGE_CURRENT_RR_RESPONSE"
    ) {
        return;
    }

    if (!pendingRRResponse) {
        return;
    }

    pendingRRResponse({
    rr: event.data.rr || null,
    marketData: event.data.marketData || null
});

pendingRRResponse = null;
});
