// Two ways to capture the Bearer token:
// 1. Content script reads it from localStorage and sends it via message.
// 2. webRequest intercepts live API calls (catches token refreshes).

function setReady() {
  chrome.action.setBadgeText({ text: "✓" });
  chrome.action.setBadgeBackgroundColor({ color: "#2a9d2a" });
}

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "token" && msg.token) {
    chrome.storage.session.set({ at_token: msg.token });
    setReady();
  }
});

chrome.webRequest.onBeforeSendHeaders.addListener(
  (details) => {
    const auth = details.requestHeaders?.find(
      (h) => h.name.toLowerCase() === "authorization"
    );
    if (auth?.value?.startsWith("Bearer ")) {
      chrome.storage.session.set({ at_token: auth.value });
      setReady();
    }
  },
  { urls: ["https://api.academictransfer.com/*"] },
  ["requestHeaders", "extraHeaders"]
);