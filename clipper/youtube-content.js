// Petrarca Clipper — YouTube Content Script
// Detects YouTube watch pages and offers a "Save to Petrarca" button.
// Sends video metadata to the server, which fetches the transcript.
//
// YouTube is an SPA — we listen for yt-navigate-finish events
// to detect navigation between videos.

(function () {
  "use strict";

  const LOG = "[petrarca-youtube]";
  function log(...args) { console.warn(LOG, ...args); }

  let currentVideoId = null;
  let buttonInjected = false;

  // --- Extract video metadata from the page ---------------------------------

  function getVideoId() {
    const params = new URLSearchParams(window.location.search);
    return params.get("v") || null;
  }

  function getVideoMetadata() {
    const videoId = getVideoId();
    if (!videoId) return null;

    // Try ytInitialPlayerResponse for rich data
    let playerResponse = null;
    try {
      const scripts = document.querySelectorAll("script");
      for (const s of scripts) {
        const text = s.textContent || "";
        const match = text.match(/ytInitialPlayerResponse\s*=\s*(\{.+?\});/);
        if (match) {
          playerResponse = JSON.parse(match[1]);
          break;
        }
      }
    } catch (e) {}

    const videoDetails = playerResponse?.videoDetails || {};

    // DOM fallbacks
    const titleEl = document.querySelector(
      "h1.ytd-watch-metadata yt-formatted-string, h1.ytd-video-primary-info-renderer"
    );
    const channelEl = document.querySelector(
      "#channel-name a, ytd-channel-name a"
    );
    const descEl = document.querySelector(
      "#description-inner, ytd-text-inline-expander"
    );

    const title =
      videoDetails.title ||
      titleEl?.textContent?.trim() ||
      document.title.replace(" - YouTube", "").trim();

    const channel =
      videoDetails.author ||
      channelEl?.textContent?.trim() ||
      "";

    const description =
      videoDetails.shortDescription ||
      descEl?.textContent?.trim()?.substring(0, 1000) ||
      "";

    // Duration in seconds
    const duration = parseInt(videoDetails.lengthSeconds || "0", 10);

    // Keywords/tags
    const keywords = videoDetails.keywords || [];

    // Chapters from description (timestamp pattern)
    const chapters = [];
    const chapterPattern = /^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$/gm;
    let chMatch;
    while ((chMatch = chapterPattern.exec(description))) {
      chapters.push({ time: chMatch[1], title: chMatch[2].trim() });
    }

    return {
      video_id: videoId,
      title,
      channel,
      description: description.substring(0, 2000),
      url: `https://www.youtube.com/watch?v=${videoId}`,
      duration,
      keywords: keywords.slice(0, 20),
      chapters,
    };
  }

  // --- Inject "Save to Petrarca" button -------------------------------------

  function injectButton() {
    if (document.getElementById("petrarca-yt-btn")) return;

    // Find the action buttons area below the video
    const actionsRow = document.querySelector(
      "#top-level-buttons-computed, ytd-menu-renderer.ytd-watch-metadata"
    );
    if (!actionsRow) {
      log("Actions row not found, retrying...");
      setTimeout(injectButton, 2000);
      return;
    }

    const btn = document.createElement("button");
    btn.id = "petrarca-yt-btn";
    btn.innerHTML = "✦ Petrarca";
    btn.title = "Save this video to Petrarca for knowledge extraction";
    btn.style.cssText = `
      background: #f7f4ec;
      color: #8b2500;
      border: 1px solid #8b2500;
      border-radius: 18px;
      padding: 6px 16px;
      font-family: 'EB Garamond', Georgia, serif;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      margin-left: 8px;
      transition: all 0.2s;
      letter-spacing: 0.3px;
    `;
    btn.onmouseenter = () => {
      btn.style.background = "#8b2500";
      btn.style.color = "#f7f4ec";
    };
    btn.onmouseleave = () => {
      btn.style.background = "#f7f4ec";
      btn.style.color = "#8b2500";
    };
    btn.onclick = saveVideo;

    actionsRow.appendChild(btn);
    buttonInjected = true;
    log("Button injected");
  }

  // --- Save video to Petrarca -----------------------------------------------

  async function saveVideo() {
    const btn = document.getElementById("petrarca-yt-btn");
    if (!btn) return;

    const meta = getVideoMetadata();
    if (!meta) {
      log("Could not extract video metadata");
      return;
    }

    // Visual feedback
    btn.innerHTML = "✦ Saving...";
    btn.style.opacity = "0.7";
    btn.style.pointerEvents = "none";

    log("Saving video:", meta.title);

    // Send to background for server sync
    chrome.runtime.sendMessage(
      {
        type: "saveYouTubeVideo",
        payload: meta,
      },
      (response) => {
        if (response?.ok) {
          btn.innerHTML = "✦ Saved ✓";
          btn.style.background = "#2a7a4a";
          btn.style.color = "#fff";
          btn.style.borderColor = "#2a7a4a";
          // Gold flash
          setTimeout(() => {
            btn.style.background = "#c9a84c";
            setTimeout(() => {
              btn.style.background = "#2a7a4a";
            }, 300);
          }, 200);
          log("Video saved successfully");
        } else {
          btn.innerHTML = "✦ Error";
          btn.style.background = "#c44";
          btn.style.color = "#fff";
          log("Save failed:", response?.error);
          // Reset after 3s
          setTimeout(() => {
            btn.innerHTML = "✦ Petrarca";
            btn.style.background = "#f7f4ec";
            btn.style.color = "#8b2500";
            btn.style.borderColor = "#8b2500";
            btn.style.opacity = "1";
            btn.style.pointerEvents = "auto";
          }, 3000);
        }
      }
    );
  }

  // --- Handle SPA navigation ------------------------------------------------

  function onNavigate() {
    const videoId = getVideoId();
    if (!videoId || videoId === currentVideoId) return;

    currentVideoId = videoId;
    buttonInjected = false;
    log("New video:", videoId);

    // Remove old button
    const oldBtn = document.getElementById("petrarca-yt-btn");
    if (oldBtn) oldBtn.remove();

    // Inject new button after a delay (DOM needs to settle)
    setTimeout(injectButton, 2000);
  }

  // --- Initialize -----------------------------------------------------------

  log("Loaded on:", window.location.href);

  // YouTube SPA navigation events
  document.addEventListener("yt-navigate-finish", onNavigate);

  // Initial load
  if (window.location.pathname === "/watch") {
    currentVideoId = getVideoId();
    setTimeout(injectButton, 3000);
  }
})();
