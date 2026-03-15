// Petrarca Clipper — Amazon "Manage Your Content and Devices" Content Script
// Extracts the full Kindle library from amazon.com/hz/mycd/myx
//
// Confirmed DOM structure (March 2026):
//   Table: .ListLayout-module_table__*
//   Rows: .ListItem-module_row__* (tr elements)
//   Entity: .digital_entity_title, .digital_entity_details
//   Pagination: .page-item elements
//   Shows 25 items per page, paginated

(function () {
  "use strict";

  const LOG = "🟢 [petrarca-kindle-manage]";

  function log(...args) {
    console.warn(LOG, ...args);
  }

  console.error("🟢🟢🟢 PETRARCA KINDLE MANAGE SCRIPT LOADED 🟢🟢🟢", window.location.href);

  // --- Extract books from current page ----------------------------------------

  function extractCurrentPage() {
    const books = [];

    // Use confirmed selectors: .digital_entity_title for titles
    const rows = document.querySelectorAll(
      "tr[class*='ListItem-module_row'], [class*='digital_entity_details']"
    );

    if (rows.length === 0) {
      // Fallback: try table rows
      const tableRows = document.querySelectorAll("table tbody tr");
      log(`No ListItem rows found, trying table tbody tr: ${tableRows.length}`);
      tableRows.forEach((row) => extractBookFromRow(row, books));
    } else {
      log(`Found ${rows.length} ListItem/digital_entity rows`);
      rows.forEach((row) => extractBookFromRow(row, books));
    }

    return books;
  }

  function extractBookFromRow(row, books) {
    // Title: .digital_entity_title or first significant text
    const titleEl =
      row.querySelector(".digital_entity_title") ||
      row.querySelector("[class*='entity_title']") ||
      row.querySelector("[class*='Title']") ||
      row.querySelector("a");

    if (!titleEl) return;

    const title = titleEl.textContent.trim();
    if (!title || title.length < 2) return;

    // Author: usually the text node right after title, or in .information_row
    const authorEl =
      row.querySelector("[class*='information_row']:first-of-type") ||
      row.querySelector("p:nth-of-type(1)");

    let author = "";
    if (authorEl) {
      // The information_row contains "Author\nName" — we want just the name part
      const text = authorEl.textContent.trim();
      // If it starts with the title text, skip that
      if (!text.startsWith(title.substring(0, 20))) {
        author = text;
      }
    }

    // If author is empty, try to find it from the full row text
    if (!author) {
      const fullText = row.innerText || "";
      const lines = fullText.split("\n").map((l) => l.trim()).filter(Boolean);
      // Title is usually line 0, author line 1
      const titleIdx = lines.findIndex((l) => l.includes(title.substring(0, 30)));
      if (titleIdx >= 0 && titleIdx + 1 < lines.length) {
        const candidate = lines[titleIdx + 1];
        // Skip if it looks like a date or device info
        if (
          !candidate.startsWith("Acquired") &&
          !candidate.startsWith("In") &&
          !candidate.includes("Device") &&
          !candidate.includes("Deliver") &&
          !candidate.includes("Delete") &&
          !candidate.includes("More actions") &&
          !candidate.includes("Download")
        ) {
          author = candidate;
        }
      }
    }

    // Date acquired
    const dateMatch = (row.innerText || "").match(
      /Acquired on ([A-Za-z]+ \d+, \d{4})/
    );
    const dateAcquired = dateMatch ? dateMatch[1] : "";

    // Try to find ASIN from any link in the row
    let asin = "";
    const links = row.querySelectorAll("a[href]");
    for (const link of links) {
      const href = link.getAttribute("href") || "";
      const match =
        href.match(/\/dp\/(B[0-9A-Z]{9})/) ||
        href.match(/asin=(B[0-9A-Z]{9})/) ||
        href.match(/ASIN=(B[0-9A-Z]{9})/);
      if (match) {
        asin = match[1];
        break;
      }
    }

    books.push({
      asin,
      title,
      author,
      date_acquired: dateAcquired,
    });
  }

  // --- Pagination -------------------------------------------------------------

  function getTotalItems() {
    // Look for "Showing 1 to 25 of 883 items"
    const text = document.body.innerText;
    const match = text.match(/of (\d[\d,]*) items/);
    if (match) return parseInt(match[1].replace(/,/g, ""), 10);
    return 0;
  }

  function getCurrentPage() {
    // The active page button
    const active = document.querySelector(
      ".page-item.active, [class*='page-item'][class*='active'], [aria-current='page']"
    );
    if (active) {
      const num = parseInt(active.textContent.trim(), 10);
      if (!isNaN(num)) return num;
    }
    return 1;
  }

  function getNextPageButton() {
    // Look for "next" pagination button
    const pageItems = document.querySelectorAll(".page-item, [class*='page-item']");
    const buttons = Array.from(pageItems);

    // Find "Next" or ">" button
    for (const btn of buttons) {
      const text = btn.textContent.trim();
      if (text === "›" || text === ">" || text === "Next" || text === "»") {
        const link = btn.querySelector("a, button") || btn;
        if (!btn.classList.contains("disabled") && !btn.getAttribute("aria-disabled")) {
          return link;
        }
      }
    }

    // Also try: current page + 1
    const currentPage = getCurrentPage();
    for (const btn of buttons) {
      const num = parseInt(btn.textContent.trim(), 10);
      if (num === currentPage + 1) {
        return btn.querySelector("a, button") || btn;
      }
    }

    return null;
  }

  // --- Auto-paginate and collect all books ------------------------------------

  async function collectAllBooks() {
    const totalItems = getTotalItems();
    const totalPages = Math.ceil(totalItems / 25);
    log(`Total items: ${totalItems}, estimated pages: ${totalPages}`);

    let allBooks = [];
    let pageNum = 1;
    const maxPages = 100; // Safety limit

    while (pageNum <= maxPages) {
      log(`--- Extracting page ${pageNum}/${totalPages || "?"} ---`);

      // Wait for content to load
      await sleep(1500);

      const books = extractCurrentPage();
      log(`Page ${pageNum}: extracted ${books.length} books`);

      if (books.length === 0) {
        log("No books found on this page, stopping pagination");
        break;
      }

      allBooks = allBooks.concat(books);

      // Check if there's a next page
      const nextBtn = getNextPageButton();
      if (!nextBtn) {
        log("No next page button found, done");
        break;
      }

      // Click next page
      log("Clicking next page...");
      nextBtn.click();
      pageNum++;

      // Wait for page transition
      await sleep(2500);

      // Check if page actually changed
      if (pageNum > totalPages && totalPages > 0) {
        log("Reached total pages, done");
        break;
      }
    }

    // Deduplicate by title
    const seen = new Set();
    const unique = allBooks.filter((b) => {
      const key = b.title.toLowerCase().substring(0, 60);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    log(`=== TOTAL: ${unique.length} unique books (${allBooks.length} raw) across ${pageNum} pages ===`);
    return unique;
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  // --- Send data to background ------------------------------------------------

  function sendData(books, source) {
    if (books.length === 0) {
      log("No books to send");
      return;
    }

    log(`Sending ${books.length} books to background (source: ${source})`);

    // Send in chunks to avoid message size limits
    const CHUNK_SIZE = 100;
    for (let i = 0; i < books.length; i += CHUNK_SIZE) {
      const chunk = books.slice(i, i + CHUNK_SIZE);
      chrome.runtime.sendMessage({
        type: "kindleLibraryData",
        payload: {
          source: source,
          books: chunk,
          chunk_index: Math.floor(i / CHUNK_SIZE),
          total_chunks: Math.ceil(books.length / CHUNK_SIZE),
          total_books: books.length,
          extracted_at: new Date().toISOString(),
          url: window.location.href,
        },
      });
      log(`Sent chunk ${Math.floor(i / CHUNK_SIZE) + 1}/${Math.ceil(books.length / CHUNK_SIZE)} (${chunk.length} books)`);
    }
  }

  // --- Message handler --------------------------------------------------------

  chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
    if (request.type === "extractKindleManage") {
      log("Manual extraction triggered — collecting all pages...");
      collectAllBooks().then((books) => {
        sendData(books, "manage-page-manual");
        sendResponse({ ok: true, count: books.length });
      });
      return true; // async response
    }
    return true;
  });

  // --- Auto-run ---------------------------------------------------------------

  log("Manage content script loaded on:", window.location.href);

  // Start collection after page settles
  setTimeout(async () => {
    log("=== Starting full library extraction (all pages) ===");
    const books = await collectAllBooks();
    sendData(books, "manage-page-auto");
  }, 4000);
})();
