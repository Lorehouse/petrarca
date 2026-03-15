// Petrarca Clipper — Kindle Notebook Highlight Scraper
// Extracts highlights/notes from read.amazon.com/notebook
//
// Confirmed selectors (March 2026):
//   Sidebar books: .kp-notebook-library-each-book (DIV with ID = ASIN)
//   Annotated dates: INPUT#kp-notebook-annotated-date-{ASIN}
//   Highlights: .kp-notebook-highlight (with -pink, -blue, -orange, -yellow variants)
//   Notes: .kp-notebook-note
//   Metadata: .kp-notebook-metadata (contains "Location XXX" etc.)
//   Annotation container: .kp-notebook-annotation-container
//   Currently selected book ASIN: INPUT#kp-notebook-asin

(function () {
  "use strict";

  const LOG = "[petrarca-kindle-notebook]";
  function log(...args) { console.warn(LOG, ...args); }

  // --- Get all books in the sidebar with their annotated dates ----------------

  function getSidebarBooks() {
    const books = [];
    const bookEls = document.querySelectorAll(".kp-notebook-library-each-book");

    bookEls.forEach((el) => {
      const asin = el.id;
      if (!asin || asin.startsWith("kp-")) return;

      const titleEl = el.querySelector("h2.kp-notebook-searchable, h2");
      const authorEl = el.querySelector("p.kp-notebook-searchable, p");
      const title = titleEl ? titleEl.textContent.trim() : "";
      const author = authorEl ? authorEl.textContent.replace(/^By:\s*/i, "").trim() : "";

      // Annotated date from hidden input
      const dateInput = document.querySelector(`#kp-notebook-annotated-date-${asin}`);
      const annotatedDate = dateInput ? dateInput.value : "";

      books.push({ asin, title, author, annotated_date: annotatedDate });
    });

    return books;
  }

  // --- Extract highlights for the currently displayed book --------------------

  function extractCurrentBookHighlights() {
    const asinInput = document.querySelector("#kp-notebook-asin");
    const asin = asinInput ? asinInput.value : "";

    const highlights = [];
    const hlEls = document.querySelectorAll(".kp-notebook-highlight");

    hlEls.forEach((hl) => {
      const text = hl.querySelector("#highlight")?.textContent?.trim() ||
                   hl.textContent?.trim() || "";
      if (!text || text.length < 3) return;

      // Color from class name
      let color = "yellow"; // default
      if (hl.classList.contains("kp-notebook-highlight-pink")) color = "pink";
      else if (hl.classList.contains("kp-notebook-highlight-blue")) color = "blue";
      else if (hl.classList.contains("kp-notebook-highlight-orange")) color = "orange";

      // Location from nearest metadata
      const container = hl.closest(".a-spacing-base") || hl.parentElement;
      const metaEl = container?.querySelector(".kp-notebook-metadata") ||
                     container?.previousElementSibling?.querySelector(".kp-notebook-metadata");
      const metaText = metaEl ? metaEl.textContent : "";

      const locMatch = metaText.match(/Location\s+([\d,]+)/i);
      const pageMatch = metaText.match(/Page\s+(\d+)/i);
      const location = locMatch ? parseInt(locMatch[1].replace(/,/g, ""), 10) : null;
      const page = pageMatch ? parseInt(pageMatch[1], 10) : null;

      // Chapter — look for section headers above this highlight
      // (Amazon doesn't show chapter info inline, so this may be null)
      const chapter = null;

      // Timestamp from metadata
      const dateMatch = metaText.match(
        /(\w+day,\s+\w+\s+\d+,\s+\d{4})/i
      );
      const timestamp = dateMatch ? dateMatch[1] : null;

      highlights.push({ text, location, page, chapter, color, note: null, timestamp });
    });

    // Extract notes
    const noteEls = document.querySelectorAll(".kp-notebook-note");
    noteEls.forEach((noteEl) => {
      const noteText = noteEl.querySelector("#note")?.textContent?.trim() ||
                       noteEl.textContent?.trim() || "";
      if (!noteText || noteText === "Add a note") return;

      // Try to associate with the nearest highlight
      const container = noteEl.closest(".a-spacing-base") || noteEl.parentElement;
      const nearbyHl = container?.querySelector(".kp-notebook-highlight");
      if (nearbyHl) {
        // Find the matching highlight and add the note
        const hlText = nearbyHl.textContent?.trim();
        const match = highlights.find((h) => h.text === hlText);
        if (match) {
          match.note = noteText;
          return;
        }
      }
      // Standalone note
      highlights.push({
        text: noteText, location: null, page: null,
        chapter: null, color: null, note: noteText, timestamp: null,
      });
    });

    return { asin, highlights };
  }

  // --- Incremental scraping: click through unseen books -----------------------

  async function scrapeAllHighlights() {
    const sidebarBooks = getSidebarBooks();
    log(`Found ${sidebarBooks.length} books in sidebar`);

    // Load previously scraped dates from chrome.storage
    const stored = await chrome.storage.local.get("petrarca_notebook_scraped");
    const scraped = stored.petrarca_notebook_scraped || {};

    // Find books that need scraping (new or updated)
    const toScrape = sidebarBooks.filter((b) => {
      const lastScraped = scraped[b.asin];
      if (!lastScraped) return true;
      // If annotated date changed since last scrape, re-scrape
      return b.annotated_date && b.annotated_date !== lastScraped.annotated_date;
    });

    log(`Need to scrape: ${toScrape.length} (${sidebarBooks.length - toScrape.length} already up-to-date)`);

    if (toScrape.length === 0) {
      log("All books already scraped, nothing to do");
      return;
    }

    const allResults = [];

    for (const book of toScrape) {
      // Click the book in the sidebar
      const bookEl = document.getElementById(book.asin);
      if (!bookEl) continue;

      log(`Clicking ${book.title.substring(0, 40)}... (${book.asin})`);
      bookEl.click();

      // Wait for highlights to load
      await sleep(2000);

      // Extract highlights
      const result = extractCurrentBookHighlights();
      if (result.highlights.length > 0) {
        allResults.push({
          asin: book.asin,
          title: book.title,
          author: book.author,
          highlights: result.highlights,
          highlight_count: result.highlights.length,
        });
        log(`  → ${result.highlights.length} highlights`);
      }

      // Mark as scraped
      scraped[book.asin] = {
        annotated_date: book.annotated_date,
        scraped_at: new Date().toISOString(),
        highlight_count: result.highlights.length,
      };
    }

    // Save scrape state
    await chrome.storage.local.set({ petrarca_notebook_scraped: scraped });

    // Send to background for server sync
    if (allResults.length > 0) {
      log(`Sending ${allResults.length} books with highlights to server`);
      chrome.runtime.sendMessage({
        type: "kindleNotebookData",
        payload: {
          source: "notebook",
          books: allResults,
          extracted_at: new Date().toISOString(),
          url: window.location.href,
        },
      });
    }
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  // --- Message handler --------------------------------------------------------

  chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
    if (request.type === "extractKindleNotebook") {
      scrapeAllHighlights().then(() => {
        sendResponse({ ok: true });
      });
      return true;
    }
    // Quick sidebar-only extraction (no clicking)
    if (request.type === "getKindleNotebookBooks") {
      const books = getSidebarBooks();
      sendResponse({ ok: true, books });
    }
    return true;
  });

  // --- Auto-run: extract sidebar + current book on page load ------------------

  log("Loaded on:", window.location.href);

  setTimeout(() => {
    const sidebarBooks = getSidebarBooks();
    const currentHighlights = extractCurrentBookHighlights();
    log(`Sidebar: ${sidebarBooks.length} books. Current book: ${currentHighlights.asin} with ${currentHighlights.highlights.length} highlights`);

    // Send sidebar books list (for book metadata)
    if (sidebarBooks.length > 0) {
      chrome.runtime.sendMessage({
        type: "kindleNotebookData",
        payload: {
          source: "notebook-sidebar",
          books: sidebarBooks.map((b) => ({
            asin: b.asin, title: b.title, author: b.author,
            highlights: [], highlight_count: 0,
          })),
          extracted_at: new Date().toISOString(),
          url: window.location.href,
        },
      });
    }

    // Send current book highlights
    if (currentHighlights.highlights.length > 0) {
      chrome.runtime.sendMessage({
        type: "kindleNotebookData",
        payload: {
          source: "notebook",
          books: [{
            asin: currentHighlights.asin,
            title: "",
            author: "",
            highlights: currentHighlights.highlights,
            highlight_count: currentHighlights.highlights.length,
          }],
          extracted_at: new Date().toISOString(),
          url: window.location.href,
        },
      });
    }
  }, 4000);
})();
