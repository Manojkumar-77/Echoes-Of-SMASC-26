/**
 * ============================================================================
 * COLLEGE MEMORIES '26
 * YEARBOOK — SMOOTH INFINITE CLASS ORBIT
 * ============================================================================
 *
 * FEATURES
 * ---------------------------------------------------------------------------
 * ✓ Django DB JSON connectivity
 * ✓ True infinite left/right carousel
 * ✓ Pointer/touch/mouse drag
 * ✓ Momentum + spring physics
 * ✓ Navigation buttons
 * ✓ Side-card click → center
 * ✓ Center-card / VIEW PROFILE → modal
 * ✓ Search by name / nickname
 * ✓ Modal Previous / Next
 * ✓ Modal swipe left/right
 * ✓ Keyboard arrows
 * ✓ ESC close
 * ✓ Closing modal keeps currently selected profile centered
 * ✓ Desktop popup: photo LEFT + details RIGHT
 * ✓ Mobile responsive
 *
 * NO React / Tailwind / Framer Motion required.
 * Compatible with the Django HTML structure already used.
 * ============================================================================
 */

(() => {
  "use strict";

  /* ==========================================================================
     BOOT
     ========================================================================== */

  const ready = (callback) => {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback, {
        once: true,
      });
    } else {
      callback();
    }
  };

  ready(initYearbook);

  /* ==========================================================================
     MAIN
     ========================================================================== */

  function initYearbook() {
    /* ------------------------------------------------------------------------
       DATA
       ------------------------------------------------------------------------ */

    const dataElement = document.getElementById(
      "yearbook-student-data"
    );

    if (!dataElement) {
      console.error(
        "[Yearbook] #yearbook-student-data is missing."
      );
      return;
    }

    let students = [];

    try {
      students = JSON.parse(
        dataElement.textContent.trim() || "[]"
      );
    } catch (error) {
      console.error(
        "[Yearbook] Student JSON parse error:",
        error
      );
      return;
    }

    if (!Array.isArray(students) || !students.length) {
      console.warn(
        "[Yearbook] No student profiles available."
      );
      return;
    }

    const totalStudents = students.length;

    /* ------------------------------------------------------------------------
       DOM
       ------------------------------------------------------------------------ */

    const carouselRoot =
      document.getElementById("yearbook-carousel");

    const stage =
      document.getElementById("yearbook-3d-stage");

    const cylinder =
      document.getElementById("yearbook-cylinder");

    const prevButton =
      document.getElementById("yb-nav-prev");

    const nextButton =
      document.getElementById("yb-nav-next");

    const searchInput =
      document.getElementById("student-search");

    const searchDropdown =
      document.getElementById("yb-search-dropdown");

    /* Modal */

    const modal =
      document.getElementById("yb-morph-modal");

    const modalBackdrop =
      document.getElementById("yb-morph-backdrop");

    const modalCard =
      document.getElementById("yb-morph-card");

    const modalClose =
      document.getElementById("yb-morph-close");

    const modalImage =
      document.getElementById("yb-modal-img");

    const modalName =
      document.getElementById("yb-modal-name");

    const modalNickname =
      document.getElementById("yb-modal-nickname");

    const modalRole =
      document.getElementById("yb-modal-role");

    const modalQuote =
      document.getElementById("yb-modal-quote");

    const modalBio =
      document.getElementById("yb-modal-bio");

    const modalBioWrap =
      document.getElementById("yb-modal-bio-wrap");

    const modalSocials =
      document.getElementById("yb-modal-socials");

    const modalPrevious =
      document.getElementById("yb-modal-prev");

    const modalNext =
      document.getElementById("yb-modal-next");

    const modalCounter =
      document.getElementById("yb-modal-counter");

    const modalContent =
      modalCard?.querySelector(
        ".yb-morph-content"
      ) || null;

    if (!carouselRoot || !stage || !cylinder) {
      console.error(
        "[Yearbook] Carousel HTML elements are missing."
      );
      return;
    }

    /* ==========================================================================
       HELPERS
       ========================================================================== */

    const mod = (value, total) =>
      ((value % total) + total) % total;

    const clamp = (value, min, max) =>
      Math.min(max, Math.max(min, value));

    const normalizeText = (value = "") =>
      String(value).trim().toLowerCase();

    const prefersReducedMotion = () =>
      window.matchMedia(
        "(prefers-reduced-motion: reduce)"
      ).matches;

    function actualIndexFromLogical(logicalIndex) {
      return mod(
        Math.round(logicalIndex),
        totalStudents
      );
    }

    function closestLogicalIndexForActual(
      actualIndex,
      currentLogical
    ) {
      const currentActual =
        actualIndexFromLogical(currentLogical);

      let difference =
        actualIndex - currentActual;

      if (
        difference >
        totalStudents / 2
      ) {
        difference -= totalStudents;
      }

      if (
        difference <
        -totalStudents / 2
      ) {
        difference += totalStudents;
      }

      return (
        Math.round(currentLogical) +
        difference
      );
    }

    /* ==========================================================================
       RESPONSIVE GEOMETRY
       ========================================================================== */

    function getGeometry() {
      const width =
        window.innerWidth;

      if (width <= 480) {
        return {
          slotCount: 7,
          spacing: 0.93,
          xDistance: 150,
          zDistance: 80,
          rotateY: 13,
          dragPixelsPerItem: 125,
          wheelPixelsPerItem: 155,
        };
      }

      if (width <= 768) {
        return {
          slotCount: 9,
          spacing: 0.86,
          xDistance: 190,
          zDistance: 100,
          rotateY: 12,
          dragPixelsPerItem: 145,
          wheelPixelsPerItem: 180,
        };
      }

      if (width <= 1100) {
        return {
          slotCount: 11,
          spacing: 0.78,
          xDistance: 220,
          zDistance: 120,
          rotateY: 11,
          dragPixelsPerItem: 165,
          wheelPixelsPerItem: 205,
        };
      }

      return {
        slotCount: 13,
        spacing: 0.72,
        xDistance: 255,
        zDistance: 150,
        rotateY: 10,
        dragPixelsPerItem: 185,
        wheelPixelsPerItem: 230,
      };
    }

    let geometry =
      getGeometry();

    /* ==========================================================================
       CAROUSEL STATE
       ========================================================================== */

    let position = 0;

    let targetPosition = 0;

    let velocity = 0;

    let slots = [];

    let frameId = 0;

    let previousFrame =
      performance.now();

    /*
     * Physics tuning.
     *
     * These values deliberately avoid:
     * - heavy snapping
     * - hard stop
     * - repeated start/stop
     * - CSS transition fighting
     */

    const SPRING = 46;

    const DAMPING = 12;

    const POSITION_EPSILON =
      0.0005;

    const VELOCITY_EPSILON =
      0.002;

    /* ==========================================================================
       CREATE VIRTUAL CARD
       ========================================================================== */

    function createSlot(
      logicalIndex
    ) {
      const element =
        document.createElement("article");

      element.className =
        "yearbook-slot yb-carousel-card";

      element.innerHTML = `
        <div class="yb-slot-photo">
          <img
            src=""
            alt=""
            draggable="false"
            decoding="async"
          >

          <span
            class="yb-slot-index-tag"
          ></span>
        </div>

        <div class="yb-slot-body">
          <h3
            class="yb-slot-name"
          ></h3>

          <div
            class="yb-slot-nickname"
          ></div>

          <button
            type="button"
            class="yb-slot-cta yb-view-profile"
          >
            VIEW PROFILE ↗
          </button>
        </div>
      `;

      const slot = {
        element,
        logicalIndex,

        image:
          element.querySelector("img"),

        tag:
          element.querySelector(
            ".yb-slot-index-tag"
          ),

        name:
          element.querySelector(
            ".yb-slot-name"
          ),

        nickname:
          element.querySelector(
            ".yb-slot-nickname"
          ),

        button:
          element.querySelector(
            ".yb-view-profile"
          ),

        actualIndex: null,
      };

      refreshSlotData(slot);

      return slot;
    }

    /* ==========================================================================
       SLOT DATA
       ========================================================================== */

    function refreshSlotData(slot) {
      const actualIndex =
        mod(
          slot.logicalIndex,
          totalStudents
        );

      const student =
        students[actualIndex];

      if (!student) return;

      slot.element.dataset.logicalIndex =
        String(slot.logicalIndex);

      slot.element.dataset.studentIndex =
        String(actualIndex);

      slot.element.dataset.studentId =
        String(student.id || "");

      if (
        slot.actualIndex ===
        actualIndex
      ) {
        return;
      }

      slot.actualIndex =
        actualIndex;

      slot.image.src =
        student.image || "";

      slot.image.alt =
        `${student.name || "Classmate"} profile photo`;

      slot.tag.textContent =
        student.index_num ||
        String(
          actualIndex + 1
        ).padStart(3, "0");

      slot.name.textContent =
        student.name || "";

      slot.nickname.textContent =
        student.nickname
          ? `“${student.nickname}”`
          : "";

      slot.button.dataset.logicalIndex =
        String(slot.logicalIndex);

      slot.button.setAttribute(
        "aria-label",
        `View ${student.name || "classmate"} profile`
      );
    }

    /* ==========================================================================
       BUILD SLOTS
       ========================================================================== */

    function buildSlots() {
      geometry =
        getGeometry();

      cylinder.innerHTML = "";

      slots = [];

      const half =
        Math.floor(
          geometry.slotCount / 2
        );

      const center =
        Math.round(position);

      for (
        let offset = -half;
        offset <= half;
        offset += 1
      ) {
        const logicalIndex =
          center + offset;

        const slot =
          createSlot(
            logicalIndex
          );

        slots.push(slot);

        cylinder.appendChild(
          slot.element
        );
      }

      renderCarousel();
    }

    /* ==========================================================================
       SLOT RECYCLING
       ========================================================================== */

    function recycleSlots() {
      if (!slots.length) return;

      const center =
        Math.round(position);

      const half =
        Math.floor(
          slots.length / 2
        );

      const wantedMin =
        center - half;

      const wantedMax =
        center + half;

      let minSlot =
        slots.reduce(
          (a, b) =>
            a.logicalIndex <
            b.logicalIndex
              ? a
              : b
        );

      let maxSlot =
        slots.reduce(
          (a, b) =>
            a.logicalIndex >
            b.logicalIndex
              ? a
              : b
        );

      while (
        minSlot.logicalIndex <
        wantedMin
      ) {
        minSlot.logicalIndex =
          maxSlot.logicalIndex + 1;

        refreshSlotData(
          minSlot
        );

        maxSlot = minSlot;

        minSlot =
          slots.reduce(
            (a, b) =>
              a.logicalIndex <
              b.logicalIndex
                ? a
                : b
          );
      }

      while (
        maxSlot.logicalIndex >
        wantedMax
      ) {
        maxSlot.logicalIndex =
          minSlot.logicalIndex - 1;

        refreshSlotData(
          maxSlot
        );

        minSlot = maxSlot;

        maxSlot =
          slots.reduce(
            (a, b) =>
              a.logicalIndex >
              b.logicalIndex
                ? a
                : b
          );
      }
    }

    /* ==========================================================================
       RENDER CAROUSEL
       ========================================================================== */

    function renderCarousel() {
      recycleSlots();

      slots.forEach((slot) => {
        const difference =
          slot.logicalIndex -
          position;

        const absolute =
          Math.abs(difference);

        /*
         * Natural curved deck.
         */

        const x =
          Math.sin(
            difference *
              geometry.spacing
          ) *
          geometry.xDistance;

        const z =
          -absolute *
          geometry.zDistance;

        const rotationY =
          -difference *
          geometry.rotateY;

        const scale =
          clamp(
            1 -
              absolute * 0.13,
            0.67,
            1
          );

        const opacity =
          clamp(
            1 -
              absolute * 0.19,
            0.08,
            1
          );

        const blur =
          clamp(
            absolute * 0.7,
            0,
            3.5
          );

        const brightness =
          clamp(
            1 -
              absolute * 0.14,
            0.45,
            1
          );

        const zIndex =
          100 -
          Math.round(
            absolute * 10
          );

        slot.element.style.transform = `
          translate3d(
            calc(-50% + ${x}px),
            -50%,
            ${z}px
          )
          rotateY(${rotationY}deg)
          scale(${scale})
        `;

        slot.element.style.opacity =
          String(opacity);

        slot.element.style.filter =
          `brightness(${brightness}) blur(${blur}px)`;

        slot.element.style.zIndex =
          String(zIndex);

        const active =
          absolute < 0.48;

        slot.element.classList.toggle(
          "is-active",
          active
        );

        slot.element.classList.toggle(
          "is-side",
          !active
        );

        slot.element.setAttribute(
          "aria-hidden",
          absolute > 3.8
            ? "true"
            : "false"
        );
      });
    }

    /* ==========================================================================
       RAF PHYSICS
       ========================================================================== */

    function tick(now) {
      const deltaSeconds =
        Math.min(
          0.032,
          Math.max(
            0.001,
            (now - previousFrame) /
              1000
          )
        );

      previousFrame = now;

      if (!isDragging) {
        const displacement =
          targetPosition -
          position;

        const acceleration =
          displacement *
            SPRING -
          velocity *
            DAMPING;

        velocity +=
          acceleration *
          deltaSeconds;

        position +=
          velocity *
          deltaSeconds;

        if (
          Math.abs(displacement) <
            POSITION_EPSILON &&
          Math.abs(velocity) <
            VELOCITY_EPSILON
        ) {
          position =
            targetPosition;

          velocity = 0;
        }
      }

      renderCarousel();

      frameId =
        requestAnimationFrame(
          tick
        );
    }

    frameId =
      requestAnimationFrame(
        tick
      );

    /* ==========================================================================
       PROGRAMMATIC NAVIGATION
       ========================================================================== */

    function navigateBy(
      direction
    ) {
      const base =
        Math.round(
          targetPosition
        );

      targetPosition =
        base + direction;
    }

    prevButton?.addEventListener(
      "click",
      () => {
        navigateBy(-1);
      }
    );

    nextButton?.addEventListener(
      "click",
      () => {
        navigateBy(1);
      }
    );

    /* ==========================================================================
       CAROUSEL POINTER / TOUCH DRAG
       ========================================================================== */

    let isDragging = false;

    let dragPointerId = null;

    let dragStartX = 0;

    let dragLastX = 0;

    let dragLastTime = 0;

    let dragVelocity = 0;

    let dragMoved = false;

    stage.addEventListener(
      "pointerdown",
      (event) => {
        /*
         * Button clicks still need to work.
         */

        if (
          event.target.closest(
            ".yb-view-profile"
          )
        ) {
          return;
        }

        isDragging = true;

        dragPointerId =
          event.pointerId;

        dragStartX =
          event.clientX;

        dragLastX =
          event.clientX;

        dragLastTime =
          performance.now();

        dragVelocity = 0;

        dragMoved = false;

        velocity = 0;

        stage.classList.add(
          "is-dragging"
        );

        try {
          stage.setPointerCapture(
            event.pointerId
          );
        } catch (_) {}
      }
    );

    stage.addEventListener(
      "pointermove",
      (event) => {
        if (
          !isDragging ||
          event.pointerId !==
            dragPointerId
        ) {
          return;
        }

        const now =
          performance.now();

        const dx =
          event.clientX -
          dragLastX;

        const elapsed =
          Math.max(
            1,
            now -
              dragLastTime
          );

        if (
          Math.abs(
            event.clientX -
              dragStartX
          ) > 5
        ) {
          dragMoved = true;
        }

        const itemDelta =
          -dx /
          geometry.dragPixelsPerItem;

        position +=
          itemDelta;

        targetPosition =
          position;

        dragVelocity =
          itemDelta /
          (elapsed / 1000);

        dragLastX =
          event.clientX;

        dragLastTime =
          now;

        event.preventDefault();
      },
      {
        passive: false,
      }
    );

    function finishCarouselDrag(
      event
    ) {
      if (!isDragging) return;

      if (
        dragPointerId !== null &&
        event.pointerId !==
          dragPointerId
      ) {
        return;
      }

      try {
        stage.releasePointerCapture(
          event.pointerId
        );
      } catch (_) {}

      isDragging = false;

      dragPointerId = null;

      stage.classList.remove(
        "is-dragging"
      );

      /*
       * Momentum projection.
       *
       * Keeps swipes continuous.
       */

      const projected =
        position +
        dragVelocity * 0.105;

      targetPosition =
        Math.round(projected);

      velocity =
        dragVelocity * 0.34;

      window.setTimeout(
        () => {
          dragMoved = false;
        },
        40
      );
    }

    stage.addEventListener(
      "pointerup",
      finishCarouselDrag
    );

    stage.addEventListener(
      "pointercancel",
      finishCarouselDrag
    );

    /* ==========================================================================
       MOUSE WHEEL / TRACKPAD
       ========================================================================== */

    let wheelAccumulator = 0;

    let wheelTimer = null;

    stage.addEventListener(
      "wheel",
      (event) => {
        if (
          Math.abs(event.deltaX) <
          Math.abs(event.deltaY)
        ) {
          /*
           * Allow normal vertical page scrolling.
           */
          return;
        }

        event.preventDefault();

        wheelAccumulator +=
          event.deltaX /
          geometry.wheelPixelsPerItem;

        targetPosition +=
          event.deltaX /
          geometry.wheelPixelsPerItem;

        clearTimeout(
          wheelTimer
        );

        wheelTimer =
          setTimeout(() => {
            targetPosition =
              Math.round(
                targetPosition
              );

            wheelAccumulator = 0;
          }, 90);
      },
      {
        passive: false,
      }
    );

    /* ==========================================================================
       CARD CLICK
       ========================================================================== */

    cylinder.addEventListener(
      "click",
      (event) => {
        const button =
          event.target.closest(
            ".yb-view-profile"
          );

        const card =
          event.target.closest(
            ".yearbook-slot"
          );

        if (!card) return;

        const logicalIndex =
          Number(
            card.dataset.logicalIndex
          );

        if (
          !Number.isFinite(
            logicalIndex
          )
        ) {
          return;
        }

        if (dragMoved) {
          return;
        }

        const difference =
          Math.abs(
            logicalIndex -
              position
          );

        /*
         * Side card:
         * first bring to center.
         */

        if (
          !button &&
          difference > 0.45
        ) {
          targetPosition =
            logicalIndex;

          return;
        }

        /*
         * Active card / VIEW PROFILE.
         */

        position =
          logicalIndex;

        targetPosition =
          logicalIndex;

        velocity = 0;

        openProfile(
          logicalIndex
        );
      }
    );

    /* ==========================================================================
       SEARCH
       ========================================================================== */

    let filteredResults = [];

    function hideSearchDropdown() {
      if (!searchDropdown) {
        return;
      }

      searchDropdown.hidden = true;

      searchDropdown.setAttribute(
        "aria-hidden",
        "true"
      );

      searchDropdown.innerHTML =
        "";
    }

    function renderSearchResults(
      query
    ) {
      if (!searchDropdown) {
        return;
      }

      const normalized =
        normalizeText(query);

      if (!normalized) {
        hideSearchDropdown();
        return;
      }

      filteredResults =
        students
          .map(
            (
              student,
              index
            ) => ({
              student,
              index,
            })
          )
          .filter(
            ({
              student,
            }) => {
              const name =
                normalizeText(
                  student.name
                );

              const nickname =
                normalizeText(
                  student.nickname
                );

              return (
                name.includes(
                  normalized
                ) ||
                nickname.includes(
                  normalized
                )
              );
            }
          )
          .slice(0, 8);

      if (
        filteredResults.length ===
        0
      ) {
        searchDropdown.innerHTML = `
          <div class="yb-search-empty">
            No classmate found
          </div>
        `;

        searchDropdown.hidden =
          false;

        searchDropdown.setAttribute(
          "aria-hidden",
          "false"
        );

        return;
      }

      searchDropdown.innerHTML =
        filteredResults
          .map(
            ({
              student,
              index,
            }) => `
            <button
              type="button"
              class="yb-search-result"
              data-search-index="${index}"
            >
              <img
                src="${escapeHTMLAttribute(
                  student.image || ""
                )}"
                alt=""
              >

              <span class="yb-search-result-copy">
                <strong>
                  ${escapeHTML(
                    student.name || ""
                  )}
                </strong>

                ${
                  student.nickname
                    ? `
                      <small>
                        “${escapeHTML(
                          student.nickname
                        )}”
                      </small>
                    `
                    : ""
                }
              </span>
            </button>
          `
          )
          .join("");

      searchDropdown.hidden =
        false;

      searchDropdown.setAttribute(
        "aria-hidden",
        "false"
      );
    }

    searchInput?.addEventListener(
      "input",
      () => {
        renderSearchResults(
          searchInput.value
        );
      }
    );

    searchInput?.addEventListener(
      "keydown",
      (event) => {
        if (
          event.key ===
          "Escape"
        ) {
          hideSearchDropdown();

          searchInput.blur();

          return;
        }

        if (
          event.key ===
            "Enter" &&
          filteredResults.length
        ) {
          event.preventDefault();

          selectSearchResult(
            filteredResults[0]
              .index
          );
        }
      }
    );

    searchDropdown?.addEventListener(
      "click",
      (event) => {
        const result =
          event.target.closest(
            "[data-search-index]"
          );

        if (!result) return;

        const index =
          Number(
            result.dataset
              .searchIndex
          );

        if (
          Number.isFinite(index)
        ) {
          selectSearchResult(
            index
          );
        }
      }
    );

    function selectSearchResult(
      actualIndex
    ) {
      const logicalTarget =
        closestLogicalIndexForActual(
          actualIndex,
          position
        );

      targetPosition =
        logicalTarget;

      if (searchInput) {
        searchInput.value =
          students[
            actualIndex
          ]?.name || "";
      }

      hideSearchDropdown();

      searchInput?.blur();
    }

    document.addEventListener(
      "pointerdown",
      (event) => {
        if (
          !event.target.closest(
            ".yb-search-wrap"
          )
        ) {
          hideSearchDropdown();
        }
      }
    );

    /* ==========================================================================
       HTML ESCAPE
       ========================================================================== */

    function escapeHTML(
      value
    ) {
      return String(
        value ?? ""
      )
        .replaceAll(
          "&",
          "&amp;"
        )
        .replaceAll(
          "<",
          "&lt;"
        )
        .replaceAll(
          ">",
          "&gt;"
        )
        .replaceAll(
          '"',
          "&quot;"
        )
        .replaceAll(
          "'",
          "&#039;"
        );
    }

    function escapeHTMLAttribute(
      value
    ) {
      return escapeHTML(
        value
      );
    }

    /* ==========================================================================
       MODAL STATE & VERTICAL PARALLAX ENGINE
       ========================================================================== */

    let modalOpen = false;
    let activeIndex = 0;
    let isNavigating = false;
    let pendingStep = 0;
    let previouslyFocused = null;

    const viewportEl = document.getElementById("yb-profile-viewport");

    function normIndex(idx) {
      return ((idx % totalStudents) + totalStudents) % totalStudents;
    }

    function preloadNeighbours(idx) {
      if (!totalStudents) return;
      const nextIdx = normIndex(idx + 1);
      const prevIdx = normIndex(idx - 1);

      [nextIdx, prevIdx].forEach((i) => {
        const src = students[i]?.image;
        if (src) {
          const img = new Image();
          img.src = src;
        }
      });
    }

    function createSlideHTML(student, stateClass, slotOffset) {
      const src = student?.image || "";
      const name = student?.name || "Classmate";
      const initialTransform = slotOffset < 0 ? "translate3d(0, -100%, 0) scale(0.965)" : (slotOffset > 0 ? "translate3d(0, 100%, 0) scale(0.965)" : "translate3d(0, 0%, 0) scale(1)");
      const imgParallax = slotOffset < 0 ? "translate3d(0, 14%, 0)" : (slotOffset > 0 ? "translate3d(0, -14%, 0)" : "translate3d(0, 0%, 0)");

      return `
        <div class="yb-profile-slide ${stateClass}" data-slot="${slotOffset}" style="transform: ${initialTransform};">
          <div class="yb-profile-slide-img-wrap">
            <img src="${escapeHTMLAttribute(src)}" alt="${escapeHTMLAttribute(name)} profile photo" class="yb-profile-slide-img" style="transform: scale(1.06) ${imgParallax};" />
          </div>
        </div>
      `;
    }

    function renderVirtualStack() {
      if (!viewportEl || !totalStudents) return;

      const prevIdx = normIndex(activeIndex - 1);
      const currIdx = normIndex(activeIndex);
      const nextIdx = normIndex(activeIndex + 1);

      const prevStudent = students[prevIdx];
      const currStudent = students[currIdx];
      const nextStudent = students[nextIdx];

      viewportEl.innerHTML = `
        ${createSlideHTML(prevStudent, "is-prev", -1)}
        ${createSlideHTML(nextStudent, "is-next", 1)}
        ${createSlideHTML(currStudent, "is-active", 0)}
      `;
    }

    function renderSocials(student) {
      if (!modalSocials) return;
      const links = [];

      if (student.insta) {
        links.push(`
          <a class="yb-social-link" href="${escapeHTMLAttribute(student.insta)}" target="_blank" rel="noopener noreferrer">
            Instagram ↗
          </a>
        `);
      }

      if (student.linkedin) {
        links.push(`
          <a class="yb-social-link" href="${escapeHTMLAttribute(student.linkedin)}" target="_blank" rel="noopener noreferrer">
            LinkedIn ↗
          </a>
        `);
      }

      modalSocials.innerHTML = links.join("");
      modalSocials.hidden = links.length === 0;
    }

    function updateModalContent(idx) {
      const student = students[idx];
      if (!student) return;

      if (modalName) modalName.textContent = student.name || "";

      if (modalNickname) {
        modalNickname.textContent = student.nickname ? `“${student.nickname}”` : "";
        modalNickname.hidden = !student.nickname;
      }

      if (modalRole) {
        modalRole.textContent = student.role || "";
        modalRole.hidden = !student.role;
      }

      if (modalQuote) {
        modalQuote.textContent = student.quote ? `“${student.quote}”` : "";
        modalQuote.hidden = !student.quote;
      }

      if (modalBio) modalBio.textContent = student.bio || "";
      if (modalBioWrap) modalBioWrap.hidden = !student.bio;

      renderSocials(student);

      if (modalCounter) {
        const currentNum = String(idx + 1).padStart(2, "0");
        const totalNum = String(totalStudents).padStart(2, "0");
        modalCounter.textContent = `${currentNum} / ${totalNum}`;
        modalCounter.classList.remove("is-animating");
      }
    }

    function animateVerticalParallax(dir, onMidpoint, onComplete) {
      const duration = prefersReducedMotion() ? 10 : 480;
      const startTime = performance.now();
      let midpointFired = false;

      renderVirtualStack();

      const activeSlide = viewportEl?.querySelector(".yb-profile-slide.is-active");
      const prevSlide = viewportEl?.querySelector(".yb-profile-slide.is-prev");
      const nextSlide = viewportEl?.querySelector(".yb-profile-slide.is-next");

      const activeImg = activeSlide?.querySelector(".yb-profile-slide-img");
      const prevImg = prevSlide?.querySelector(".yb-profile-slide-img");
      const nextImg = nextSlide?.querySelector(".yb-profile-slide-img");

      function stepFrame(now) {
        const elapsed = now - startTime;
        const linearProgress = Math.min(1, elapsed / duration);
        const eased = 1 - Math.pow(1 - linearProgress, 3);

        if (linearProgress >= 0.3 && !midpointFired) {
          midpointFired = true;
          if (onMidpoint) onMidpoint();
        }

        if (dir > 0) {
          // NEXT (down -> up)
          if (prevSlide) {
            const prevY = -eased * 100;
            const prevScale = 1 - eased * 0.035;
            prevSlide.style.transform = `translate3d(0, ${prevY}%, 0) scale(${prevScale})`;
            prevSlide.style.opacity = `${1 - eased * 0.55}`;
            if (prevImg) prevImg.style.transform = `scale(1.06) translate3d(0, ${-eased * 14}%, 0)`;
          }

          if (activeSlide) {
            const activeY = (1 - eased) * 100;
            const activeScale = 0.965 + eased * 0.035;
            activeSlide.style.transform = `translate3d(0, ${activeY}%, 0) scale(${activeScale})`;
            activeSlide.style.opacity = `${0.45 + eased * 0.55}`;
            if (activeImg) activeImg.style.transform = `scale(1.06) translate3d(0, ${(1 - eased) * 14}%, 0)`;
          }
        } else {
          // PREVIOUS (up -> down)
          if (nextSlide) {
            const nextY = eased * 100;
            const nextScale = 1 - eased * 0.035;
            nextSlide.style.transform = `translate3d(0, ${nextY}%, 0) scale(${nextScale})`;
            nextSlide.style.opacity = `${1 - eased * 0.55}`;
            if (nextImg) nextImg.style.transform = `scale(1.06) translate3d(0, ${eased * 14}%, 0)`;
          }

          if (activeSlide) {
            const activeY = -(1 - eased) * 100;
            const activeScale = 0.965 + eased * 0.035;
            activeSlide.style.transform = `translate3d(0, ${activeY}%, 0) scale(${activeScale})`;
            activeSlide.style.opacity = `${0.45 + eased * 0.55}`;
            if (activeImg) activeImg.style.transform = `scale(1.06) translate3d(0, ${-(1 - eased) * 14}%, 0)`;
          }
        }

        if (linearProgress < 1) {
          requestAnimationFrame(stepFrame);
        } else {
          renderVirtualStack();
          if (onComplete) onComplete();
        }
      }

      requestAnimationFrame(stepFrame);
    }

    function navigateModalProfile(step) {
      if (!modalOpen || !totalStudents) return;

      if (isNavigating) {
        pendingStep = step;
        return;
      }

      isNavigating = true;
      const dir = step > 0 ? 1 : -1;

      activeIndex = normIndex(activeIndex + dir);

      const exitClass = dir > 0 ? "is-exiting-up" : "is-exiting-down";
      if (modalContent) modalContent.classList.add(exitClass);
      if (modalCounter) modalCounter.classList.add("is-animating");

      animateVerticalParallax(
        dir,
        () => {
          updateModalContent(activeIndex);
        },
        () => {
          if (modalContent) {
            modalContent.classList.remove("is-exiting-up", "is-exiting-down");
          }
          isNavigating = false;
          preloadNeighbours(activeIndex);

          if (pendingStep !== 0) {
            const nextStep = pendingStep;
            pendingStep = 0;
            navigateModalProfile(nextStep);
          }
        }
      );
    }

    /* ==========================================================================
       OPEN MODAL
       ========================================================================== */

    function openProfile(logicalIndex) {
      if (!modal || !modalCard) return;

      activeIndex = normIndex(Math.round(logicalIndex));

      // Synchronize background carousel position
      position = activeIndex;
      targetPosition = activeIndex;
      velocity = 0;

      renderVirtualStack();
      updateModalContent(activeIndex);
      preloadNeighbours(activeIndex);

      modalOpen = true;
      previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;

      modal.hidden = false;
      modal.setAttribute("aria-hidden", "false");
      document.body.classList.add("yearbook-modal-open");

      modal.classList.remove("is-open");
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          modal.classList.add("is-open");
        });
      });

      modalClose?.focus({ preventScroll: true });
    }

    /* ==========================================================================
       CLOSE MODAL
       ========================================================================== */

    function closeProfile() {
      if (!modal || !modalOpen) return;
      modalOpen = false;

      // Preserve currently viewed activeIndex on background carousel
      position = activeIndex;
      targetPosition = activeIndex;
      velocity = 0;

      modal.classList.remove("is-open");
      document.body.classList.remove("yearbook-modal-open");

      const duration = prefersReducedMotion() ? 10 : 480;

      setTimeout(() => {
        modal.hidden = true;
        modal.setAttribute("aria-hidden", "true");
        previouslyFocused?.focus?.({ preventScroll: true });
      }, duration);
    }

    modalClose?.addEventListener("click", closeProfile);
    modalBackdrop?.addEventListener("click", closeProfile);

    modalPrevious?.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      navigateModalProfile(-1);
    });

    modalNext?.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      navigateModalProfile(1);
    });

    /* ==========================================================================
       MODAL SWIPE (VERTICAL & HORIZONTAL GESTURES)
       ========================================================================== */

    let modalDragging = false;
    let modalPointer = null;
    let modalStartX = 0;
    let modalStartY = 0;
    let modalCurrentX = 0;
    let modalCurrentY = 0;
    let modalGesture = null;

    modalCard?.addEventListener("pointerdown", (event) => {
      if (event.target.closest("button, a, input, textarea, select")) {
        return;
      }
      if (isNavigating) return;

      modalDragging = true;
      modalPointer = event.pointerId;
      modalStartX = event.clientX;
      modalStartY = event.clientY;
      modalCurrentX = event.clientX;
      modalCurrentY = event.clientY;
      modalGesture = null;

      try {
        modalCard.setPointerCapture(event.pointerId);
      } catch (_) {}
    });

    modalCard?.addEventListener(
      "pointermove",
      (event) => {
        if (!modalDragging || event.pointerId !== modalPointer) return;

        const dx = event.clientX - modalStartX;
        const dy = event.clientY - modalStartY;

        modalCurrentX = event.clientX;
        modalCurrentY = event.clientY;

        if (!modalGesture) {
          if (Math.abs(dx) > 7 || Math.abs(dy) > 7) {
            modalGesture = Math.abs(dy) >= Math.abs(dx) ? "vertical" : "horizontal";
          }
        }
      },
      { passive: true }
    );

    function finishModalDrag(event) {
      if (!modalDragging) return;
      if (modalPointer !== null && event.pointerId !== modalPointer) return;

      try {
        modalCard.releasePointerCapture(event.pointerId);
      } catch (_) {}

      modalDragging = false;
      modalPointer = null;

      const dy = modalCurrentY - modalStartY;
      const dx = modalCurrentX - modalStartX;

      if (modalGesture === "vertical" && Math.abs(dy) >= 44) {
        if (dy < 0) {
          navigateModalProfile(1); // Swipe UP -> NEXT
        } else {
          navigateModalProfile(-1); // Swipe DOWN -> PREV
        }
      } else if (modalGesture === "horizontal" && Math.abs(dx) >= 44) {
        if (dx < 0) {
          navigateModalProfile(1); // Swipe LEFT -> NEXT
        } else {
          navigateModalProfile(-1); // Swipe RIGHT -> PREV
        }
      }

      modalGesture = null;
    }

    modalCard?.addEventListener("pointerup", finishModalDrag);
    modalCard?.addEventListener("pointercancel", finishModalDrag);

    /* ==========================================================================
       KEYBOARD
       ========================================================================== */

    document.addEventListener("keydown", (event) => {
      if (modalOpen) {
        switch (event.key) {
          case "Escape":
            event.preventDefault();
            closeProfile();
            break;

          case "ArrowLeft":
          case "ArrowUp":
            event.preventDefault();
            navigateModalProfile(-1);
            break;

          case "ArrowRight":
          case "ArrowDown":
            event.preventDefault();
            navigateModalProfile(1);
            break;
        }
        return;
      }

        if (
          document.activeElement ===
          searchInput
        ) {
          return;
        }

        if (
          event.key ===
          "ArrowLeft"
        ) {
          event.preventDefault();

          navigateBy(-1);
        }

        if (
          event.key ===
          "ArrowRight"
        ) {
          event.preventDefault();

          navigateBy(1);
        }

        if (
          event.key ===
          "Enter"
        ) {
          event.preventDefault();

          const current =
            Math.round(
              position
            );

          targetPosition =
            current;

          openProfile(
            current
          );
        }
      }
    );

    /* ==========================================================================
       RESIZE
       ========================================================================== */

    let resizeTimer =
      null;

    window.addEventListener(
      "resize",
      () => {
        clearTimeout(
          resizeTimer
        );

        resizeTimer =
          setTimeout(() => {
            const newGeometry =
              getGeometry();

            const rebuild =
              newGeometry.slotCount !==
              geometry.slotCount;

            geometry =
              newGeometry;

            if (
              rebuild &&
              !isDragging
            ) {
              buildSlots();
            }
          }, 140);
      }
    );

    /* ==========================================================================
       VISIBILITY / PERFORMANCE
       ========================================================================== */

    document.addEventListener(
      "visibilitychange",
      () => {
        previousFrame =
          performance.now();

        if (
          document.hidden
        ) {
          velocity = 0;
        }
      }
    );

    /* ==========================================================================
       INITIALIZE
       ========================================================================== */

    buildSlots();

    console.info(
      `[Yearbook] Smooth infinite Class Orbit ready — ${totalStudents} classmates.`
    );
  }
})();