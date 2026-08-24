/**
 * ============================================================================
 * COLLEGE MEMORIES '26
 * VERTICAL THUMBNAIL VIEWER — FINAL STABLE REPLACEMENT
 * ============================================================================
 *
 * FEATURES
 * ---------------------------------------------------------------------------
 * ✓ viewer.open(index, itemsPayload)
 * ✓ Infinite circular navigation
 * ✓ Previous / Next buttons
 * ✓ Keyboard arrows
 * ✓ ESC close
 * ✓ Thumbnail navigation
 * ✓ Mouse drag
 * ✓ Touch / pointer swipe
 * ✓ Swipe velocity detection
 * ✓ No overlapping setTimeout image swaps
 * ✓ No autoplay fighting user input
 * ✓ Preloads previous + next images
 * ✓ Decodes image before reveal when supported
 * ✓ Metadata stays synchronized
 * ✓ Correct counter
 * ✓ Correct aspect-ratio classification
 * ✓ Portrait ambient blurred backdrop
 * ✓ Body scroll lock
 * ✓ Focus restoration
 * ✓ Reopen-safe
 * ✓ Rapid-click safe
 * ✓ Rapid-swipe safe
 * ✓ Reduced-motion support
 * ✓ No React / dependency required
 * ============================================================================
 */

window.VerticalThumbnailViewer =
  class VerticalThumbnailViewer {
    constructor(config = {}) {
      /* ======================================================================
         DOM REFERENCES
         ====================================================================== */

      this.overlayEl =
        this.resolveElement(config.overlay);

      this.shellEl =
        this.resolveElement(config.shell);

      this.stageEl =
        this.resolveElement(config.stage);

      this.imgEl =
        this.resolveElement(config.img);

      this.blurEl =
        this.resolveElement(config.blur);

      this.thumbStripEl =
        this.resolveElement(
          config.thumbStrip
        );

      this.titleEl =
        this.resolveElement(config.title);

      this.categoryEl =
        this.resolveElement(
          config.category
        );

      this.dateEl =
        this.resolveElement(config.date);

      this.descriptionEl =
        this.resolveElement(
          config.description
        );

      this.counterEl =
        this.resolveElement(
          config.counter
        );

      this.prevBtn =
        this.resolveElement(config.prevBtn);

      this.nextBtn =
        this.resolveElement(config.nextBtn);

      this.closeBtn =
        this.resolveElement(
          config.closeBtn
        );

      /* ======================================================================
         CONFIG
         ====================================================================== */

      this.getItems =
        typeof config.getItems ===
        "function"
          ? config.getItems
          : null;

      this.bodyLockClass =
        config.bodyLockClass ||
        "viewer-open";

      /*
       * Keep supported for compatibility,
       * but autoplay is OFF by default.
       */
      this.autostart =
        config.autostart === true;

      this.autoplayDelay =
        Number(config.autoplayDelay) >
        0
          ? Number(config.autoplayDelay)
          : 5000;

      /* ======================================================================
         STATE
         ====================================================================== */

      this.items = [];

      this.thumbs = [];

      this.currentIndex = 0;

      this.isOpen = false;

      this.destroyed = false;

      this.transitionToken = 0;

      this.navigationLocked = false;

      this.navigationUnlockTimer =
        null;

      this.autoplayTimer = null;

      this.lastFocusedElement = null;

      /* ======================================================================
         SWIPE STATE
         ====================================================================== */

      this.pointerActive = false;

      this.pointerId = null;

      this.pointerStartX = 0;

      this.pointerStartY = 0;

      this.pointerCurrentX = 0;

      this.pointerCurrentY = 0;

      this.pointerStartedAt = 0;

      this.pointerAxis = null;

      this.pointerSamples = [];

      this.dragOffsetX = 0;

      this.suppressClickUntil = 0;

      /* ======================================================================
         CONSTANTS
         ====================================================================== */

      this.AXIS_LOCK_THRESHOLD = 7;

      this.SWIPE_DISTANCE = 52;

      this.SWIPE_VELOCITY = 0.34;

      this.MAX_DRAG_VISUAL = 110;

      /* ======================================================================
         REDUCED MOTION
         ====================================================================== */

      this.reducedMotionQuery =
        window.matchMedia
          ? window.matchMedia(
              "(prefers-reduced-motion: reduce)"
            )
          : null;

      this.bindEvents();
    }

    /* ========================================================================
       ELEMENT RESOLVER
       ======================================================================== */

    resolveElement(value) {
      if (!value) {
        return null;
      }

      if (
        typeof value === "string"
      ) {
        return document.querySelector(
          value
        );
      }

      return value;
    }

    /* ========================================================================
       REDUCED MOTION
       ======================================================================== */

    prefersReducedMotion() {
      return Boolean(
        this.reducedMotionQuery?.matches
      );
    }

    /* ========================================================================
       OPEN
       ======================================================================== */

    open(
      index = 0,
      itemsPayload = null
    ) {
      if (this.destroyed) {
        return;
      }

      if (!this.overlayEl) {
        console.error(
          "[VerticalThumbnailViewer] Overlay element not found."
        );
        return;
      }

      /*
       * Obtain items.
       */

      if (
        Array.isArray(itemsPayload) &&
        itemsPayload.length
      ) {
        this.items =
          this.normalizeItems(
            itemsPayload
          );
      } else if (this.getItems) {
        const resolvedItems =
          this.getItems() || [];

        this.items =
          this.normalizeItems(
            resolvedItems
          );
      }

      if (!this.items.length) {
        console.warn(
          "[VerticalThumbnailViewer] No items available."
        );
        return;
      }

      let safeIndex =
        Number(index);

      if (
        !Number.isFinite(
          safeIndex
        )
      ) {
        safeIndex = 0;
      }

      safeIndex =
        this.normalizeIndex(
          safeIndex
        );

      this.lastFocusedElement =
        document.activeElement instanceof
        HTMLElement
          ? document.activeElement
          : null;

      this.currentIndex =
        safeIndex;

      /*
       * Build thumbnails only once for
       * current payload.
       */

      this.buildThumbnails();

      /*
       * Render BEFORE showing overlay.
       */

      this.renderCurrent({
        immediate: true,
      });

      this.overlayEl.classList.add(
        "active"
      );

      this.overlayEl.setAttribute(
        "aria-hidden",
        "false"
      );

      document.body.classList.add(
        this.bodyLockClass
      );

      this.isOpen = true;

      this.preloadAround(
        this.currentIndex
      );

      if (
        this.autostart &&
        !this.prefersReducedMotion()
      ) {
        this.startAutoplay();
      }

      window.setTimeout(() => {
        this.closeBtn?.focus({
          preventScroll: true,
        });
      }, 80);
    }

    /* ========================================================================
       CLOSE
       ======================================================================== */

    close() {
      if (!this.isOpen) {
        return;
      }

      this.isOpen = false;

      this.stopAutoplay();

      this.transitionToken += 1;

      this.resetDragVisual();

      this.overlayEl?.classList.remove(
        "active"
      );

      this.overlayEl?.setAttribute(
        "aria-hidden",
        "true"
      );

      document.body.classList.remove(
        this.bodyLockClass
      );

      if (
        this.lastFocusedElement &&
        document.contains(
          this.lastFocusedElement
        )
      ) {
        try {
          this.lastFocusedElement.focus({
            preventScroll: true,
          });
        } catch (_) {}
      }
    }

    /* ========================================================================
       NORMALIZE ITEMS
       ======================================================================== */

    normalizeItems(items) {
      return items
        .map((item, index) => {
          if (!item) {
            return null;
          }

          const src =
            String(
              item.src ||
                item.image ||
                item.imageUrl ||
                ""
            ).trim();

          if (!src) {
            return null;
          }

          return {
            id:
              String(
                item.id ??
                  index
              ),

            src,

            title:
              String(
                item.title ||
                  "Memory"
              ),

            category:
              String(
                item.category ||
                  "Memory"
              ),

            date:
              String(
                item.date ||
                  ""
              ),

            description:
              String(
                item.description ||
                  item.caption ||
                  ""
              ),

            caption:
              String(
                item.caption ||
                  item.description ||
                  ""
              ),

            alt:
              String(
                item.alt ||
                  item.title ||
                  "Gallery Photograph"
              ),
          };
        })
        .filter(Boolean);
    }

    /* ========================================================================
       INDEX NORMALIZATION
       ======================================================================== */

    normalizeIndex(index) {
      if (!this.items.length) {
        return 0;
      }

      return (
        (index %
          this.items.length +
          this.items.length) %
        this.items.length
      );
    }

    /* ========================================================================
       THUMBNAILS
       ======================================================================== */

    buildThumbnails() {
      if (!this.thumbStripEl) {
        return;
      }

      this.thumbStripEl.innerHTML =
        "";

      this.thumbs = [];

      const fragment =
        document.createDocumentFragment();

      this.items.forEach(
        (item, index) => {
          const thumb =
            document.createElement(
              "button"
            );

          thumb.type = "button";

          thumb.className =
            "vertical-viewer-thumb";

          thumb.dataset.index =
            String(index);

          thumb.setAttribute(
            "aria-label",
            `View photo ${
              index + 1
            }: ${item.title}`
          );

          const image =
            document.createElement(
              "img"
            );

          image.className =
            "vertical-viewer-thumb-img";

          image.src = item.src;

          image.alt = "";

          image.loading =
            index <= 4
              ? "eager"
              : "lazy";

          image.decoding =
            "async";

          thumb.appendChild(
            image
          );

          fragment.appendChild(
            thumb
          );

          this.thumbs.push(
            thumb
          );
        }
      );

      this.thumbStripEl.appendChild(
        fragment
      );

      this.updateThumbnailState();
    }

    /* ========================================================================
       THUMBNAIL STATE
       ======================================================================== */

    updateThumbnailState() {
      this.thumbs.forEach(
        (thumb, index) => {
          const active =
            index ===
            this.currentIndex;

          thumb.classList.toggle(
            "active",
            active
          );

          if (active) {
            thumb.setAttribute(
              "aria-current",
              "true"
            );
          } else {
            thumb.removeAttribute(
              "aria-current"
            );
          }
        }
      );

      const activeThumb =
        this.thumbs[
          this.currentIndex
        ];

      if (
        !activeThumb ||
        typeof activeThumb.scrollIntoView !==
          "function"
      ) {
        return;
      }

      try {
        activeThumb.scrollIntoView({
          behavior:
            this.prefersReducedMotion()
              ? "auto"
              : "smooth",

          block: "nearest",

          inline: "center",
        });
      } catch (_) {}
    }

    /* ========================================================================
       NAVIGATION
       ======================================================================== */

    goTo(
      index,
      options = {}
    ) {
      if (
        !this.items.length ||
        !this.isOpen
      ) {
        return;
      }

      const targetIndex =
        this.normalizeIndex(
          Number(index)
        );

      if (
        targetIndex ===
          this.currentIndex &&
        !options.force
      ) {
        return;
      }

      this.stopAutoplay();

      const previousIndex =
        this.currentIndex;

      this.currentIndex =
        targetIndex;

      const direction =
        options.direction ||
        this.calculateDirection(
          previousIndex,
          targetIndex
        );

      this.renderCurrent({
        immediate: false,
        direction,
      });

      this.preloadAround(
        targetIndex
      );

      if (this.autostart) {
        this.scheduleAutoplayResume();
      }
    }

    next() {
      this.goTo(
        this.currentIndex + 1,
        {
          direction: "next",
        }
      );
    }

    prev() {
      this.goTo(
        this.currentIndex - 1,
        {
          direction: "prev",
        }
      );
    }

    calculateDirection(
      previousIndex,
      nextIndex
    ) {
      if (
        previousIndex ===
        nextIndex
      ) {
        return "next";
      }

      const forward =
        this.normalizeIndex(
          nextIndex -
            previousIndex
        );

      const backward =
        this.normalizeIndex(
          previousIndex -
            nextIndex
        );

      return forward <= backward
        ? "next"
        : "prev";
    }

    /* ========================================================================
       MAIN RENDER
       ======================================================================== */

    renderCurrent({
      immediate = false,
      direction = "next",
    } = {}) {
      const item =
        this.items[
          this.currentIndex
        ];

      if (!item) {
        return;
      }

      /*
       * Metadata changes immediately.
       */

      this.updateMetadata(item);

      this.updateCounter();

      this.updateThumbnailState();

      this.updateAmbientBackdrop(
        item.src
      );

      /*
       * Image transition.
       */

      if (this.imgEl) {
        this.transitionImage(
          item,
          {
            immediate,
            direction,
          }
        );
      }
    }

    /* ========================================================================
       IMAGE TRANSITION
       ======================================================================== */

    async transitionImage(
      item,
      {
        immediate = false,
        direction = "next",
      } = {}
    ) {
      if (!this.imgEl) {
        return;
      }

      const token =
        ++this.transitionToken;

      if (immediate) {
        this.imgEl.src =
          item.src;

        this.imgEl.alt =
          item.alt;

        this.imgEl.style.opacity =
          "1";

        this.imgEl.style.transform =
          "translate3d(0,0,0) scale(1)";

        await this.waitForImage(
          this.imgEl
        );

        if (
          token !==
          this.transitionToken
        ) {
          return;
        }

        this.classifyImage(
          this.imgEl
        );

        return;
      }

      /*
       * Predecode target image without
       * touching current visible image.
       */

      const preload =
        new Image();

      preload.decoding =
        "async";

      preload.src =
        item.src;

      try {
        if (
          typeof preload.decode ===
          "function"
        ) {
          await preload.decode();
        } else {
          await this.waitForImage(
            preload
          );
        }
      } catch (_) {
        /*
         * Browser may reject decode
         * for some cached/cross-origin images.
         */
      }

      if (
        token !==
          this.transitionToken ||
        !this.isOpen
      ) {
        return;
      }

      const reduced =
        this.prefersReducedMotion();

      if (reduced) {
        this.imgEl.src =
          item.src;

        this.imgEl.alt =
          item.alt;

        this.classifyImage(
          this.imgEl
        );

        return;
      }

      const exitX =
        direction === "next"
          ? -22
          : 22;

      const enterX =
        direction === "next"
          ? 22
          : -22;

      /*
       * Cancel any running animation.
       */

      this.imgEl
        .getAnimations?.()
        .forEach((animation) =>
          animation.cancel()
        );

      const exitAnimation =
        this.imgEl.animate(
          [
            {
              opacity: 1,
              transform:
                "translate3d(0,0,0) scale(1)",
            },

            {
              opacity: 0,
              transform:
                `translate3d(${exitX}px,0,0) scale(.985)`,
            },
          ],
          {
            duration: 115,

            easing:
              "cubic-bezier(.4,0,1,1)",

            fill: "forwards",
          }
        );

      try {
        await exitAnimation.finished;
      } catch (_) {}

      if (
        token !==
          this.transitionToken ||
        !this.isOpen
      ) {
        return;
      }

      this.imgEl.src =
        item.src;

      this.imgEl.alt =
        item.alt;

      this.classifyImage(
        this.imgEl
      );

      const enterAnimation =
        this.imgEl.animate(
          [
            {
              opacity: 0,
              transform:
                `translate3d(${enterX}px,0,0) scale(.985)`,
            },

            {
              opacity: 1,
              transform:
                "translate3d(0,0,0) scale(1)",
            },
          ],
          {
            duration: 220,

            easing:
              "cubic-bezier(.16,1,.3,1)",

            fill: "forwards",
          }
        );

      try {
        await enterAnimation.finished;
      } catch (_) {}

      if (
        token ===
        this.transitionToken
      ) {
        this.imgEl.style.opacity =
          "1";

        this.imgEl.style.transform =
          "translate3d(0,0,0) scale(1)";
      }
    }

    /* ========================================================================
       IMAGE LOAD HELPER
       ======================================================================== */

    waitForImage(image) {
      return new Promise(
        (resolve) => {
          if (
            image.complete &&
            image.naturalWidth
          ) {
            resolve();
            return;
          }

          const done = () => {
            image.removeEventListener(
              "load",
              done
            );

            image.removeEventListener(
              "error",
              done
            );

            resolve();
          };

          image.addEventListener(
            "load",
            done,
            {
              once: true,
            }
          );

          image.addEventListener(
            "error",
            done,
            {
              once: true,
            }
          );
        }
      );
    }

    /* ========================================================================
       PRELOAD AROUND CURRENT
       ======================================================================== */

    preloadAround(index) {
      if (
        this.items.length <= 1
      ) {
        return;
      }

      const indexes = [
        this.normalizeIndex(
          index - 2
        ),

        this.normalizeIndex(
          index - 1
        ),

        this.normalizeIndex(
          index + 1
        ),

        this.normalizeIndex(
          index + 2
        ),
      ];

      const unique =
        [...new Set(indexes)];

      unique.forEach(
        (targetIndex) => {
          const item =
            this.items[
              targetIndex
            ];

          if (!item?.src) {
            return;
          }

          const image =
            new Image();

          image.decoding =
            "async";

          image.src =
            item.src;
        }
      );
    }

    /* ========================================================================
       IMAGE CLASSIFICATION
       ======================================================================== */

    classifyImage(image) {
      if (
        !this.stageEl ||
        !image
      ) {
        return;
      }

      const apply =
        () => {
          const width =
            image.naturalWidth ||
            1000;

          const height =
            image.naturalHeight ||
            750;

          const ratio =
            width / height;

          this.stageEl.classList.remove(
            "is-landscape",
            "is-square",
            "is-portrait",
            "is-tall-portrait"
          );

          if (ratio >= 1.25) {
            this.stageEl.classList.add(
              "is-landscape"
            );
          } else if (
            ratio >= 0.88
          ) {
            this.stageEl.classList.add(
              "is-square"
            );
          } else if (
            ratio >= 0.65
          ) {
            this.stageEl.classList.add(
              "is-portrait"
            );
          } else {
            this.stageEl.classList.add(
              "is-tall-portrait"
            );
          }

          this.stageEl.style.setProperty(
            "--active-image-ratio",
            `${width} / ${height}`
          );
        };

      if (
        image.complete &&
        image.naturalWidth
      ) {
        apply();
      } else {
        image.addEventListener(
          "load",
          apply,
          {
            once: true,
          }
        );
      }
    }

    /* ========================================================================
       METADATA
       ======================================================================== */

    updateMetadata(item) {
      if (this.titleEl) {
        this.titleEl.textContent =
          item.title || "";
      }

      if (this.categoryEl) {
        this.categoryEl.textContent =
          item.category ||
          "Memory";
      }

      if (this.dateEl) {
        this.dateEl.textContent =
          item.date || "";
      }

      if (this.descriptionEl) {
        this.descriptionEl.textContent =
          item.description ||
          item.caption ||
          "";
      }
    }

    /* ========================================================================
       COUNTER
       ======================================================================== */

    updateCounter() {
      if (!this.counterEl) {
        return;
      }

      const current =
        String(
          this.currentIndex + 1
        ).padStart(2, "0");

      const total =
        String(
          this.items.length
        ).padStart(2, "0");

      this.counterEl.textContent =
        `${current} / ${total}`;
    }

    /* ========================================================================
       AMBIENT BACKDROP
       ======================================================================== */

    updateAmbientBackdrop(src) {
      if (!this.blurEl) {
        return;
      }

      /*
       * CSS variable is safer than
       * interpolating url('...') manually.
       */

      this.blurEl.style.backgroundImage =
        `url("${String(src).replaceAll(
          '"',
          '\\"'
        )}")`;
    }

    /* ========================================================================
       POINTER SAMPLES
       ======================================================================== */

    pushPointerSample(x) {
      const now =
        performance.now();

      this.pointerSamples.push({
        x,
        time: now,
      });

      this.pointerSamples =
        this.pointerSamples.filter(
          (sample) =>
            now -
              sample.time <=
            110
        );

      if (
        this.pointerSamples.length >
        6
      ) {
        this.pointerSamples.shift();
      }
    }

    getPointerVelocity() {
      if (
        this.pointerSamples.length <
        2
      ) {
        return 0;
      }

      const first =
        this.pointerSamples[0];

      const last =
        this.pointerSamples[
          this.pointerSamples.length -
            1
        ];

      return (
        (last.x - first.x) /
        Math.max(
          1,
          last.time -
            first.time
        )
      );
    }

    /* ========================================================================
       DRAG VISUAL
       ======================================================================== */

    applyDragVisual(dx) {
      if (!this.imgEl) {
        return;
      }

      const resisted =
        Math.max(
          -this.MAX_DRAG_VISUAL,
          Math.min(
            this.MAX_DRAG_VISUAL,
            dx * 0.32
          )
        );

      this.dragOffsetX =
        resisted;

      this.imgEl.style.transition =
        "none";

      this.imgEl.style.transform =
        `translate3d(${resisted}px,0,0) scale(.992)`;

      this.imgEl.style.opacity =
        String(
          Math.max(
            0.72,
            1 -
              Math.abs(
                resisted
              ) /
                300
          )
        );
    }

    resetDragVisual({
      animate = true,
    } = {}) {
      if (!this.imgEl) {
        return;
      }

      this.dragOffsetX = 0;

      if (
        animate &&
        !this.prefersReducedMotion()
      ) {
        this.imgEl.style.transition =
          "transform 220ms cubic-bezier(.16,1,.3,1), opacity 180ms ease";
      } else {
        this.imgEl.style.transition =
          "none";
      }

      this.imgEl.style.transform =
        "translate3d(0,0,0) scale(1)";

      this.imgEl.style.opacity =
        "1";
    }

    /* ========================================================================
       POINTER EVENTS
       ======================================================================== */

    handlePointerDown(event) {
      if (
        !this.isOpen ||
        event.button > 0
      ) {
        return;
      }

      if (
        event.target.closest(
          "button, a, input, textarea, select"
        )
      ) {
        return;
      }

      this.pointerActive = true;

      this.pointerId =
        event.pointerId;

      this.pointerStartX =
        event.clientX;

      this.pointerStartY =
        event.clientY;

      this.pointerCurrentX =
        event.clientX;

      this.pointerCurrentY =
        event.clientY;

      this.pointerStartedAt =
        performance.now();

      this.pointerAxis = null;

      this.pointerSamples = [];

      this.pushPointerSample(
        event.clientX
      );

      this.stopAutoplay();

      try {
        this.stageEl?.setPointerCapture(
          event.pointerId
        );
      } catch (_) {}
    }

    handlePointerMove(event) {
      if (
        !this.pointerActive ||
        event.pointerId !==
          this.pointerId
      ) {
        return;
      }

      this.pointerCurrentX =
        event.clientX;

      this.pointerCurrentY =
        event.clientY;

      const dx =
        this.pointerCurrentX -
        this.pointerStartX;

      const dy =
        this.pointerCurrentY -
        this.pointerStartY;

      if (!this.pointerAxis) {
        if (
          Math.abs(dx) >
            this.AXIS_LOCK_THRESHOLD ||
          Math.abs(dy) >
            this.AXIS_LOCK_THRESHOLD
        ) {
          this.pointerAxis =
            Math.abs(dx) >
            Math.abs(dy)
              ? "x"
              : "y";
        }
      }

      if (
        this.pointerAxis !== "x"
      ) {
        return;
      }

      event.preventDefault();

      this.pushPointerSample(
        event.clientX
      );

      this.applyDragVisual(
        dx
      );
    }

    handlePointerUp(event) {
      if (
        !this.pointerActive
      ) {
        return;
      }

      if (
        this.pointerId !== null &&
        event.pointerId !==
          this.pointerId
      ) {
        return;
      }

      try {
        this.stageEl?.releasePointerCapture(
          event.pointerId
        );
      } catch (_) {}

      const dx =
        this.pointerCurrentX -
        this.pointerStartX;

      const velocity =
        this.getPointerVelocity();

      const horizontal =
        this.pointerAxis === "x";

      this.pointerActive =
        false;

      this.pointerId = null;

      this.pointerAxis = null;

      this.pointerSamples = [];

      if (!horizontal) {
        this.resetDragVisual();
        return;
      }

      const shouldNavigate =
        Math.abs(dx) >=
          this.SWIPE_DISTANCE ||
        Math.abs(velocity) >=
          this.SWIPE_VELOCITY;

      if (
        Math.abs(dx) > 8
      ) {
        this.suppressClickUntil =
          performance.now() + 180;
      }

      if (!shouldNavigate) {
        this.resetDragVisual();
        return;
      }

      /*
       * Reset immediately because
       * transitionImage owns the
       * actual next transition.
       */

      this.resetDragVisual({
        animate: false,
      });

      if (dx < 0) {
        this.next();
      } else {
        this.prev();
      }
    }

    /* ========================================================================
       AUTOPLAY
       ======================================================================== */

    startAutoplay() {
      this.stopAutoplay();

      if (
        !this.autostart ||
        this.prefersReducedMotion() ||
        this.items.length <= 1 ||
        !this.isOpen
      ) {
        return;
      }

      this.autoplayTimer =
        window.setInterval(() => {
          if (
            !document.hidden &&
            this.isOpen
          ) {
            this.next();
          }
        }, this.autoplayDelay);
    }

    stopAutoplay() {
      if (!this.autoplayTimer) {
        return;
      }

      clearInterval(
        this.autoplayTimer
      );

      this.autoplayTimer = null;
    }

    scheduleAutoplayResume() {
      /*
       * We intentionally do not use
       * multiple resume timers.
       */

      this.stopAutoplay();

      if (
        !this.autostart ||
        this.prefersReducedMotion()
      ) {
        return;
      }

      window.clearTimeout(
        this.autoplayResumeTimer
      );

      this.autoplayResumeTimer =
        window.setTimeout(() => {
          if (this.isOpen) {
            this.startAutoplay();
          }
        }, 3500);
    }

    /* ========================================================================
       EVENT BINDING
       ======================================================================== */

    bindEvents() {
      /* Buttons */

      this.prevBtn?.addEventListener(
        "click",
        (event) => {
          event.preventDefault();

          this.prev();
        }
      );

      this.nextBtn?.addEventListener(
        "click",
        (event) => {
          event.preventDefault();

          this.next();
        }
      );

      this.closeBtn?.addEventListener(
        "click",
        (event) => {
          event.preventDefault();

          this.close();
        }
      );

      /* Thumbnail delegation */

      this.thumbStripEl?.addEventListener(
        "click",
        (event) => {
          const thumb =
            event.target.closest(
              ".vertical-viewer-thumb"
            );

          if (!thumb) {
            return;
          }

          const index =
            Number(
              thumb.dataset.index
            );

          if (
            Number.isFinite(index)
          ) {
            this.goTo(index);
          }
        }
      );

      /* Overlay click */

      this.overlayEl?.addEventListener(
        "click",
        (event) => {
          if (
            performance.now() <
            this.suppressClickUntil
          ) {
            return;
          }

          if (
            event.target ===
              this.overlayEl ||
            event.target.classList.contains(
              "vertical-viewer-overlay"
            )
          ) {
            this.close();
          }
        }
      );

      /* Keyboard */

      document.addEventListener(
        "keydown",
        (event) => {
          if (!this.isOpen) {
            return;
          }

          switch (event.key) {
            case "Escape":
              event.preventDefault();

              this.close();
              break;

            case "ArrowLeft":
            case "ArrowUp":
              event.preventDefault();

              this.prev();
              break;

            case "ArrowRight":
            case "ArrowDown":
              event.preventDefault();

              this.next();
              break;
          }
        }
      );

      /* Pointer swipe */

      if (this.stageEl) {
        /*
         * JS handles horizontal drag.
         * Browser still owns vertical pan.
         */

        this.stageEl.style.touchAction =
          "pan-y";

        this.stageEl.addEventListener(
          "pointerdown",
          (event) =>
            this.handlePointerDown(
              event
            )
        );

        this.stageEl.addEventListener(
          "pointermove",
          (event) =>
            this.handlePointerMove(
              event
            ),
          {
            passive: false,
          }
        );

        this.stageEl.addEventListener(
          "pointerup",
          (event) =>
            this.handlePointerUp(
              event
            )
        );

        this.stageEl.addEventListener(
          "pointercancel",
          (event) =>
            this.handlePointerUp(
              event
            )
        );
      }

      /* Visibility */

      document.addEventListener(
        "visibilitychange",
        () => {
          if (
            document.hidden
          ) {
            this.stopAutoplay();
            return;
          }

          if (
            this.isOpen &&
            this.autostart
          ) {
            this.startAutoplay();
          }
        }
      );
    }

    /* ========================================================================
       DESTROY
       ======================================================================== */

    destroy() {
      this.destroyed = true;

      this.close();

      this.stopAutoplay();

      window.clearTimeout(
        this.autoplayResumeTimer
      );

      window.clearTimeout(
        this.navigationUnlockTimer
      );

      this.items = [];

      this.thumbs = [];
    }
  };