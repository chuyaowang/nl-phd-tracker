const btn = document.getElementById("syncBtn");
const statusEl = document.getElementById("status");
const lastEl = document.getElementById("last");

const SERVER = "http://localhost:8765";

async function loadStatus() {
  try {
    const r = await fetch(`${SERVER}/status`);
    const data = await r.json();
    if (data.timestamp) {
      lastEl.textContent = `Last sync: ${data.timestamp} — ${data.total} jobs (${data.added} new)`;
    }
  } catch {
    lastEl.textContent = "Local server not running.";
  }
}

btn.addEventListener("click", async () => {
  btn.disabled = true;
  statusEl.textContent = "Looking for token…";

  const { at_token } = await chrome.storage.session.get("at_token");
  if (!at_token) {
    statusEl.textContent = "No token found. Visit AcademicTransfer first.";
    btn.disabled = false;
    return;
  }

  statusEl.textContent = "Syncing…";
  try {
    const r = await fetch(`${SERVER}/sync`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: at_token }),
    });
    const data = await r.json();
    if (!r.ok) {
      statusEl.textContent = `Error: ${data.detail}`;
    } else {
      statusEl.textContent = `Done! ${data.total} jobs (${data.added} new).`;
      lastEl.textContent = `Last sync: ${data.timestamp}`;
    }
  } catch {
    statusEl.textContent = "Could not reach local server.";
  }
  btn.disabled = false;
});

loadStatus();