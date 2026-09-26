import { captureTrade } from "./services/tradeService.js";

console.log(
    "🚀 You Can't Trade background loaded"
);

let captureInProgress = false;

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === "OPEN_DASHBOARD") {
        const dashboardUrl = new URL(
            chrome.runtime.getURL("dashboard/dashboard.html")
        );

        if (request.tradeId) {
            dashboardUrl.searchParams.set("tradeId", request.tradeId);
        }

        chrome.tabs.create({
            url: dashboardUrl.toString()
        });

        sendResponse({ ok: true });
        return;
    }

    if (request.type !== "CAPTURE_TRADE") {
        return;
    }

    if (captureInProgress) {
        sendResponse({
            ok: false,
            error: "A trade capture is already in progress."
        });
        return;
    }

    captureInProgress = true;

    captureTrade()
        .then(trade => {
            sendResponse({
                ok: true,
                tradeId: trade.id
            });
        })
        .catch(error => {
            console.error("❌ TRADINGVIEW CAPTURE FAILED", error);

            sendResponse({
                ok: false,
                error: error?.message || "Trade capture failed."
            });
        })
        .finally(() => {
            captureInProgress = false;
        });

    return true;
});
