// Petrarca Clipper — Kindle Cloud Reader Content Script
// Extracts library metadata + cover images from read.amazon.com
//
// Confirmed DOM structure (March 2026):
//   Cover images: img#cover-B00685OM8W (ASIN in the ID!)
//   Title/Author: visible text near each cover, titles appear doubled
//   Headings: h3#library_title, h3#notes_title
//   No IndexedDB databases available
//   No KindleModuleManager on library page (it's a different app now)

(function () {
  "use strict";

  const LOG = "🔶 [petrarca-kindle]";
  function log(...args) { console.warn(LOG, ...args); }

  console.error("🔶🔶🔶 PETRARCA KINDLE CONTENT SCRIPT LOADED 🔶🔶🔶", window.location.href);

  // --- Extract books using cover image IDs (most reliable) --------------------

  function extractBooks() {
    const books = [];

    // Primary method: find all cover images — ASIN is in the ID
    const coverImgs = document.querySelectorAll("img[id^='cover-']");
    log(`Found ${coverImgs.length} cover images`);

    coverImgs.forEach((img) => {
      const asin = img.id.replace("cover-", "");
      const coverUrl = img.src || "";

      // Walk up to find the containing book element
      let container = img.closest("[class]");
      // Try several levels up to find the book container
      for (let i = 0; i < 5 && container; i++) {
        const text = container.innerText || "";
        if (text.length > 10 && text.length < 2000) break;
        container = container.parentElement;
      }

      let title = "";
      let author = "";

      if (container) {
        const text = container.innerText.trim();
        const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);

        // Pattern: title appears (sometimes doubled), then author as "Last, First"
        // Deduplicate consecutive identical lines
        const deduped = [];
        for (const line of lines) {
          if (deduped.length === 0 || deduped[deduped.length - 1] !== line) {
            deduped.push(line);
          }
        }

        if (deduped.length >= 2) {
          title = deduped[0];
          author = deduped[1];
        } else if (deduped.length === 1) {
          title = deduped[0];
        }
      }

      // Fallback: try img alt text
      if (!title && img.alt) {
        title = img.alt;
      }

      if (asin) {
        books.push({ asin, title, author, cover_url: coverUrl });
      }
    });

    // If no cover images found, try text-based extraction
    if (books.length === 0) {
      log("No cover images found, trying text-based extraction...");
      extractFromText(books);
    }

    return books;
  }

  function extractFromText(books) {
    // Fallback: parse the visible text which shows title/author pairs
    const bodyText = document.body?.innerText || "";
    const lines = bodyText.split("\n").map((l) => l.trim()).filter(Boolean);

    // Look for patterns: titles are usually longer, authors have commas (Last, First)
    for (let i = 0; i < lines.length - 1; i++) {
      const line = lines[i];
      const next = lines[i + 1];

      // Skip navigation/UI text
      if (line.length < 3 || line.length > 300) continue;
      if (/^(Skip|Search|Library|Notes|Kindle|All|EN|Hello|Cart|Sign)/.test(line)) continue;

      // If next line looks like "Last, First" author format
      if (next && /^[A-Z][a-z]+,\s/.test(next) && next.length < 100) {
        // Check we haven't already captured this title (titles appear doubled)
        if (!books.some((b) => b.title === line)) {
          books.push({
            asin: "",
            title: line,
            author: next,
            cover_url: "",
          });
          i++; // Skip the author line
        }
      }
    }
  }

  // --- Also probe for the Notes & Highlights section --------------------------

  function extractNotesSection() {
    const notesHeading = document.querySelector("#notes_title");
    if (!notesHeading) return null;

    log("Notes & Highlights section found");
    // The notes section content follows the heading
    let section = notesHeading.parentElement;
    while (section && section.innerText?.length < 100) {
      section = section.parentElement;
    }

    if (section) {
      const text = section.innerText;
      log("Notes section text (first 500 chars):", text.substring(0, 500));
      return text;
    }
    return null;
  }

  // --- Send data to background ------------------------------------------------

  function sendData(books) {
    if (books.length === 0) {
      log("No books to send");
      return;
    }

    log(`Sending ${books.length} books with covers to background`);
    books.slice(0, 5).forEach((b, i) => {
      log(`  [${i}] ${b.asin}: "${b.title}" by ${b.author} (cover: ${b.cover_url ? "yes" : "no"})`);
    });

    chrome.runtime.sendMessage({
      type: "kindleLibraryData",
      payload: {
        source: "cloud-reader",
        books: books,
        extracted_at: new Date().toISOString(),
        url: window.location.href,
      },
    });
  }

  // --- Message handler --------------------------------------------------------

  chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
    if (request.type === "extractKindleData") {
      log("Manual extraction triggered");
      const books = extractBooks();
      sendData(books);
      sendResponse({ ok: true, count: books.length });
    }
    return true;
  });

  // --- Auto-run ---------------------------------------------------------------

  log("Content script loaded on:", window.location.href);

  setTimeout(() => {
    log("=== Starting extraction ===");
    const books = extractBooks();
    sendData(books);
    extractNotesSection();
  }, 3000);

  // Re-run after more time (page may lazy-load more covers)
  setTimeout(() => {
    log("=== Delayed re-extraction (12s) ===");
    const books = extractBooks();
    if (books.length > 0) sendData(books);
  }, 12000);
})();
