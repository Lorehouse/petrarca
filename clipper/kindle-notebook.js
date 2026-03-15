// Petrarca Clipper — Kindle Notebook Content Script
// Extracts highlights and notes from read.amazon.com/notebook

(function () {
  "use strict";

  const LOG_PREFIX = "🔷 [petrarca-kindle-notebook]";
  const EXTRACTION_DELAY_MS = 3000;

  function log(...args) {
    console.warn(LOG_PREFIX, ...args);
  }

  function logGroup(label) {
    console.warn(`${LOG_PREFIX} ▸▸▸ ${label} ▸▸▸`);
  }

  function logGroupEnd() {
    console.warn(`${LOG_PREFIX} ◂◂◂`);
  }

  console.error("🔷🔷🔷 PETRARCA KINDLE NOTEBOOK SCRIPT LOADED 🔷🔷🔷", window.location.href);

  // --- Page diagnostics -------------------------------------------------------

  function dumpPageDiagnostics() {
    logGroup("NOTEBOOK PAGE DIAGNOSTICS");
    log("URL:", window.location.href);
    log("Title:", document.title);
    log("Body text length:", document.body?.innerText?.length);

    // All unique classes
    const allClasses = new Set();
    document.querySelectorAll("[class]").forEach((el) => {
      el.classList.forEach((c) => allClasses.add(c));
    });
    const classArr = Array.from(allClasses);

    // Filter for notebook/highlight/book related
    const relevant = classArr.filter((c) =>
      /notebook|highlight|note|book|annotation|clip|mark|library|kp-/i.test(c)
    );
    log("Relevant classes:", relevant);
    log("All classes (first 100):", classArr.slice(0, 100));

    // All IDs
    const allIds = Array.from(document.querySelectorAll("[id]")).map(
      (el) => `${el.tagName}#${el.id}`
    );
    const relevantIds = allIds.filter((id) =>
      /highlight|note|book|annotation|library|notebook/i.test(id)
    );
    log("Relevant IDs:", relevantIds);

    // Top-level structure
    log("--- Body structure ---");
    if (document.body) {
      Array.from(document.body.children)
        .slice(0, 20)
        .forEach((child, i) => {
          log(
            `  [${i}]`,
            child.tagName,
            child.id ? `#${child.id}` : "",
            child.className
              ? `.${Array.from(child.classList).join(".")}`
              : "",
            `(${child.children?.length} children, ${child.innerText?.length || 0} chars)`
          );
        });
    }

    logGroupEnd();
  }

  // --- Extraction with logging ------------------------------------------------

  function extractNotebookData() {
    logGroup("NOTEBOOK EXTRACTION");

    // Try many different selector patterns
    const bookSelectors = [
      ".kp-notebook-library-each-book",
      "[class*='notebook-library-each-book']",
      "[class*='kp-notebook']",
      "[class*='notebookLibrary']",
      ".a-section[data-asin]",
      "[class*='BookAnnotation']",
      "[class*='book-annotation']",
      "[class*='annotationSection']",
      ".a-section .a-spacing-base",
      "div[id*='annotation']",
      "div[id*='highlight']",
      "div[id*='book']",
    ];

    for (const selector of bookSelectors) {
      const els = document.querySelectorAll(selector);
      if (els.length > 0) {
        log(`Selector "${selector}": ${els.length} matches`);
        Array.from(els)
          .slice(0, 2)
          .forEach((el, i) => {
            log(
              `  [${i}]`,
              el.tagName,
              el.id ? `#${el.id}` : "",
              el.className
                ? `.${String(el.className).substring(0, 100)}`
                : "",
              el.innerText?.substring(0, 200)
            );
          });
      }
    }

    // Highlight selectors
    const highlightSelectors = [
      "[id^='highlight-']",
      ".kp-notebook-highlight",
      "[class*='highlight']",
      "[class*='Highlight']",
      "span.a-text-bold",
      ".a-text-quote",
      "blockquote",
    ];

    for (const selector of highlightSelectors) {
      const els = document.querySelectorAll(selector);
      if (els.length > 0) {
        log(`Highlight selector "${selector}": ${els.length} matches`);
        Array.from(els)
          .slice(0, 2)
          .forEach((el, i) => {
            log(`  [${i}]`, el.innerText?.substring(0, 150));
          });
      }
    }

    // Note selectors
    const noteSelectors = [
      "[id^='note-']",
      ".kp-notebook-note",
      "[class*='note']",
      "[class*='Note']",
    ];

    for (const selector of noteSelectors) {
      const els = document.querySelectorAll(selector);
      if (els.length > 0) {
        log(`Note selector "${selector}": ${els.length} matches`);
      }
    }

    // Dump visible text for analysis
    const bodyText = document.body?.innerText || "";
    log("Page text (first 3000 chars):", bodyText.substring(0, 3000));

    // Also check for the sidebar book list
    const sidebarSelectors = [
      ".kp-notebook-library-each-book",
      "[class*='sidebar'] a",
      "[class*='Sidebar'] a",
      "nav a",
      ".a-column a[href*='#']",
    ];
    for (const selector of sidebarSelectors) {
      const els = document.querySelectorAll(selector);
      if (els.length > 0) {
        log(`Sidebar selector "${selector}": ${els.length} matches`);
        Array.from(els)
          .slice(0, 5)
          .forEach((el, i) => {
            log(`  [${i}]`, el.innerText?.substring(0, 80), el.href?.substring(0, 80));
          });
      }
    }

    logGroupEnd();

    // Try actual extraction with all working selectors
    return tryExtractBooks();
  }

  function tryExtractBooks() {
    const books = [];

    // Cast a wide net for book sections
    const bookElements = document.querySelectorAll(
      ".kp-notebook-library-each-book, " +
        "[class*='notebook-library-each-book'], " +
        "[class*='kp-notebook'] > div, " +
        ".a-section[data-asin], " +
        "[data-asin]"
    );

    log(`tryExtractBooks: found ${bookElements.length} candidate elements`);

    bookElements.forEach((bookEl) => {
      const titleEl = bookEl.querySelector("h2, h3, h4, [class*='title'], [class*='Title']");
      const authorEl = bookEl.querySelector("[class*='author'], [class*='Author'], p:nth-child(2)");
      const title = titleEl ? titleEl.textContent.trim() : "";
      const author = authorEl ? authorEl.textContent.trim() : "";
      let asin = bookEl.getAttribute("data-asin") || "";

      // Extract highlights with rich metadata
      const highlights = [];
      let currentChapter = "";

      // Walk through all child elements to track chapter context
      const allChildren = bookEl.querySelectorAll("*");
      allChildren.forEach((el) => {
        // Chapter/section headers — these appear before their highlights
        if (
          el.matches(
            "[class*='chapter'], [class*='section-heading'], " +
              "[class*='Chapter'], h3, h4, [class*='sectionHeading']"
          )
        ) {
          const chText = el.textContent.trim();
          if (chText && chText.length < 200 && chText.length > 2) {
            currentChapter = chText;
          }
        }

        // Highlight elements
        if (
          el.matches(
            "[id^='highlight-'], .kp-notebook-highlight, " +
              "#highlight, [class*='highlightText']"
          )
        ) {
          const text = el.textContent?.trim();
          if (!text || text.length < 5) return;

          // Location/page metadata — usually a nearby sibling or parent's child
          const container =
            el.closest(".a-row, [class*='row'], [class*='annotation']") ||
            el.parentElement;
          const metaEl = container?.querySelector(
            ".kp-notebook-metadata, [class*='metadata'], " +
              ".a-color-secondary, [class*='location']"
          );
          const metaText = metaEl ? metaEl.textContent.trim() : "";

          // Parse location number from "Location 1234" or "Page 56"
          const locMatch = metaText.match(/Location\s+([\d,]+)/i);
          const pageMatch = metaText.match(/Page\s+(\d+)/i);
          const location = locMatch
            ? parseInt(locMatch[1].replace(/,/g, ""), 10)
            : null;
          const page = pageMatch ? parseInt(pageMatch[1], 10) : null;

          // Highlight color
          const colorEl = container?.querySelector(
            "[class*='color'], [class*='Color'], " +
              "[style*='border-color'], [style*='background']"
          );
          let color = "";
          if (colorEl) {
            const style = colorEl.getAttribute("style") || "";
            const cls = colorEl.className || "";
            if (/yellow/i.test(style + cls)) color = "yellow";
            else if (/blue/i.test(style + cls)) color = "blue";
            else if (/pink|red/i.test(style + cls)) color = "pink";
            else if (/orange/i.test(style + cls)) color = "orange";
          }

          // Timestamp — sometimes shown as "Added on Month Day, Year"
          const dateMatch = metaText.match(
            /(?:Added on\s+)?(\w+ \d+,?\s*\d{4})/i
          );
          const timestamp = dateMatch ? dateMatch[1] : "";

          // Associated note — usually right after the highlight
          let note = "";
          const noteEl = container?.querySelector(
            "[id^='note-'], .kp-notebook-note, [class*='noteText'], #note"
          );
          if (noteEl) {
            const noteText = noteEl.textContent.trim();
            if (noteText && noteText !== "Add a note") {
              note = noteText;
            }
          }

          highlights.push({
            text: text.substring(0, 2000),
            location,
            page,
            chapter: currentChapter || null,
            color: color || null,
            note: note || null,
            timestamp: timestamp || null,
          });
        }
      });

      if (title || highlights.length > 0) {
        books.push({
          asin,
          title,
          author,
          highlights,
          highlight_count: highlights.length,
        });
      }
    });

    log(`tryExtractBooks: extracted ${books.length} books`);
    return books;
  }

  // --- Send data to background ------------------------------------------------

  function sendData(books) {
    log(`Sending ${books.length} books to background`);
    chrome.runtime.sendMessage({
      type: "kindleNotebookData",
      payload: {
        source: "notebook",
        books: books,
        extracted_at: new Date().toISOString(),
        url: window.location.href,
      },
    });
  }

  // --- Message handler --------------------------------------------------------

  chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
    if (request.type === "extractKindleNotebook") {
      log("Manual extraction triggered");
      dumpPageDiagnostics();
      const books = extractNotebookData();
      sendData(books);
      sendResponse({ ok: true, count: books.length });
    }
    return true;
  });

  // --- Auto-run ---------------------------------------------------------------

  log("Notebook content script loaded on:", window.location.href);

  setTimeout(() => {
    log("=== Starting notebook extraction ===");
    dumpPageDiagnostics();
    const books = extractNotebookData();
    sendData(books);
  }, EXTRACTION_DELAY_MS);

  // Re-run after more time
  setTimeout(() => {
    log("=== Delayed notebook re-extraction (12s) ===");
    const books = extractNotebookData();
    if (books.length > 0) sendData(books);
  }, 12000);
})();
