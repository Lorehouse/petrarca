// Petrarca Clipper — Kindle Cloud Reader Content Script
// Extracts library metadata + cover URLs from read.amazon.com
//
// Confirmed selectors (March 2026):
//   Cover images: img#cover-{ASIN} (ASIN embedded in the element ID)
//   Title/author: visible text near each cover, titles appear doubled

(function () {
  "use strict";

  const LOG = "[petrarca-kindle]";
  function log(...args) { console.warn(LOG, ...args); }

  function extractBooks() {
    const books = [];
    const coverImgs = document.querySelectorAll("img[id^='cover-']");

    coverImgs.forEach((img) => {
      const asin = img.id.replace("cover-", "");
      const coverUrl = img.src || "";

      // Walk up to find the containing book element
      let container = img.closest("[class]");
      for (let i = 0; i < 5 && container; i++) {
        const text = container.innerText || "";
        if (text.length > 10 && text.length < 2000) break;
        container = container.parentElement;
      }

      let title = "";
      let author = "";

      if (container) {
        const lines = container.innerText.trim().split("\n")
          .map((l) => l.trim()).filter(Boolean);
        // Deduplicate consecutive identical lines (titles appear doubled)
        const deduped = [];
        for (const line of lines) {
          if (deduped.length === 0 || deduped[deduped.length - 1] !== line) {
            deduped.push(line);
          }
        }
        if (deduped.length >= 2) { title = deduped[0]; author = deduped[1]; }
        else if (deduped.length === 1) { title = deduped[0]; }
      }

      if (!title && img.alt) title = img.alt;
      if (asin) books.push({ asin, title, author, cover_url: coverUrl });
    });

    return books;
  }

  // --- Message handler --------------------------------------------------------

  chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
    if (request.type === "extractKindleData") {
      const books = extractBooks();
      sendData(books);
      sendResponse({ ok: true, count: books.length });
    }
    return true;
  });

  function sendData(books) {
    if (books.length === 0) return;
    log(`Sending ${books.length} books with covers`);
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

  // --- Auto-run ---------------------------------------------------------------

  log("Loaded on:", window.location.href);
  setTimeout(() => {
    const books = extractBooks();
    log(`Extracted ${books.length} books`);
    sendData(books);
  }, 4000);
})();
