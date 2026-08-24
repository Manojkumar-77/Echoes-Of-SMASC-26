/**
 * ============================================================================
 * COLLEGE MEMORIES '26
 * GALLERY — FULLY REBUILT CONTROLLER
 * ============================================================================
 *
 * Designed for the current Django Gallery architecture.
 *
 * Supports:
 * ---------------------------------------------------------------------------
 * ✓ Gallery progressive rendering
 * ✓ Stable database photo IDs
 * ✓ Gallery lightbox opening
 * ✓ Correct clicked-image mapping
 * ✓ Works after Load More
 * ✓ Works with 3000+ photos
 * ✓ Previous / Next compatibility through VerticalThumbnailViewer
 * ✓ Keyboard-safe interactions
 * ✓ No duplicate event listeners
 * ✓ Selected Memories accordion
 * ✓ Selected Memories keyboard controls
 * ✓ Touch / pointer friendly
 * ✓ Responsive-safe
 * ✓ No React required
 * ✓ No Tailwind required
 * ✓ No DOM index dependency
 * ✓ No accidental metadata-card clicks
 * ✓ Safe malformed/missing field handling
 * ✓ No inline layout manipulation beyond hidden state
 * ✓ Browser back/forward safe
 * ✓ Prevents duplicate viewer initialization
 *
 * IMPORTANT:
 * ---------------------------------------------------------------------------
 * This JS intentionally DOES NOT control grid columns, aspect ratios,
 * mobile breakpoints, or card sizing. Those belong exclusively to gallery.css.
 * ============================================================================
 */

(() => {
  "use strict";

  /* ==========================================================================
     GLOBAL CONFIG
     ========================================================================== */

  const CONFIG = Object.freeze({
    INITIAL_BATCH_SIZE: 24,
    LOAD_MORE_BATCH_SIZE: 24,

    SELECTORS: {
      galleryGrid: "#gallery-grid",
      galleryItem: ".gallery-item",
      galleryImageButton: ".gallery-image-button",
      loadMoreButton: "#gallery-load-more",

      selectedTrack: "#selected-memories-track",
      selectedItem: ".selected-memory-item",

      lightbox: "#gallery-lightbox",
      lightboxShell: ".vertical-viewer-shell",
      lightboxStage: "#gallery-viewer-stage",
      lightboxImage: "#gallery-lightbox-img",
      lightboxBlur: "#gallery-lightbox-blur",
      lightboxThumbs: "#gallery-viewer-thumbs",
      lightboxTitle: "#gallery-lightbox-title",
      lightboxCategory: "#gallery-lightbox-category",
      lightboxDate: "#gallery-lightbox-date",
      lightboxDescription: "#gallery-lightbox-caption",
      lightboxCounter: "#gallery-lightbox-counter",
      lightboxPrevious: "#gallery-lightbox-prev",
      lightboxNext: "#gallery-lightbox-next",
      lightboxClose: "#gallery-lightbox-close",
    },
  });

  /* ==========================================================================
     STATE
     ========================================================================== */

  const state = {
    initialized: false,

    gallery: {
      grid: null,
      loadMoreButton: null,

      allItems: [],
      visibleCount: 0,

      viewer: null,
      viewerReady: false,

      opening: false,
    },

    selectedMemories: {
      track: null,
      items: [],
      activeIndex: 0,
    },
  };

  /* ==========================================================================
     DOM READY
     ========================================================================== */

  function ready(callback) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback, {
        once: true,
      });
    } else {
      callback();
    }
  }

  ready(initGalleryPage);

  /* ==========================================================================
     MAIN INITIALIZATION
     ========================================================================== */

  function initGalleryPage() {
    if (state.initialized) {
      return;
    }

    state.initialized = true;

    initGalleryArchive();
    initGalleryViewer();
    initSelectedMemories();

    /*
     * Handle browser back/forward cache.
     *
     * Some browsers restore a page without firing DOMContentLoaded again.
     */
    window.addEventListener("pageshow", handlePageShow);

    console.info("[Gallery] Controller initialized.");
  }

  function handlePageShow(event) {
    if (!event.persisted) {
      return;
    }

    refreshGalleryCollection();
  }

  /* ==========================================================================
     BASIC HELPERS
     ========================================================================== */

  function toArray(collection) {
    return Array.from(collection || []);
  }

  function getString(element, attribute) {
    if (!element) {
      return "";
    }

    return (
      element.getAttribute(attribute) ||
      ""
    ).trim();
  }

  function getDatasetValue(element, key) {
    if (!element || !element.dataset) {
      return "";
    }

    return String(
      element.dataset[key] ?? ""
    ).trim();
  }

  function normalizeId(value) {
    return String(value ?? "").trim();
  }

  function clamp(value, min, max) {
    return Math.min(
      max,
      Math.max(min, value)
    );
  }

  /* ==========================================================================
     GALLERY ARCHIVE
     ========================================================================== */

  function initGalleryArchive() {
    const grid = document.querySelector(
      CONFIG.SELECTORS.galleryGrid
    );

    if (!grid) {
      return;
    }

    state.gallery.grid = grid;

    state.gallery.loadMoreButton =
      document.querySelector(
        CONFIG.SELECTORS.loadMoreButton
      );

    /*
     * With server-side pagination all rendered cards are visible.
     * No DOM hiding needed — all initial cards are shown as-is.
     */
    refreshGalleryCollection();

    bindLoadMoreButton();

    /*
     * Event delegation.
     *
     * One listener survives:
     * - pagination
     * - future DOM additions
     * - Django partial rendering
     * - filtering
     */
    grid.addEventListener(
      "click",
      handleGalleryGridClick
    );

    grid.addEventListener(
      "keydown",
      handleGalleryGridKeyboard
    );
  }

  /* ==========================================================================
     REFRESH COLLECTION
     ========================================================================== */

  function refreshGalleryCollection() {
    const grid = state.gallery.grid;

    if (!grid) {
      state.gallery.allItems = [];
      return;
    }

    state.gallery.allItems = toArray(
      grid.querySelectorAll(
        CONFIG.SELECTORS.galleryItem
      )
    ).filter((item) => {
      return Boolean(
        item.querySelector(
          CONFIG.SELECTORS.galleryImageButton
        )
      );
    });

    /*
     * Keep data-count synchronized with actual DOM.
     */
    grid.dataset.count = String(
      state.gallery.allItems.length
    );
  }

  /* ==========================================================================
     LOAD MORE — AJAX SERVER-SIDE PAGINATION
     ========================================================================== */

  function bindLoadMoreButton() {
    const button =
      state.gallery.loadMoreButton;

    if (!button) {
      return;
    }

    button.addEventListener(
      "click",
      handleLoadMore
    );
  }

  function handleLoadMore(event) {
    event.preventDefault();

    const grid = state.gallery.grid;
    const button = state.gallery.loadMoreButton;

    if (!grid || !button || button.disabled) {
      return;
    }

    /*
     * Read pagination state from data attributes on #gallery-grid.
     */
    const hasMore = grid.dataset.hasMore === "true";
    const nextPage = parseInt(grid.dataset.nextPage, 10);
    const category = grid.dataset.category || "";
    const apiUrl = grid.dataset.apiUrl || "/gallery/photos/";

    if (!hasMore || isNaN(nextPage)) {
      button.hidden = true;
      return;
    }

    /*
     * Lock button during fetch.
     */
    button.disabled = true;
    button.textContent = "Loading…";

    const url = new URL(apiUrl, window.location.origin);
    url.searchParams.set("page", nextPage);
    if (category) {
      url.searchParams.set("category", category);
    }

    fetch(url.toString(), {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(
            `Gallery API returned ${response.status}`
          );
        }
        return response.json();
      })
      .then((data) => {
        const photos = data.photos || [];

        photos.forEach((photo, idx) => {
          const card = buildPhotoCard(
            photo,
            state.gallery.allItems.length + idx
          );
          grid.appendChild(card);
        });

        /*
         * Update grid pagination state.
         */
        grid.dataset.hasMore = data.has_more ? "true" : "false";
        grid.dataset.nextPage = data.next_page || "";

        /*
         * Sync allItems registry so lightbox sees new cards.
         */
        refreshGalleryCollection();

        /*
         * Update Load More button state.
         */
        if (data.has_more) {
          button.disabled = false;
          button.textContent = "Load More Memories";
          button.hidden = false;
        } else {
          button.hidden = true;
        }

        /*
         * Smooth reveal for first newly added item.
         */
        const firstNew =
          state.gallery.allItems[
            state.gallery.allItems.length - photos.length
          ];

        if (firstNew) {
          firstNew.classList.add("gallery-item--just-revealed");
          window.setTimeout(() => {
            firstNew.classList.remove(
              "gallery-item--just-revealed"
            );
          }, 500);
        }
      })
      .catch((error) => {
        console.error("[Gallery] Load More failed:", error);
        button.disabled = false;
        button.textContent = "Load More Memories";
      });
  }

  /* ==========================================================================
     CARD BUILDER — builds a gallery-item <article> from JSON photo data
     ========================================================================== */

  function escapeAttr(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function buildPhotoCard(photo, indexInGrid) {
    const article = document.createElement("article");
    article.className = "gallery-item";
    article.dataset.photoId = photo.id;

    const imgHtml = photo.image_url
      ? `<img
           src="${escapeAttr(photo.image_url)}"
           alt="${escapeAttr(photo.alt_text || photo.title)}"
           loading="lazy"
           decoding="async"
           draggable="false"
         >`
      : "";

    const captionHtml = photo.caption
      ? `<p class="gallery-item-caption">${escapeHtml(photo.caption)}</p>`
      : "";

    const dateHtml = photo.event_date
      ? `<span class="gallery-item-date">${escapeHtml(photo.event_date)}</span>`
      : "";

    article.innerHTML = `
      <button
        type="button"
        class="gallery-image-button"
        data-photo-id="${escapeAttr(photo.id)}"
        data-image="${escapeAttr(photo.image_url)}"
        data-title="${escapeAttr(photo.title)}"
        data-caption="${escapeAttr(photo.caption)}"
        data-category-name="${escapeAttr(photo.category_name)}"
        data-date="${escapeAttr(photo.event_date)}"
        aria-label="Open ${escapeAttr(photo.title)} in fullscreen viewer"
      >
        ${imgHtml}
      </button>
      <div class="gallery-item-content">
        <span class="gallery-item-category">${escapeHtml(photo.category_name)}</span>
        <h3 class="gallery-item-title">${escapeHtml(photo.title)}</h3>
        ${captionHtml}
        ${dateHtml}
      </div>
    `;

    return article;
  }

  /* ==========================================================================
     CANONICAL PHOTO DATA
     ========================================================================== */

  function getGalleryButtonFromItem(item) {
    if (!item) {
      return null;
    }

    return item.querySelector(
      CONFIG.SELECTORS.galleryImageButton
    );
  }

  function buildPhotoData(button) {
    if (!button) {
      return null;
    }

    const id =
      normalizeId(
        getDatasetValue(
          button,
          "photoId"
        )
      );

    const src =
      getDatasetValue(
        button,
        "image"
      );

    if (!id || !src) {
      return null;
    }

    const title =
      getDatasetValue(
        button,
        "title"
      );

    const category =
      getDatasetValue(
        button,
        "categoryName"
      );

    const date =
      getDatasetValue(
        button,
        "date"
      );

    const caption =
      getDatasetValue(
        button,
        "caption"
      );

    return {
      /*
       * Stable DB identity
       */
      id,

      /*
       * VerticalThumbnailViewer canonical source
       */
      src,

      /*
       * Metadata
       */
      title:
        title || "Memory",

      category:
        category || "Memory",

      date,

      caption,

      description:
        caption,

      /*
       * Compatibility aliases.
       *
       * Harmless if viewer ignores them.
       */
      image: src,
      imageUrl: src,
      alt:
        title || "Memory",
    };
  }

  /* ==========================================================================
     GET CURRENT VISIBLE PHOTOS
     ========================================================================== */

  function getVisibleGalleryPayload() {
    const grid =
      state.gallery.grid;

    if (!grid) {
      return [];
    }

    /*
     * IMPORTANT:
     *
     * :not([hidden]) must be checked on .gallery-item,
     * not simply on buttons.
     */

    const visibleItems = toArray(
      grid.querySelectorAll(
        `${CONFIG.SELECTORS.galleryItem}:not([hidden])`
      )
    );

    const payload = [];

    visibleItems.forEach((item) => {
      const button =
        getGalleryButtonFromItem(
          item
        );

      const data =
        buildPhotoData(button);

      if (data) {
        payload.push(data);
      }
    });

    return payload;
  }

  /* ==========================================================================
     GALLERY CLICK
     ========================================================================== */

  function handleGalleryGridClick(event) {
    /*
     * ONLY actual image button opens viewer.
     *
     * The old:
     *
     * e.target.closest('[data-photo-id]')
     *
     * could match <article data-photo-id>
     * when users click metadata.
     *
     * That is removed.
     */

    const button =
      event.target.closest(
        CONFIG.SELECTORS.galleryImageButton
      );

    if (!button) {
      return;
    }

    const grid =
      state.gallery.grid;

    if (
      !grid ||
      !grid.contains(button)
    ) {
      return;
    }

    event.preventDefault();

    openGalleryPhoto(button);
  }

  function handleGalleryGridKeyboard(event) {
    if (
      event.key !== "Enter" &&
      event.key !== " "
    ) {
      return;
    }

    const button =
      event.target.closest(
        CONFIG.SELECTORS.galleryImageButton
      );

    if (!button) {
      return;
    }

    /*
     * Native buttons already fire click on Enter/Space.
     *
     * Do not trigger manually or it opens twice.
     */
  }

  /* ==========================================================================
     INITIALIZE VERTICAL VIEWER
     ========================================================================== */

  function initGalleryViewer() {
    if (
      typeof window.VerticalThumbnailViewer !==
      "function"
    ) {
      console.error(
        "[Gallery] VerticalThumbnailViewer is unavailable. " +
        "Check that vertical-viewer.js loads before gallery.js."
      );

      return;
    }

    try {
      state.gallery.viewer =
        new window.VerticalThumbnailViewer({
          overlay:
            CONFIG.SELECTORS.lightbox,

          shell:
            CONFIG.SELECTORS.lightboxShell,

          stage:
            CONFIG.SELECTORS.lightboxStage,

          img:
            CONFIG.SELECTORS.lightboxImage,

          blur:
            CONFIG.SELECTORS.lightboxBlur,

          thumbStrip:
            CONFIG.SELECTORS.lightboxThumbs,

          title:
            CONFIG.SELECTORS.lightboxTitle,

          category:
            CONFIG.SELECTORS.lightboxCategory,

          date:
            CONFIG.SELECTORS.lightboxDate,

          description:
            CONFIG.SELECTORS.lightboxDescription,

          counter:
            CONFIG.SELECTORS.lightboxCounter,

          prevBtn:
            CONFIG.SELECTORS.lightboxPrevious,

          nextBtn:
            CONFIG.SELECTORS.lightboxNext,

          closeBtn:
            CONFIG.SELECTORS.lightboxClose,

          /*
           * Do not auto-open any image.
           *
           * Viewer starts only after explicit user action.
           */
          autostart: false,
        });

      state.gallery.viewerReady =
        Boolean(
          state.gallery.viewer
        );

      console.info(
        "[Gallery] Vertical photo viewer ready."
      );
    } catch (error) {
      state.gallery.viewer = null;
      state.gallery.viewerReady = false;

      console.error(
        "[Gallery] Viewer initialization failed:",
        error
      );
    }
  }

  /* ==========================================================================
     OPEN PHOTO
     ========================================================================== */

  function openGalleryPhoto(button) {
    if (
      state.gallery.opening
    ) {
      return;
    }

    const clickedId =
      normalizeId(
        getDatasetValue(
          button,
          "photoId"
        )
      );

    if (!clickedId) {
      console.warn(
        "[Gallery] Clicked photo has no data-photo-id."
      );

      return;
    }

    const items =
      getVisibleGalleryPayload();

    if (!items.length) {
      console.warn(
        "[Gallery] No visible gallery images available."
      );

      return;
    }

    const clickedIndex =
      items.findIndex(
        (item) =>
          normalizeId(item.id) ===
          clickedId
      );

    if (
      clickedIndex < 0
    ) {
      console.warn(
        `[Gallery] Photo ID ${clickedId} is not part of the current visible payload.`
      );

      return;
    }

    if (
      !ensureViewerReady()
    ) {
      return;
    }

    state.gallery.opening = true;

    try {
      const viewer =
        state.gallery.viewer;

      /*
       * Primary contract used by your current viewer:
       *
       * viewer.open(index, items)
       */

      if (
        typeof viewer.open ===
        "function"
      ) {
        viewer.open(
          clickedIndex,
          items
        );
      } else {
        throw new Error(
          "VerticalThumbnailViewer does not expose an open() method."
        );
      }
    } catch (error) {
      console.error(
        "[Gallery] Failed to open viewer:",
        error
      );
    } finally {
      /*
       * Small lock avoids accidental double click,
       * but never makes the UI feel delayed.
       */

      window.setTimeout(() => {
        state.gallery.opening =
          false;
      }, 180);
    }
  }

  /* ==========================================================================
     VIEWER HEALTH / REINITIALIZATION
     ========================================================================== */

  function ensureViewerReady() {
    if (
      state.gallery.viewer &&
      typeof state.gallery.viewer.open ===
        "function"
    ) {
      return true;
    }

    /*
     * Try one safe reconstruction.
     */

    state.gallery.viewerReady =
      false;

    initGalleryViewer();

    if (
      state.gallery.viewer &&
      typeof state.gallery.viewer.open ===
        "function"
    ) {
      return true;
    }

    console.error(
      "[Gallery] Viewer could not be initialized."
    );

    return false;
  }

  /* ==========================================================================
     SELECTED MEMORIES
     ========================================================================== */

  function initSelectedMemories() {
    const track =
      document.querySelector(
        CONFIG.SELECTORS.selectedTrack
      );

    if (!track) {
      return;
    }

    const items =
      toArray(
        track.querySelectorAll(
          CONFIG.SELECTORS.selectedItem
        )
      );

    if (!items.length) {
      return;
    }

    state.selectedMemories.track =
      track;

    state.selectedMemories.items =
      items;

    /*
     * Respect server-rendered initial active item.
     */

    const initialIndex =
      items.findIndex((item) =>
        item.classList.contains(
          "is-active"
        )
      );

    state.selectedMemories.activeIndex =
      initialIndex >= 0
        ? initialIndex
        : 0;

    setSelectedMemoryActive(
      state.selectedMemories.activeIndex,
      {
        focus: false,
        scroll: false,
      }
    );

    /*
     * Delegated events.
     */

    track.addEventListener(
      "click",
      handleSelectedMemoryClick
    );

    track.addEventListener(
      "keydown",
      handleSelectedMemoryKeyboard
    );

    initSelectedMemoriesTouchGesture(track);
    initSelectedMemoriesBorderGlow(items);
  }

  /* ==========================================================================
     SELECTED MEMORIES TOUCH / SWIPE GESTURE SUPPORT
     ========================================================================== */

  function initSelectedMemoriesTouchGesture(track) {
    if (!track) return;

    let touchStartX = 0;
    let touchStartY = 0;
    let touchStartTime = 0;
    let isTracking = false;

    track.addEventListener(
      "touchstart",
      (event) => {
        if (event.touches.length !== 1) return;
        const touch = event.touches[0];
        touchStartX = touch.clientX;
        touchStartY = touch.clientY;
        touchStartTime = Date.now();
        isTracking = true;
      },
      { passive: true }
    );

    track.addEventListener(
      "touchend",
      (event) => {
        if (!isTracking) return;
        isTracking = false;

        const touch = event.changedTouches[0];
        if (!touch) return;

        const deltaX = touch.clientX - touchStartX;
        const deltaY = touch.clientY - touchStartY;
        const duration = Date.now() - touchStartTime;

        // Verify gesture is predominantly horizontal
        const isHorizontal = Math.abs(deltaX) > Math.abs(deltaY) * 1.25;
        const isFastSwipe = duration < 350 && Math.abs(deltaX) > 28;
        const isLongSwipe = Math.abs(deltaX) > 55;

        if (isHorizontal && (isFastSwipe || isLongSwipe)) {
          const currentIndex = state.selectedMemories.activeIndex;
          const total = state.selectedMemories.items.length;

          if (deltaX < 0) {
            // Swipe left -> advance to next card
            const nextIndex = Math.min(total - 1, currentIndex + 1);
            if (nextIndex !== currentIndex) {
              setSelectedMemoryActive(nextIndex, {
                focus: false,
                scroll: true,
              });
            }
          } else {
            // Swipe right -> return to previous card
            const prevIndex = Math.max(0, currentIndex - 1);
            if (prevIndex !== currentIndex) {
              setSelectedMemoryActive(prevIndex, {
                focus: false,
                scroll: true,
              });
            }
          }
        }
      },
      { passive: true }
    );
  }

  /* ==========================================================================
     SELECTED MEMORY CURSOR EDGE BORDER GLOW
     ========================================================================== */

  function initSelectedMemoriesBorderGlow(items) {
    if (!items || !items.length) return;
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;

    items.forEach((item) => {
      let rafId = null;

      function onPointerMove(event) {
        if (rafId) return;

        rafId = requestAnimationFrame(() => {
          rafId = null;

          const rect = item.getBoundingClientRect();
          if (!rect.width || !rect.height) return;

          const x = event.clientX - rect.left;
          const y = event.clientY - rect.top;

          const centerX = rect.width / 2;
          const centerY = rect.height / 2;

          // 1. Cursor angle from center to pointer
          const rad = Math.atan2(y - centerY, x - centerX);
          const deg = (rad * (180 / Math.PI) + 90 + 360) % 360;

          // 2. Proximity to nearest card edge
          const distLeft = x;
          const distRight = rect.width - x;
          const distTop = y;
          const distBottom = rect.height - y;

          const minDistToEdge = Math.min(distLeft, distRight, distTop, distBottom);
          const threshold = Math.min(65, Math.min(rect.width, rect.height) * 0.35);

          let proximity = 0;
          if (minDistToEdge < threshold) {
            proximity = Math.max(0, 1 - minDistToEdge / threshold);
          }

          item.style.setProperty("--sm-cursor-angle", `${deg.toFixed(1)}deg`);
          item.style.setProperty("--sm-edge-proximity", proximity.toFixed(3));
          item.style.setProperty("--sm-glow-opacity", "1");
        });
      }

      function onPointerEnter() {
        item.style.setProperty("--sm-glow-opacity", "1");
      }

      function onPointerLeave() {
        if (rafId) {
          cancelAnimationFrame(rafId);
          rafId = null;
        }
        item.style.setProperty("--sm-glow-opacity", "0");
        item.style.setProperty("--sm-edge-proximity", "0");
      }

      item.addEventListener("pointermove", onPointerMove, { passive: true });
      item.addEventListener("pointerenter", onPointerEnter, { passive: true });
      item.addEventListener("pointerleave", onPointerLeave, { passive: true });
    });
  }

  /* ==========================================================================
     SELECTED MEMORY ACTIVE STATE
     ========================================================================== */

  function setSelectedMemoryActive(
    index,
    options = {}
  ) {
    const items =
      state.selectedMemories.items;

    if (!items.length) {
      return;
    }

    const safeIndex =
      clamp(
        index,
        0,
        items.length - 1
      );

    state.selectedMemories.activeIndex =
      safeIndex;

    items.forEach(
      (item, itemIndex) => {
        const active =
          itemIndex ===
          safeIndex;

        item.classList.toggle(
          "is-active",
          active
        );

        item.setAttribute(
          "aria-expanded",
          active
            ? "true"
            : "false"
        );

        if (active) {
          item.setAttribute(
            "aria-current",
            "true"
          );
        } else {
          item.removeAttribute(
            "aria-current"
          );
        }
      }
    );

    const activeItem =
      items[safeIndex];

    if (
      options.focus &&
      activeItem
    ) {
      activeItem.focus({
        preventScroll: true,
      });
    }

    if (
      options.scroll &&
      activeItem
    ) {
      scrollSelectedMemoryIntoView(
        activeItem
      );
    }
  }

  /* ==========================================================================
     SELECTED MEMORY CLICK
     ========================================================================== */

  function handleSelectedMemoryClick(event) {
    const item =
      event.target.closest(
        CONFIG.SELECTORS.selectedItem
      );

    if (
      !item ||
      !state.selectedMemories.track.contains(
        item
      )
    ) {
      return;
    }

    const index =
      state.selectedMemories.items.indexOf(
        item
      );

    if (index < 0) {
      return;
    }

    setSelectedMemoryActive(
      index,
      {
        focus: false,
        scroll: true,
      }
    );
  }

  /* ==========================================================================
     SELECTED MEMORY KEYBOARD
     ========================================================================== */

  function handleSelectedMemoryKeyboard(event) {
    const item =
      event.target.closest(
        CONFIG.SELECTORS.selectedItem
      );

    if (!item) {
      return;
    }

    const currentIndex =
      state.selectedMemories.items.indexOf(
        item
      );

    if (currentIndex < 0) {
      return;
    }

    switch (event.key) {
      case "Enter":
      case " ":
        event.preventDefault();

        setSelectedMemoryActive(
          currentIndex,
          {
            focus: true,
            scroll: true,
          }
        );

        break;

      case "ArrowLeft":
        event.preventDefault();

        setSelectedMemoryActive(
          Math.max(
            0,
            currentIndex - 1
          ),
          {
            focus: true,
            scroll: true,
          }
        );

        break;

      case "ArrowRight":
        event.preventDefault();

        setSelectedMemoryActive(
          Math.min(
            state.selectedMemories.items.length -
              1,

            currentIndex + 1
          ),
          {
            focus: true,
            scroll: true,
          }
        );

        break;

      case "Home":
        event.preventDefault();

        setSelectedMemoryActive(
          0,
          {
            focus: true,
            scroll: true,
          }
        );

        break;

      case "End":
        event.preventDefault();

        setSelectedMemoryActive(
          state.selectedMemories.items.length -
            1,
          {
            focus: true,
            scroll: true,
          }
        );

        break;
    }
  }

  /* ==========================================================================
     SELECTED MEMORY SCROLL
     ========================================================================== */

  function scrollSelectedMemoryIntoView(
    item
  ) {
    if (
      !item ||
      typeof item.scrollIntoView !==
        "function"
    ) {
      return;
    }

    const reducedMotion =
      window.matchMedia(
        "(prefers-reduced-motion: reduce)"
      ).matches;

    item.scrollIntoView({
      behavior:
        reducedMotion
          ? "auto"
          : "smooth",

      block:
        "nearest",

      inline:
        "center",
    });
  }

  /* ==========================================================================
     OPTIONAL MEDIA ERROR SAFETY
     ========================================================================== */

  document.addEventListener(
    "error",
    (event) => {
      const image =
        event.target;

      if (
        !(image instanceof HTMLImageElement)
      ) {
        return;
      }

      const isGalleryImage =
        image.closest(
          CONFIG.SELECTORS.galleryGrid
        ) ||
        image.closest(
          CONFIG.SELECTORS.selectedTrack
        );

      if (!isGalleryImage) {
        return;
      }

      image.classList.add(
        "gallery-image-error"
      );

      console.warn(
        "[Gallery] Image failed to load:",
        image.currentSrc ||
          image.src
      );
    },
    true
  );

})();