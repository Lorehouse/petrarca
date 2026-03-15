// Petrarca Clipper — Amazon "Manage Your Content and Devices" Scraper
// Extracts full Kindle library from amazon.com/hz/mycd/myx
//
// Confirmed selectors (March 2026):
//   Table: .ListLayout-module_table__* (1 table, 25 rows per page)
//   Rows: tr.ListItem-module_row__* or [class*='digital_entity'] (50 matches)
//   Title: .digital_entity_title
//   Author: .information_row or parsed from row innerText
//   Pagination: .page-item elements, "Showing 1 to 25 of 883 items"
//   No data-asin attributes — ASINs not directly available on this page

(function () {
  "use strict";

  const LOG = "[petrarca-kindle-manage]";
  function log(...args) { console.warn(LOG, ...args); }

  function extractCurrentPage() {
    const books = [];
    const rows = document.querySelectorAll(
      "tr[class*='ListItem-module_row'], [class*='digital_entity_details']"
    );
    if (rows.length === 0) {
      document.querySelectorAll("table tbody tr").forEach((r) => extractRow(r, books));
    } else {
      rows.forEach((r) => extractRow(r, books));
    }
    return books;
  }

  function extractRow(row, books) {
    const titleEl = row.querySelector(".digital_entity_title") ||
                    row.querySelector("[class*='entity_title']") ||
                    row.querySelector("a");
    if (!titleEl) return;

    const title = titleEl.textContent.trim();
    if (!title || title.length < 2) return;

    // Author from row text (title line, then author line)
    let author = "";
    const lines = (row.innerText || "").split("\n").map((l) => l.trim()).filter(Boolean);
    const titleIdx = lines.findIndex((l) => l.includes(title.substring(0, 30)));
    if (titleIdx >= 0 && titleIdx + 1 < lines.length) {
      const candidate = lines[titleIdx + 1];
      if (!/^(Acquired|In |Device|Deliver|Delete|More|Download)/.test(candidate)) {
        author = candidate;
      }
    }

    // Date acquired
    const dateMatch = (row.innerText || "").match(/Acquired on ([A-Za-z]+ \d+, \d{4})/);
    const dateAcquired = dateMatch ? dateMatch[1] : "";

    books.push({ asin: "", title, author, date_acquired: dateAcquired });
  }

  function getTotalItems() {
    const match = (document.body.innerText || "").match(/of (\d[\d,]*) items/);
    return match ? parseInt(match[1].replace(/,/g, ""), 10) : 0;
  }

  function getNextPageButton() {
    const items = document.querySelectorAll(".page-item, [class*='page-item']");
    for (const btn of items) {
      const text = btn.textContent.trim();
      if ((text === "›" || text === ">" || text === "Next") &&
          !btn.classList.contains("disabled")) {
        return btn.querySelector("a, button") || btn;
      }
    }
    return null;
  }

  async function collectAllBooks() {
    const total = getTotalItems();
    const totalPages = Math.ceil(total / 25);
    log(`Total: ${total} items, ~${totalPages} pages`);

    let allBooks = [];
    let page = 1;

    while (page <= 100) {
      await sleep(1500);
      const books = extractCurrentPage();
      log(`Page ${page}: ${books.length} books`);
      if (books.length === 0) break;

      allBooks = allBooks.concat(books);
      const next = getNextPageButton();
      if (!next || (page >= totalPages && totalPages > 0)) break;

      next.click();
      page++;
      await sleep(2500);
    }

    // Deduplicate
    const seen = new Set();
    return allBooks.filter((b) => {
      const key = b.title.toLowerCase().substring(0, 60);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

  function sendData(books, source) {
    if (books.length === 0) return;
    log(`Sending ${books.length} books (${source})`);
    const CHUNK = 100;
    for (let i = 0; i < books.length; i += CHUNK) {
      chrome.runtime.sendMessage({
        type: "kindleLibraryData",
        payload: {
          source, books: books.slice(i, i + CHUNK),
          total_books: books.length,
          extracted_at: new Date().toISOString(),
          url: window.location.href,
        },
      });
    }
  }

  chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
    if (request.type === "extractKindleManage") {
      collectAllBooks().then((books) => {
        sendData(books, "manage-page-manual");
        sendResponse({ ok: true, count: books.length });
      });
      return true;
    }
    return true;
  });

  log("Loaded on:", window.location.href);
  setTimeout(async () => {
    const books = await collectAllBooks();
    sendData(books, "manage-page-auto");
  }, 4000);
})();
