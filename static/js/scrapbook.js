/**
 * ============================================================
 * COLLEGE MEMORIES '26
 * PREMIUM INTERACTIVE SCRAPBOOK
 * ============================================================
 *
 * Responsibilities:
 *
 * 1. Scratch-to-Reveal Polaroids
 * 2. Pointer / Mouse / Touch support
 * 3. High-DPI Canvas Rendering
 * 4. Automatic Reveal Threshold
 * 5. Reset Scratch Memories
 * 6. Dynamic Polaroid Layout for 10+ items
 * 7. Scrapbook Lightbox
 * 8. Final Memory Envelope
 *
 * No external libraries required.
 * ============================================================
 */


document.addEventListener("DOMContentLoaded", () => {
  initScratchPolaroids();
  initScrapbookDeckEngine();
  initFilmStripSeamlessLoop();
  initScrapbookLightbox();
  initFinalMemoryEnvelope();
  initInteractiveSlogan();
});

/* ============================================================
   INTERACTIVE SLOGAN
   ============================================================ */

function initInteractiveSlogan() {
  const slogan = document.getElementById("scrapbook-slogan");
  if (!slogan) return;

  const textSpan = slogan.querySelector(".slogan-text");
  const dot = slogan.querySelector(".slogan-glow-dot");
  if (!textSpan) return;

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;

  slogan.addEventListener("mousemove", (e) => {
    const rect = slogan.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;

    const moveX = (x / (rect.width / 2)) * 3;
    const moveY = (y / (rect.height / 2)) * 2;

    textSpan.style.transform = `translate3d(${moveX}px, ${moveY}px, 0)`;
    if (dot) {
      dot.style.transform = `translate3d(${x}px, ${y}px, 0) translate(-50%, -50%)`;
    }
  });

  slogan.addEventListener("mouseleave", () => {
    textSpan.style.transform = "translate3d(0, 0, 0)";
    if (dot) {
      dot.style.transform = "translate(-50%, -50%)";
    }
  });
}


/* ============================================================
   SCRATCH POLAROIDS
   ============================================================ */

function initScratchPolaroids() {
  const cards = Array.from(
    document.querySelectorAll(".memory-polaroid")
  );

  if (!cards.length) {
    return;
  }


  cards.forEach((card) => {
    createScratchCard(card);
  });


  const resetButton =
    document.getElementById("scratch-reset-btn");


  if (resetButton) {
    resetButton.addEventListener("click", () => {
      cards.forEach((card) => {
        resetScratchCard(card);
      });
    });
  }
}



/* ============================================================
   CREATE ONE SCRATCH CARD
   ============================================================ */

function createScratchCard(card) {
  const canvas =
    card.querySelector(".memory-scratch-canvas");

  const photoFrame =
    card.querySelector(".memory-polaroid-photo");

  const trigger =
    card.querySelector(".memory-view-trigger");


  if (
    !canvas ||
    !photoFrame
  ) {
    return;
  }


  const ctx =
    canvas.getContext("2d", {
      willReadFrequently: true,
    });


  if (!ctx) {
    return;
  }


  const state = {
    card,
    canvas,
    photoFrame,
    trigger,
    ctx,

    drawing: false,

    lastX: null,
    lastY: null,

    revealCheckedAt: 0,

    revealed: false,

    resizeObserver: null,
  };


  card._scratchState = state;


  initializeScratchSurface(state);


  if ("ResizeObserver" in window) {
    state.resizeObserver =
      new ResizeObserver(() => {
        if (!state.revealed) {
          initializeScratchSurface(state);
        }
      });

    state.resizeObserver.observe(photoFrame);
  }


  canvas.addEventListener(
    "pointerdown",
    (event) => {
      beginScratch(event, state);
    }
  );


  canvas.addEventListener(
    "pointermove",
    (event) => {
      continueScratch(event, state);
    }
  );


  canvas.addEventListener(
    "pointerup",
    (event) => {
      finishScratch(event, state);
    }
  );


  canvas.addEventListener(
    "pointercancel",
    (event) => {
      finishScratch(event, state);
    }
  );


  canvas.addEventListener(
    "pointerleave",
    (event) => {
      if (
        event.pointerType === "mouse" &&
        state.drawing
      ) {
        finishScratch(event, state);
      }
    }
  );
}



/* ============================================================
   PAINT SCRATCH SURFACE
   ============================================================ */

function initializeScratchSurface(state) {
  const {
    canvas,
    photoFrame,
    ctx,
  } = state;


  const rect =
    photoFrame.getBoundingClientRect();


  if (
    rect.width <= 0 ||
    rect.height <= 0
  ) {
    return;
  }


  const dpr =
    Math.min(
      window.devicePixelRatio || 1,
      2
    );


  canvas.width =
    Math.round(rect.width * dpr);

  canvas.height =
    Math.round(rect.height * dpr);


  canvas.style.width =
    `${rect.width}px`;

  canvas.style.height =
    `${rect.height}px`;


  ctx.setTransform(
    dpr,
    0,
    0,
    dpr,
    0,
    0
  );


  ctx.globalCompositeOperation =
    "source-over";


  /* ----------------------------------------------------------
     BACKGROUND
     ---------------------------------------------------------- */

  const gradient =
    ctx.createLinearGradient(
      0,
      0,
      rect.width,
      rect.height
    );


  gradient.addColorStop(
    0,
    "#25242a"
  );

  gradient.addColorStop(
    0.5,
    "#19191e"
  );

  gradient.addColorStop(
    1,
    "#29272e"
  );


  ctx.fillStyle = gradient;

  ctx.fillRect(
    0,
    0,
    rect.width,
    rect.height
  );


  /* ----------------------------------------------------------
     SUBTLE PAPER GRAIN
     ---------------------------------------------------------- */

  ctx.save();

  ctx.globalAlpha = 0.18;


  const dotCount =
    Math.round(
      (rect.width * rect.height) /
      650
    );


  for (
    let i = 0;
    i < dotCount;
    i += 1
  ) {
    const x =
      Math.random() * rect.width;

    const y =
      Math.random() * rect.height;

    const size =
      Math.random() * 1.3 + 0.3;


    ctx.fillStyle =
      Math.random() > 0.5
        ? "#8f876f"
        : "#060606";


    ctx.fillRect(
      x,
      y,
      size,
      size
    );
  }


  ctx.restore();


  state.card.classList.remove(
    "is-revealed",
    "is-scratching"
  );


  state.revealed = false;

  state.drawing = false;

  state.lastX = null;

  state.lastY = null;


  if (state.trigger) {
    state.trigger.tabIndex = -1;
  }
}



/* ============================================================
   BEGIN SCRATCH
   ============================================================ */

function beginScratch(event, state) {
  if (state.revealed) {
    return;
  }


  event.preventDefault();


  state.drawing = true;


  state.card.classList.add(
    "is-scratching"
  );


  try {
    state.canvas.setPointerCapture(
      event.pointerId
    );
  } catch (_) {
    // Safe fallback.
  }


  const position =
    getCanvasPoint(
      event,
      state.canvas
    );


  state.lastX = position.x;

  state.lastY = position.y;


  eraseAt(
    position.x,
    position.y,
    state
  );
}



/* ============================================================
   CONTINUE SCRATCH
   ============================================================ */

function continueScratch(event, state) {
  if (
    !state.drawing ||
    state.revealed
  ) {
    return;
  }


  event.preventDefault();


  const current =
    getCanvasPoint(
      event,
      state.canvas
    );


  if (
    state.lastX === null ||
    state.lastY === null
  ) {
    state.lastX = current.x;
    state.lastY = current.y;
  }


  eraseStroke(
    state.lastX,
    state.lastY,
    current.x,
    current.y,
    state
  );


  state.lastX = current.x;

  state.lastY = current.y;


  const now =
    performance.now();


  /*
   * Pixel analysis is intentionally throttled.
   * Checking every pointermove causes mobile stuttering.
   */

  if (
    now -
    state.revealCheckedAt >
    130
  ) {
    state.revealCheckedAt = now;

    maybeRevealCard(state);
  }
}



/* ============================================================
   FINISH SCRATCH
   ============================================================ */

function finishScratch(event, state) {
  if (!state.drawing) {
    return;
  }


  state.drawing = false;

  state.lastX = null;

  state.lastY = null;


  state.card.classList.remove(
    "is-scratching"
  );


  try {
    state.canvas.releasePointerCapture(
      event.pointerId
    );
  } catch (_) {
    // Safe fallback.
  }


  maybeRevealCard(state);
}



/* ============================================================
   ERASE SINGLE POINT
   ============================================================ */

function eraseAt(x, y, state) {
  const {
    ctx,
    photoFrame,
  } = state;


  const width =
    photoFrame.clientWidth;


  const radius =
    Math.max(
      18,
      Math.min(
        34,
        width * 0.085
      )
    );


  ctx.save();


  ctx.globalCompositeOperation =
    "destination-out";


  const gradient =
    ctx.createRadialGradient(
      x,
      y,
      radius * 0.25,
      x,
      y,
      radius
    );


  gradient.addColorStop(
    0,
    "rgba(0,0,0,1)"
  );

  gradient.addColorStop(
    0.78,
    "rgba(0,0,0,1)"
  );

  gradient.addColorStop(
    1,
    "rgba(0,0,0,0)"
  );


  ctx.fillStyle = gradient;


  ctx.beginPath();

  ctx.arc(
    x,
    y,
    radius,
    0,
    Math.PI * 2
  );

  ctx.fill();


  ctx.restore();
}



/* ============================================================
   ERASE SMOOTH LINE
   ============================================================ */

function eraseStroke(
  fromX,
  fromY,
  toX,
  toY,
  state
) {
  const {
    ctx,
    photoFrame,
  } = state;


  const width =
    photoFrame.clientWidth;


  const brush =
    Math.max(
      34,
      Math.min(
        68,
        width * 0.17
      )
    );


  ctx.save();


  ctx.globalCompositeOperation =
    "destination-out";


  ctx.lineWidth = brush;

  ctx.lineCap = "round";

  ctx.lineJoin = "round";


  ctx.beginPath();

  ctx.moveTo(
    fromX,
    fromY
  );

  ctx.lineTo(
    toX,
    toY
  );

  ctx.stroke();


  ctx.restore();
}



/* ============================================================
   POINTER POSITION
   ============================================================ */

function getCanvasPoint(event, canvas) {
  if (
    typeof event.offsetX === "number" &&
    typeof event.offsetY === "number" &&
    event.target === canvas
  ) {
    return {
      x: event.offsetX,
      y: event.offsetY,
    };
  }

  const rect =
    canvas.getBoundingClientRect();


  return {
    x:
      event.clientX -
      rect.left,

    y:
      event.clientY -
      rect.top,
  };
}



/* ============================================================
   REVEAL CHECK
   ============================================================ */

function maybeRevealCard(state) {
  if (state.revealed) {
    return;
  }


  const percent =
    getTransparentPercentage(
      state.canvas,
      state.ctx
    );


  /*
   * 42% feels intentional without forcing the visitor
   * to scratch every single pixel.
   */

  if (percent >= 42) {
    revealScratchCard(state);
  }
}



/* ============================================================
   TRANSPARENT PIXEL SAMPLE
   ============================================================ */

function getTransparentPercentage(
  canvas,
  ctx
) {
  try {
    const imageData =
      ctx.getImageData(
        0,
        0,
        canvas.width,
        canvas.height
      );


    const pixels =
      imageData.data;


    /*
     * Sample every 32 pixels rather than every pixel.
     * This massively reduces work on phones.
     */

    const step =
      4 * 32;


    let transparent = 0;

    let checked = 0;


    for (
      let i = 3;
      i < pixels.length;
      i += step
    ) {
      checked += 1;


      if (pixels[i] < 50) {
        transparent += 1;
      }
    }


    if (!checked) {
      return 0;
    }


    return (
      transparent /
      checked
    ) * 100;

  } catch (_) {

    return 0;

  }
}



/* ============================================================
   FULL REVEAL
   ============================================================ */

function revealScratchCard(state) {
  if (state.revealed) {
    return;
  }


  state.revealed = true;

  state.drawing = false;


  state.card.classList.remove(
    "is-scratching"
  );


  state.card.classList.add(
    "is-revealed"
  );


  state.ctx.save();


  state.ctx.globalCompositeOperation =
    "destination-out";


  state.ctx.clearRect(
    0,
    0,
    state.canvas.width,
    state.canvas.height
  );


  state.ctx.restore();


  if (state.trigger) {
    state.trigger.tabIndex = 0;
  }
}



/* ============================================================
   RESET ONE CARD
   ============================================================ */

function resetScratchCard(card) {
  const state =
    card._scratchState;


  if (!state) {
    return;
  }


  initializeScratchSurface(state);
}



/* ============================================================
   RESPONSIVE SCRAPBOOK DECK CAROUSEL & SWIPE ENGINE
   Supports 1 to 8+ Polaroids across Mobile, Tablet, Desktop
   ============================================================ */

function initScrapbookDeckEngine() {
  const wall = document.getElementById("memory-polaroid-wall");
  const frame = document.querySelector(".scrapbook-display-frame");
  if (!wall || !frame) return;

  const cards = Array.from(wall.querySelectorAll(".memory-polaroid"));
  if (!cards.length) return;

  frame.setAttribute("data-count", String(cards.length));

  const prevBtn = document.getElementById("scrapbook-deck-prev");
  const nextBtn = document.getElementById("scrapbook-deck-next");
  const dotsContainer = document.getElementById("scrapbook-deck-dots");
  const counterEl = document.getElementById("scrapbook-deck-counter");

  let currentPage = 0;
  let totalPages = 1;
  let pageSize = 3;

  function getPageSize() {
    const w = window.innerWidth;
    if (w < 768) return 1;       // Mobile: 1 COMPLETE card per view
    if (w < 1025) return 2;      // Tablet: 2 cards per view
    return 3;                    // Desktop: 3 cards per view
  }

  function updateDeckPages() {
    pageSize = getPageSize();
    totalPages = Math.max(1, Math.ceil(cards.length / pageSize));
    if (currentPage >= totalPages) currentPage = totalPages - 1;

    renderDeckUI();
  }

  function renderDeckUI() {
    if (dotsContainer) {
      dotsContainer.innerHTML = "";
      for (let i = 0; i < totalPages; i++) {
        const dot = document.createElement("button");
        dot.type = "button";
        dot.className = `scrapbook-deck-dot ${i === currentPage ? "is-active" : ""}`;
        dot.setAttribute("aria-label", `Go to page ${i + 1}`);
        dot.addEventListener("click", () => goToPage(i));
        dotsContainer.appendChild(dot);
      }
    }

    if (counterEl) {
      const pageStr = String(currentPage + 1).padStart(2, "0");
      const totalStr = String(totalPages).padStart(2, "0");
      counterEl.textContent = `${pageStr} / ${totalStr}`;
    }

    if (prevBtn) prevBtn.disabled = currentPage === 0;
    if (nextBtn) nextBtn.disabled = currentPage === totalPages - 1;

    const startIndex = currentPage * pageSize;
    const endIndex = startIndex + pageSize;

    cards.forEach((card, idx) => {
      const isVisible = idx >= startIndex && idx < endIndex;
      const slotIndex = idx - startIndex;

      card.classList.toggle("is-deck-visible", isVisible);
      card.classList.toggle("is-deck-hidden", !isVisible);
      card.setAttribute("aria-hidden", String(!isVisible));

      if (isVisible) {
        if (pageSize === 1) {
          card.style.left = "50%";
          card.style.top = "50%";
          card.style.transform = "translate(-50%, -50%) rotate(var(--admin-rotation, 0deg))";
        } else if (pageSize === 2) {
          const posLeft = slotIndex === 0 ? "30%" : "70%";
          card.style.left = posLeft;
          card.style.top = "50%";
          card.style.transform = "translate(-50%, -50%) rotate(var(--admin-rotation, 0deg))";
        } else {
          const posLeft = slotIndex === 0 ? "22%" : (slotIndex === 1 ? "50%" : "78%");
          const posTop = slotIndex === 1 ? "46%" : "50%";
          card.style.left = posLeft;
          card.style.top = posTop;
          card.style.transform = "translate(-50%, -50%) rotate(var(--admin-rotation, 0deg))";
        }

        if (card._scratchState && !card._scratchState.revealed) {
          initializeScratchSurface(card._scratchState);
        }
      }
    });
  }

  function goToPage(page) {
    if (page < 0 || page >= totalPages) return;
    currentPage = page;
    renderDeckUI();
  }

  if (prevBtn) prevBtn.addEventListener("click", () => goToPage(currentPage - 1));
  if (nextBtn) nextBtn.addEventListener("click", () => goToPage(currentPage + 1));

  let touchStartX = 0;
  let touchStartY = 0;
  let touchActive = false;

  wall.addEventListener("touchstart", (e) => {
    if (!e.touches || e.touches.length !== 1) return;
    const targetCanvas = e.target.closest(".memory-scratch-canvas");
    if (targetCanvas && targetCanvas.classList.contains("is-scratching")) return;

    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
    touchActive = true;
  }, { passive: true });

  wall.addEventListener("touchend", (e) => {
    if (!touchActive || !e.changedTouches || !e.changedTouches.length) return;
    touchActive = false;

    const touchEndX = e.changedTouches[0].clientX;
    const touchEndY = e.changedTouches[0].clientY;
    const deltaX = touchEndX - touchStartX;
    const deltaY = touchEndY - touchStartY;

    if (Math.abs(deltaX) > 40 && Math.abs(deltaX) > Math.abs(deltaY) * 1.2) {
      if (deltaX < 0) {
        goToPage(currentPage + 1);
      } else {
        goToPage(currentPage - 1);
      }
    }
  }, { passive: true });

  window.addEventListener("resize", () => {
    updateDeckPages();
  });

  updateDeckPages();
}



/* ============================================================
   SEAMLESS CINEMATIC FILM STRIP CLONING ENGINE
   ============================================================ */

function initFilmStripSeamlessLoop() {
  const rows = document.querySelectorAll(".film-strip-row");
  if (!rows.length) return;

  rows.forEach((row) => {
    const track = row.querySelector(".film-strip-track");
    if (!track) return;

    const originalCards = Array.from(track.children).filter(
      (child) => !child.hasAttribute("data-film-clone")
    );

    if (originalCards.length <= 1) {
      row.classList.add("film-row--static");
      return;
    }

    originalCards.forEach((card) => {
      const clone = card.cloneNode(true);
      clone.setAttribute("data-film-clone", "true");
      clone.setAttribute("aria-hidden", "true");

      const trigger = clone.querySelector(".film-photo-trigger");
      if (trigger) {
        trigger.setAttribute("tabindex", "-1");
        trigger.setAttribute("aria-hidden", "true");
      }

      track.appendChild(clone);
    });
  });
}

/* ============================================================
   SCRAPBOOK LIGHTBOX WITH 3D POLAROID STACK & METADATA MOTION
   ============================================================ */

function initScrapbookLightbox() {
  const lightbox = document.getElementById("scrapbook-lightbox");
  if (!lightbox) return;

  const stackContainer = document.getElementById("scrapbook-viewer-stack");
  const contentPanel = document.getElementById("scrapbook-lightbox-content");
  const categoryEl = document.getElementById("scrapbook-lightbox-category");
  const dateEl = document.getElementById("scrapbook-lightbox-date");
  const counterEl = document.getElementById("scrapbook-lightbox-counter");
  const thumbPreview = document.getElementById("scrapbook-lightbox-thumb");
  const thumbImg = document.getElementById("scrapbook-lightbox-thumb-img");
  const titleEl = document.getElementById("scrapbook-lightbox-title");
  const captionEl = document.getElementById("scrapbook-lightbox-caption");
  const closeButton = document.getElementById("scrapbook-lightbox-close");
  const prevButton = document.getElementById("scrapbook-lightbox-prev");
  const nextButton = document.getElementById("scrapbook-lightbox-next");

  let activeTriggers = [];
  let currentIndex = -1;
  let lastFocusedElement = null;
  let isNavigating = false;
  let touchStartX = 0;
  let touchStartY = 0;

  const ROTATIONS = [-4, 3.5, -3, 5, -4.5, 2.5];

  function getCardRotation(index) {
    return ROTATIONS[Math.abs(index) % ROTATIONS.length];
  }

  function refreshTriggers() {
    activeTriggers = Array.from(
      document.querySelectorAll(".scrapbook-photo-trigger")
    ).filter((t) => {
      const polaroid = t.closest(".memory-polaroid");
      if (polaroid && !polaroid.classList.contains("is-revealed")) {
        return false;
      }
      if (t.closest('[data-film-clone="true"]')) {
        return false;
      }
      return Boolean(t.dataset.image);
    });
  }

  function preloadNeighbours() {
    if (!activeTriggers.length) return;
    const nextIdx = (currentIndex + 1) % activeTriggers.length;
    const prevIdx = (currentIndex - 1 + activeTriggers.length) % activeTriggers.length;

    [nextIdx, prevIdx].forEach((idx) => {
      const src = activeTriggers[idx]?.dataset?.image;
      if (src) {
        const img = new Image();
        img.src = src;
      }
    });
  }

  function renderCaptionWords(text) {
    if (!captionEl) return;
    captionEl.setAttribute("aria-label", text || "");
    if (!text) {
      captionEl.innerHTML = "";
      return;
    }
    const words = text.split(/\s+/);
    captionEl.innerHTML = words
      .map((w, i) => {
        const delayIdx = Math.min(i, 20);
        return `<span class="memory-caption-word" style="--word-index: ${delayIdx}" aria-hidden="true">${w}&nbsp;</span>`;
      })
      .join("");
  }

  function createPolaroidCardHTML(trigger, cardStateClass, index) {
    const src = trigger?.dataset?.image || "";
    const titleText = trigger?.dataset?.title || "Scrapbook Memory";
    const rot = getCardRotation(index);

    return `
      <div class="scrapbook-stack-card ${cardStateClass}" style="--stack-rotation: ${rot}deg;">
        <div class="lightbox-polaroid-tape" aria-hidden="true"></div>
        <div class="lightbox-polaroid-photo">
          <img src="${src}" alt="${titleText}" class="scrapbook-lightbox-image" />
        </div>
        <div class="lightbox-polaroid-footer">
          <span class="lightbox-polaroid-stamp">CM ’26 ARCHIVE</span>
        </div>
      </div>
    `;
  }

  function renderStack(isEntering = false) {
    if (!stackContainer || !activeTriggers.length) return;

    const total = activeTriggers.length;
    const prevIdx = (currentIndex - 1 + total) % total;
    const nextIdx = (currentIndex + 1) % total;

    const activeTrigger = activeTriggers[currentIndex];
    const prevTrigger = activeTriggers[prevIdx];
    const nextTrigger = activeTriggers[nextIdx];

    const activeState = isEntering ? "is-active is-entering" : "is-active";

    stackContainer.innerHTML = `
      ${createPolaroidCardHTML(prevTrigger, "is-prev", prevIdx)}
      ${createPolaroidCardHTML(nextTrigger, "is-next", nextIdx)}
      ${createPolaroidCardHTML(activeTrigger, activeState, currentIndex)}
    `;
  }

  function displayMemory(trigger, isNav = false) {
    if (!trigger) return;

    // 1. Polaroid Stack Render
    renderStack(isNav);

    // 2. Right Panel Exit & Entrance Motion
    if (contentPanel && isNav) {
      contentPanel.classList.add("is-exiting");
      if (thumbPreview) thumbPreview.classList.add("is-animating");
      if (counterEl) counterEl.classList.add("is-animating");
    }

    setTimeout(() => {
      // Category & Date
      if (categoryEl) {
        categoryEl.textContent = trigger.dataset.category || "Memory";
      }

      if (dateEl) {
        dateEl.textContent = trigger.dataset.date || "";
        dateEl.style.display = trigger.dataset.date ? "inline-block" : "none";
      }

      // Counter
      if (counterEl && activeTriggers.length) {
        const currentNum = String(currentIndex + 1).padStart(2, "0");
        const totalNum = String(activeTriggers.length).padStart(2, "0");
        counterEl.textContent = `${currentNum} / ${totalNum}`;
        counterEl.classList.remove("is-animating");
      }

      // Thumbnail
      if (thumbImg && trigger.dataset.image) {
        thumbImg.src = trigger.dataset.image;
        thumbImg.alt = trigger.dataset.title || "";
      }
      if (thumbPreview) {
        thumbPreview.classList.remove("is-animating");
      }

      // Title
      if (titleEl) {
        titleEl.textContent = trigger.dataset.title || "Untitled Memory";
      }

      // Caption Word Reveal
      renderCaptionWords(trigger.dataset.caption || "");

      if (contentPanel) {
        contentPanel.classList.remove("is-exiting");
      }
    }, isNav ? 140 : 0);

    preloadNeighbours();
  }

  function openLightbox(trigger) {
    refreshTriggers();

    currentIndex = activeTriggers.indexOf(trigger);
    if (currentIndex === -1) {
      activeTriggers.push(trigger);
      currentIndex = activeTriggers.length - 1;
    }

    lastFocusedElement = document.activeElement;

    displayMemory(trigger, false);

    lightbox.hidden = false;

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        lightbox.classList.add("is-open");
        lightbox.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
        closeButton?.focus();
      });
    });
  }

  function openNext() {
    if (isNavigating) return;
    refreshTriggers();
    if (!activeTriggers.length) return;

    isNavigating = true;
    currentIndex = (currentIndex + 1) % activeTriggers.length;
    displayMemory(activeTriggers[currentIndex], true);

    setTimeout(() => {
      isNavigating = false;
    }, 380);
  }

  function openPrev() {
    if (isNavigating) return;
    refreshTriggers();
    if (!activeTriggers.length) return;

    isNavigating = true;
    currentIndex = (currentIndex - 1 + activeTriggers.length) % activeTriggers.length;
    displayMemory(activeTriggers[currentIndex], true);

    setTimeout(() => {
      isNavigating = false;
    }, 380);
  }

  function closeLightbox() {
    lightbox.classList.remove("is-open");
    lightbox.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";

    setTimeout(() => {
      lightbox.hidden = true;
      if (stackContainer) stackContainer.innerHTML = "";
      if (lastFocusedElement && typeof lastFocusedElement.focus === "function") {
        lastFocusedElement.focus();
      }
    }, 320);
  }

  // Click Trigger Listener
  document.addEventListener("click", (event) => {
    const trigger = event.target.closest(".scrapbook-photo-trigger");
    if (!trigger) return;

    const polaroid = trigger.closest(".memory-polaroid");
    if (polaroid && !polaroid.classList.contains("is-revealed")) {
      return;
    }

    event.preventDefault();
    openLightbox(trigger);
  });

  // Controls Listeners
  closeButton?.addEventListener("click", closeLightbox);

  prevButton?.addEventListener("click", (event) => {
    event.stopPropagation();
    openPrev();
  });

  nextButton?.addEventListener("click", (event) => {
    event.stopPropagation();
    openNext();
  });

  lightbox.querySelectorAll("[data-lightbox-close]").forEach((element) => {
    element.addEventListener("click", closeLightbox);
  });

  // Keyboard Navigation
  document.addEventListener("keydown", (event) => {
    if (!lightbox.classList.contains("is-open")) return;

    if (event.key === "Escape") {
      closeLightbox();
    } else if (event.key === "ArrowRight") {
      openNext();
    } else if (event.key === "ArrowLeft") {
      openPrev();
    }
  });

  // Touch Swipe Listener
  const dialog = lightbox.querySelector(".scrapbook-lightbox-dialog");
  if (dialog) {
    dialog.addEventListener(
      "touchstart",
      (e) => {
        if (e.touches.length === 1) {
          touchStartX = e.touches[0].clientX;
          touchStartY = e.touches[0].clientY;
        }
      },
      { passive: true }
    );

    dialog.addEventListener(
      "touchend",
      (e) => {
        if (!e.changedTouches.length) return;
        const deltaX = e.changedTouches[0].clientX - touchStartX;
        const deltaY = e.changedTouches[0].clientY - touchStartY;

        if (Math.abs(deltaX) > 45 && Math.abs(deltaX) > Math.abs(deltaY)) {
          if (deltaX < 0) {
            openNext();
          } else {
            openPrev();
          }
        }
      },
      { passive: true }
    );
  }
}



/* ============================================================
   FINAL MEMORY ENVELOPE
   ============================================================ */

function initFinalMemoryEnvelope() {
  const envelope =
    document.getElementById(
      "last-page-envelope"
    );


  const openButton =
    document.getElementById(
      "envelope-open-btn"
    );


  if (
    !envelope ||
    !openButton
  ) {
    return;
  }


  openButton.addEventListener(
    "click",
    () => {
      envelope.classList.add(
        "is-open"
      );


      openButton.setAttribute(
        "aria-expanded",
        "true"
      );
    }
  );
}