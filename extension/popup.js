import { captureTrade } from "./services/tradeService.js";

const captureButton = document.getElementById("captureBtn");
const captureStatus = document.getElementById("captureStatus");
const dashboardButton = document.getElementById("openDashboard");

function setCaptureStatus(message, state = "") {
    captureStatus.textContent = message;
    captureStatus.className = `capture-status ${state}`;
}

dashboardButton.addEventListener("click", () => {
    chrome.tabs.create({
        url: chrome.runtime.getURL("dashboard/dashboard.html")
    });
});

captureButton.addEventListener("click", async () => {
    captureButton.disabled = true;
    captureButton.textContent = "Capturing…";
    setCaptureStatus("Reading the visible TradingView chart…");

    try {
        const trade = await captureTrade();

        console.log("✅ TRADE CAPTURED:", trade);

        setCaptureStatus(
            "Trade captured successfully.",
            "success"
        );

    } catch (error) {
        console.error("❌ TRADE CAPTURE FAILED", error);

        setCaptureStatus(
            error?.message ||
            "Could not capture this trade. Open a TradingView chart and try again.",
            "error"
        );

    } finally {
        captureButton.disabled = false;
        captureButton.textContent = "Capture Trade";
    }
});
