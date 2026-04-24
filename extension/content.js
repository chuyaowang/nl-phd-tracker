// Runs in the context of every AcademicTransfer page.
// Scans localStorage and sessionStorage for a JWT Bearer token and sends it
// to the background script, which stores it for the popup to use.

function findToken() {
  for (const storage of [localStorage, sessionStorage]) {
    for (let i = 0; i < storage.length; i++) {
      const val = storage.getItem(storage.key(i)) || "";
      // Match a raw JWT (three base64url segments) or "Bearer <jwt>"
      const match = val.match(/(?:Bearer\s+)?(eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)/);
      if (match) {
        return `Bearer ${match[1]}`;
      }
    }
  }
  return null;
}

const token = findToken();
if (token) {
  chrome.runtime.sendMessage({ type: "token", token });
}