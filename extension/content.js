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

    button.addEventListener("click", () => {
        console.log("YCT button clicked");
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
