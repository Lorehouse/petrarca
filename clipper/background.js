// Petrarca Clipper — Background Service Worker
// Handles badge state, message routing, Twitter cookie sync, and Kindle data sync.

const SERVER_DEFAULT = "http://alifstian.duckdns.org:8090";
const COOKIE_SYNC_INTERVAL_MS = 4 * 60 * 60 * 1000; // 4 hours
const KINDLE_SYNC_INTERVAL_MS = 4 * 60 * 60 * 1000; // 4 hours
const HIGHLIGHT_SYNC_PERIOD_MINUTES = 720; // 12 hours

// --- Periodic highlight sync via chrome.alarms ---
chrome.alarms.create("kindleHighlightSync", {
  delayInMinutes: 5,
  periodInMinutes: HIGHLIGHT_SYNC_PERIOD_MINUTES,
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "kindleHighlightSync") {
    console.log("[petrarca-kindle] Alarm triggered: highlight sync");
    syncHighlightsInBackground().catch((e) => {
      console.log(`[petrarca-kindle] Scheduled highlight sync failed: ${e.message}`);
    });
  }
});

// Listen for messages from popup or content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "saveClip") {
    handleSave(message.payload)
      .then((result) => sendResponse(result))
      .catch(async (err) => {
        // Offline fallback: queue locally
        try {
          await storeLocally(message.payload);
          console.log("[petrarca] Server unavailable, saved locally");
          sendResponse({ ok: true, queued: true });
        } catch (storageErr) {
          sendResponse({ ok: false, error: err.message });
        }
      });
    return true;
  }

  if (message.type === "addNote") {
    handleAddNote(message.payload)
      .then((result) => sendResponse(result))
      .catch((err) => {
        console.log(`[petrarca] addNote failed: ${err.message}`);
        sendResponse({ ok: false, error: err.message });
      });
    return true;
  }

  if (message.type === "cancelSave") {
    handleCancelSave(message.payload)
      .then((result) => sendResponse(result))
      .catch((err) => {
        console.log(`[petrarca] cancelSave failed: ${err.message}`);
        sendResponse({ ok: false, error: err.message });
      });
    return true;
  }

  if (message.type === "setBadge") {
    chrome.action.setBadgeText({ text: message.text || "" });
    chrome.action.setBadgeBackgroundColor({ color: "#8b2500" });
    sendResponse({ ok: true });
  }

  if (message.type === "clearBadge") {
    chrome.action.setBadgeText({ text: "" });
    sendResponse({ ok: true });
  }

  // Kindle library data from content script (read.amazon.com)
  if (message.type === "kindleLibraryData") {
    handleKindleSync("library", message.payload)
      .then((result) => sendResponse(result))
      .catch((err) => {
        console.log(`[petrarca-kindle] Library sync failed: ${err.message}`);
        sendResponse({ ok: false, error: err.message });
      });
    return true;
  }

  // YouTube video save
  if (message.type === "saveYouTubeVideo") {
    handleYouTubeSave(message.payload)
      .then((result) => sendResponse(result))
      .catch((err) => {
        console.log(`[petrarca-youtube] Save failed: ${err.message}`);
        sendResponse({ ok: false, error: err.message });
      });
    return true;
  }

  // Trigger background highlight sync
  if (message.type === "kindleSyncHighlights") {
    syncHighlightsInBackground()
      .then(() => sendResponse({ ok: true }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true;
  }

  // Kindle notebook data from content script (read.amazon.com/notebook)
  if (message.type === "kindleNotebookData") {
    handleKindleSync("notebook", message.payload)
      .then((result) => sendResponse(result))
      .catch((err) => {
        console.log(`[petrarca-kindle] Notebook sync failed: ${err.message}`);
        sendResponse({ ok: false, error: err.message });
      });
    return true;
  }
});

async function handleSave(payload) {
  const settings = await loadSettings();
  const serverUrl = (settings.serverUrl || SERVER_DEFAULT).replace(/\/+$/, "");
  const authToken = settings.authToken || "";

  const headers = { "Content-Type": "application/json" };
  if (authToken) {
    headers["X-Petrarca-Token"] = authToken;
  }

  const response = await fetch(`${serverUrl}/ingest`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status}: ${text.slice(0, 200)}`);
  }

  return { ok: true };
}

async function handleAddNote(payload) {
  const settings = await loadSettings();
  const serverUrl = (settings.serverUrl || SERVER_DEFAULT).replace(/\/+$/, "");
  const authToken = settings.authToken || "";

  const headers = { "Content-Type": "application/json" };
  if (authToken) {
    headers["X-Petrarca-Token"] = authToken;
  }

  const response = await fetch(`${serverUrl}/ingest-note`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status}: ${text.slice(0, 200)}`);
  }

  return { ok: true };
}

async function handleCancelSave(payload) {
  const settings = await loadSettings();
  const serverUrl = (settings.serverUrl || SERVER_DEFAULT).replace(/\/+$/, "");
  const authToken = settings.authToken || "";

  const headers = { "Content-Type": "application/json" };
  if (authToken) {
    headers["X-Petrarca-Token"] = authToken;
  }

  const response = await fetch(`${serverUrl}/ingest-cancel`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status}: ${text.slice(0, 200)}`);
  }

  return { ok: true };
}

async function storeLocally(payload) {
  const result = await chrome.storage.local.get(["petrarca_queue"]);
  const queue = result.petrarca_queue || [];
  queue.push({
    ...payload,
    queued_at: new Date().toISOString(),
  });
  await chrome.storage.local.set({ petrarca_queue: queue });
}

function loadSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(
      ["petrarca_server_url", "petrarca_auth_token"],
      (result) => {
        resolve({
          serverUrl: result.petrarca_server_url || "",
          authToken: result.petrarca_auth_token || "",
        });
      }
    );
  });
}

// ---------------------------------------------------------------------------
// Twitter/X cookie auto-sync
// ---------------------------------------------------------------------------

async function maybeSyncTwitterCookies(tabUrl) {
  // Only trigger on twitter.com / x.com
  if (!tabUrl || (!tabUrl.includes("x.com") && !tabUrl.includes("twitter.com"))) {
    return;
  }

  // Throttle: check last sync time
  const { petrarca_last_cookie_sync } = await chrome.storage.local.get(
    "petrarca_last_cookie_sync"
  );
  const now = Date.now();
  if (petrarca_last_cookie_sync && now - petrarca_last_cookie_sync < COOKIE_SYNC_INTERVAL_MS) {
    return;
  }

  // Extract auth_token and ct0 cookies (try x.com first, then twitter.com)
  let authCookie = await chrome.cookies.get({ url: "https://x.com", name: "auth_token" });
  let ct0Cookie = await chrome.cookies.get({ url: "https://x.com", name: "ct0" });

  if (!authCookie || !ct0Cookie) {
    authCookie = await chrome.cookies.get({ url: "https://twitter.com", name: "auth_token" });
    ct0Cookie = await chrome.cookies.get({ url: "https://twitter.com", name: "ct0" });
  }

  if (!authCookie || !ct0Cookie) {
    console.log("[petrarca] No Twitter cookies found");
    return;
  }

  // Push to server
  const settings = await loadSettings();
  const serverUrl = (settings.serverUrl || SERVER_DEFAULT).replace(/\/+$/, "");
  const authToken = settings.authToken || "";

  try {
    const headers = { "Content-Type": "application/json" };
    if (authToken) {
      headers["X-Petrarca-Token"] = authToken;
    }

    const resp = await fetch(`${serverUrl}/twitter/cookies`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        auth_token: authCookie.value,
        ct0: ct0Cookie.value,
      }),
    });

    if (resp.ok) {
      await chrome.storage.local.set({ petrarca_last_cookie_sync: now });
      console.log("[petrarca] Twitter cookies synced to server");
    } else {
      console.log(`[petrarca] Cookie sync failed: ${resp.status}`);
    }
  } catch (err) {
    console.log(`[petrarca] Cookie sync error: ${err.message}`);
  }
}

// Trigger on tab updates (navigating to X/Twitter or Amazon Kindle)
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url) {
    maybeSyncTwitterCookies(tab.url);
    maybeTriggerKindleExtraction(tabId, tab.url);
  }
});

// ---------------------------------------------------------------------------
// Kindle data sync
// ---------------------------------------------------------------------------

async function handleKindleSync(dataType, payload) {
  // Throttle: don't sync more than once every 4 hours
  const storageKey = `petrarca_last_kindle_${dataType}_sync`;
  const stored = await chrome.storage.local.get(storageKey);
  const now = Date.now();

  if (stored[storageKey] && now - stored[storageKey] < KINDLE_SYNC_INTERVAL_MS) {
    console.log(`[petrarca-kindle] ${dataType} sync throttled (last: ${new Date(stored[storageKey]).toISOString()})`);
    return { ok: true, throttled: true };
  }

  const settings = await loadSettings();
  const serverUrl = (settings.serverUrl || SERVER_DEFAULT).replace(/\/+$/, "");
  const authToken = settings.authToken || "";

  const headers = { "Content-Type": "application/json" };
  if (authToken) {
    headers["X-Petrarca-Token"] = authToken;
  }

  const response = await fetch(`${serverUrl}/kindle/sync`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      data_type: dataType,
      ...payload,
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status}: ${text.slice(0, 200)}`);
  }

  await chrome.storage.local.set({ [storageKey]: now });
  console.log(`[petrarca-kindle] ${dataType} data synced to server`);
  return { ok: true };
}

// ---------------------------------------------------------------------------
// YouTube video save
// ---------------------------------------------------------------------------

async function handleYouTubeSave(payload) {
  const settings = await loadSettings();
  const serverUrl = (settings.serverUrl || SERVER_DEFAULT).replace(/\/+$/, "");
  const authToken = settings.authToken || "";

  const headers = { "Content-Type": "application/json" };
  if (authToken) {
    headers["X-Petrarca-Token"] = authToken;
  }

  const response = await fetch(`${serverUrl}/ingest-youtube`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status}: ${text.slice(0, 200)}`);
  }

  const result = await response.json();
  console.log(`[petrarca-youtube] Saved: ${payload.title}`);
  return { ok: true, ...result };
}

async function maybeTriggerKindleExtraction(tabId, tabUrl) {
  if (!tabUrl || !tabUrl.includes("read.amazon.com")) {
    return;
  }
  console.log(`[petrarca-kindle] Kindle page detected: ${tabUrl}`);
}

// Background highlight sync: opens notebook in a tab, scrapes, closes
async function syncHighlightsInBackground() {
  console.log("[petrarca-kindle] Starting background highlight sync...");

  const tab = await chrome.tabs.create({
    url: "https://read.amazon.com/notebook",
    active: false, // open in background
  });

  // Wait for page to load
  await new Promise((resolve) => {
    function listener(tabId, info) {
      if (tabId === tab.id && info.status === "complete") {
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }
    }
    chrome.tabs.onUpdated.addListener(listener);
  });

  // Wait extra for sidebar to populate
  await new Promise((r) => setTimeout(r, 6000));

  // Tell content script to scrape all highlights incrementally
  try {
    await chrome.tabs.sendMessage(tab.id, { type: "extractKindleNotebook" });
    // Give it time to click through books
    await new Promise((r) => setTimeout(r, 30000));
  } catch (e) {
    console.log(`[petrarca-kindle] Highlight sync error: ${e.message}`);
  }

  // Close the tab
  try { await chrome.tabs.remove(tab.id); } catch (e) {}
  console.log("[petrarca-kindle] Background highlight sync complete");
}
