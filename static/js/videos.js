(() => {
  "use strict";

  const VOLUME_KEY = "es26-vmp-volume";
  const MUTE_KEY = "es26-vmp-muted";
  const HIDE_DELAY_MS = 2500;
  const SEEK_STEP = 10;
  const VOLUME_STEP = 0.1;

  document.addEventListener("DOMContentLoaded", () => {
    initVideoFilters();
    initVideoPlayer();
    initVideoLoadMore();
  });

  /* --------------------------------------------------------------------------
     1. VIDEO CATEGORY FILTERS
     -------------------------------------------------------------------------- */
  function initVideoFilters() {
    const buttons = Array.from(document.querySelectorAll("[data-vm-filter]"));
    if (!buttons.length) return;

    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        const filter = button.dataset.vmFilter || "all";
        buttons.forEach((item) => {
          const active = item === button;
          item.classList.toggle("vm-active", active);
          item.setAttribute("aria-pressed", String(active));
        });
        /*
         * Read cards live from DOM so newly loaded cards are included.
         */
        const cards = Array.from(document.querySelectorAll(".vm-card"));
        cards.forEach((card) => {
          const category = card.dataset.vmCategory || "uncategorized";
          card.hidden = filter !== "all" && category !== filter;
        });
      });
    });
  }

  /* --------------------------------------------------------------------------
     2. VIDEO LOAD MORE (AJAX Server-Side Pagination)
     -------------------------------------------------------------------------- */
  function initVideoLoadMore() {
    const loadMoreBtn = document.getElementById("vm-load-more");
    const grid = document.getElementById("vm-grid");

    if (!loadMoreBtn || !grid) {
      return;
    }

    loadMoreBtn.addEventListener("click", (event) => {
      event.preventDefault();

      if (loadMoreBtn.disabled) {
        return;
      }

      const hasMore = grid.dataset.hasMore === "true";
      const nextPage = parseInt(grid.dataset.nextPage, 10);
      const apiUrl = grid.dataset.apiUrl || "/videos/page/";

      if (!hasMore || isNaN(nextPage)) {
        loadMoreBtn.hidden = true;
        return;
      }

      loadMoreBtn.disabled = true;
      loadMoreBtn.textContent = "Loading…";

      const url = new URL(apiUrl, window.location.origin);
      url.searchParams.set("page", nextPage);

      fetch(url.toString(), {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`Videos API returned ${response.status}`);
          }
          return response.json();
        })
        .then((data) => {
          const videos = data.videos || [];

          /*
           * Find the active category filter (if any) so newly
           * appended cards respect the current filter state.
           */
          const activeFilterBtn = document.querySelector(
            "[data-vm-filter].vm-active"
          );
          const activeFilter =
            activeFilterBtn
              ? activeFilterBtn.dataset.vmFilter || "all"
              : "all";

          /*
           * Track current card count for numbering offset.
           */
          const existingCount = document.querySelectorAll(".vm-card").length;

          videos.forEach((video, idx) => {
            const card = buildVideoCard(video, existingCount + idx);
            /*
             * Apply active filter immediately to new cards.
             */
            if (
              activeFilter !== "all" &&
              card.dataset.vmCategory !== activeFilter
            ) {
              card.hidden = true;
            }
            grid.appendChild(card);
          });

          /*
           * Update grid pagination state.
           */
          grid.dataset.hasMore = data.has_more ? "true" : "false";
          grid.dataset.nextPage = data.next_page || "";

          if (data.has_more) {
            loadMoreBtn.disabled = false;
            loadMoreBtn.textContent = "Load More Videos";
            loadMoreBtn.hidden = false;
          } else {
            loadMoreBtn.hidden = true;
          }
        })
        .catch((error) => {
          console.error("[Videos] Load More failed:", error);
          loadMoreBtn.disabled = false;
          loadMoreBtn.textContent = "Load More Videos";
        });
    });
  }

  /* --------------------------------------------------------------------------
     VIDEO CARD BUILDER
     -------------------------------------------------------------------------- */
  function escapeAttrV(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function escapeHtmlV(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function buildVideoCard(video, indexInGrid) {
    const article = document.createElement("article");
    article.className = "vm-card";
    article.dataset.vmCategory = video.category_slug || "uncategorized";

    const thumbHtml = video.thumbnail_url
      ? `<img class="vm-thumb" src="${escapeAttrV(video.thumbnail_url)}" alt="${escapeAttrV(video.title)}" loading="lazy">`
      : `<div class="vm-placeholder">
           <span class="vm-placeholder-icon">▶</span>
           <span class="vm-placeholder-text">Video Memory</span>
         </div>`;

    const featuredHtml = video.is_featured
      ? `<span class="vm-featured">★ Featured</span>`
      : "";

    const durationHtml = video.duration
      ? `<span class="vm-duration">${escapeHtmlV(video.duration)}</span>`
      : "";

    const descHtml = video.description
      ? `<p class="vm-description">${escapeHtmlV(video.description)}</p>`
      : "";

    const numStr = String(indexInGrid + 1).padStart(2, "0");

    article.innerHTML = `
      <button
        type="button"
        class="vm-thumb-btn"
        data-vm-open
        data-vm-src="${escapeAttrV(video.video_url)}"
        data-vm-title="${escapeAttrV(video.title)}"
        data-vm-category="${escapeAttrV(video.category_name)}"
        data-vm-date="${escapeAttrV(video.created_at)}"
        data-vm-desc="${escapeAttrV(video.description)}"
        data-vm-poster="${escapeAttrV(video.thumbnail_url)}"
        data-vm-index="${indexInGrid}"
      >
        ${thumbHtml}
        <div class="vm-overlay"></div>
        <span class="vm-play" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M8 6.5v11l9-5.5-9-5.5Z" fill="currentColor" />
          </svg>
        </span>
        ${featuredHtml}
        ${durationHtml}
      </button>
      <div class="vm-body">
        <div class="vm-meta">
          <span class="vm-category">${escapeHtmlV(video.category_name)}</span>
          <span class="vm-number">${numStr}</span>
        </div>
        <h2 class="vm-title">${escapeHtmlV(video.title)}</h2>
        ${descHtml}
        <button
          type="button"
          class="vm-watch"
          data-vm-open
          data-vm-src="${escapeAttrV(video.video_url)}"
          data-vm-title="${escapeAttrV(video.title)}"
          data-vm-category="${escapeAttrV(video.category_name)}"
          data-vm-date="${escapeAttrV(video.created_at)}"
          data-vm-desc="${escapeAttrV(video.description)}"
          data-vm-poster="${escapeAttrV(video.thumbnail_url)}"
          data-vm-index="${indexInGrid}"
        >
          Watch Memory <span aria-hidden="true">→</span>
        </button>
      </div>
    `;

    return article;
  }

  /* --------------------------------------------------------------------------
     2. STANDARDIZED SPLIT-SHELL FULL-CONTROL VIDEO PLAYER (GALLERY UI REFERENCE)
     -------------------------------------------------------------------------- */
  function initVideoPlayer() {
    const modal = document.getElementById("vm-modal");
    const shell = document.getElementById("vmp-shell");
    const player = document.getElementById("vmp-player");
    const stage = document.getElementById("vmp-stage");
    const video = document.getElementById("vm-player");
    const loader = document.getElementById("vmp-loader");
    const errorBox = document.getElementById("vmp-error");
    const retryBtn = document.getElementById("vmp-retry");

    // Sidebar Info Metadata
    const titleEl = document.getElementById("vmp-info-title");
    const categoryEl = document.getElementById("vmp-info-category");
    const dateEl = document.getElementById("vmp-info-date");
    const descEl = document.getElementById("vmp-info-description");
    const previewThumb = document.getElementById("vmp-preview-thumb");
    const counterEl = document.getElementById("vmp-counter");
    const prevBtn = document.getElementById("vmp-prev-btn");
    const nextBtn = document.getElementById("vmp-next-btn");
    const thumbRail = document.getElementById("vmp-thumbs");

    // Video Player Controls
    const centerBtn = document.getElementById("vmp-center");
    const playBtn = document.getElementById("vmp-play");
    const backBtn = document.getElementById("vmp-back");
    const fwdBtn = document.getElementById("vmp-fwd");
    const progress = document.getElementById("vmp-progress");
    const playedEl = document.getElementById("vmp-played");
    const bufferedEl = document.getElementById("vmp-buffered");
    const handleEl = document.getElementById("vmp-handle");
    const timeCurrent = document.getElementById("vmp-time-current");
    const timeDuration = document.getElementById("vmp-time-duration");
    const muteBtn = document.getElementById("vmp-mute");
    const volumeSlider = document.getElementById("vmp-volume-slider");
    const speedBtn = document.getElementById("vmp-speed");
    const speedMenu = document.getElementById("vmp-speed-menu");
    const speedLabel = document.getElementById("vmp-speed-label");
    const pipBtn = document.getElementById("vmp-pip");
    const fsBtn = document.getElementById("vmp-fs");
    const closeBtn = document.getElementById("vm-modal-close");

    if (!modal || !player || !video) return;

    let playlist = [];
    let currentIndex = 0;
    let lastTrigger = null;
    let hideTimer = null;
    let isDragging = false;
    let lastVolume = readStoredNumber(VOLUME_KEY, 0.85);

    // Collect all video card items on page
    function collectPlaylist() {
      const cards = Array.from(document.querySelectorAll(".vm-card:not([hidden])"));
      const targetCards = cards.length ? cards : Array.from(document.querySelectorAll(".vm-card"));
      
      playlist = targetCards.map((card, idx) => {
        const btn = card.querySelector("[data-vm-open]") || card;
        return {
          src: btn.dataset.vmSrc || "",
          title: btn.dataset.vmTitle || "Video Memory",
          category: btn.dataset.vmCategory || "Memory",
          date: btn.dataset.vmDate || "",
          desc: btn.dataset.vmDesc || "",
          poster: btn.dataset.vmPoster || "",
          index: idx,
        };
      }).filter((item) => Boolean(item.src));
    }

    // Initial PiP Feature Support Check
    if (!document.pictureInPictureEnabled || typeof video.requestPictureInPicture !== "function") {
      if (pipBtn) pipBtn.hidden = true;
    }

    restoreVolume();

    // Attach Open Event Listeners
    document.addEventListener("click", (e) => {
      const openBtn = e.target.closest("[data-vm-open]");
      if (openBtn) {
        e.preventDefault();
        collectPlaylist();
        const src = openBtn.dataset.vmSrc;
        const matchedIdx = playlist.findIndex((item) => item.src === src);
        openModal(matchedIdx >= 0 ? matchedIdx : 0, openBtn);
      }
    });

    // Close Listener
    closeBtn?.addEventListener("click", (e) => {
      e.preventDefault();
      closeModal();
    });

    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        closeModal();
      }
    });

    // Playlist Navigation (Previous / Next)
    prevBtn?.addEventListener("click", (e) => {
      e.preventDefault();
      navigatePlaylist(-1);
    });

    nextBtn?.addEventListener("click", (e) => {
      e.preventDefault();
      navigatePlaylist(1);
    });

    // Thumbnail Rail Clicks
    thumbRail?.addEventListener("click", (e) => {
      const thumbBtn = e.target.closest("[data-vmp-thumb-idx]");
      if (thumbBtn) {
        e.preventDefault();
        const idx = parseInt(thumbBtn.dataset.vmpThumbIdx, 10);
        if (!isNaN(idx) && idx >= 0 && idx < playlist.length) {
          goToIndex(idx);
        }
      }
    });

    // Playback Buttons
    centerBtn?.addEventListener("click", (e) => {
      e.stopPropagation();
      togglePlayback();
      revealChrome();
    });

    playBtn?.addEventListener("click", (e) => {
      e.stopPropagation();
      togglePlayback();
      revealChrome();
    });

    // Skip Buttons (+-10s)
    backBtn?.addEventListener("click", (e) => {
      e.stopPropagation();
      seekRelative(-SEEK_STEP);
      revealChrome();
    });

    fwdBtn?.addEventListener("click", (e) => {
      e.stopPropagation();
      seekRelative(SEEK_STEP);
      revealChrome();
    });

    // Volume & Mute Controls
    muteBtn?.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleMute();
      revealChrome();
    });

    volumeSlider?.addEventListener("input", () => {
      const val = clamp(parseFloat(volumeSlider.value), 0, 1);
      video.muted = val === 0;
      video.volume = val;
      if (val > 0) lastVolume = val;
      persistVolume();
      syncVolumeUI();
      revealChrome();
    });

    // Speed Selector Menu
    speedBtn?.addEventListener("click", (e) => {
      e.stopPropagation();
      const isOpen = Boolean(speedMenu && !speedMenu.hidden);
      setSpeedMenu(!isOpen);
      revealChrome();
    });

    speedMenu?.querySelectorAll(".vmp-speed-opt").forEach((opt) => {
      opt.addEventListener("click", (e) => {
        e.stopPropagation();
        const speed = parseFloat(opt.dataset.speed || "1");
        if (!Number.isFinite(speed)) return;
        video.playbackRate = speed;
        if (speedLabel) speedLabel.textContent = `${speed}x`;
        speedMenu.querySelectorAll(".vmp-speed-opt").forEach((item) => {
          item.classList.toggle("is-active", item === opt);
        });
        setSpeedMenu(false);
        revealChrome();
      });
    });

    // Picture-in-Picture
    pipBtn?.addEventListener("click", async (e) => {
      e.stopPropagation();
      try {
        if (document.pictureInPictureElement) {
          await document.exitPictureInPicture();
        } else if (document.pictureInPictureEnabled) {
          await video.requestPictureInPicture();
        }
      } catch (err) {
        console.warn("PiP Error:", err);
      }
      revealChrome();
    });

    // Fullscreen
    fsBtn?.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleFullscreen();
      revealChrome();
    });

    // Retry Button
    retryBtn?.addEventListener("click", (e) => {
      e.stopPropagation();
      if (playlist[currentIndex]) loadCurrentVideo(true);
    });

    // Stage Tap / Click Playback Interaction
    stage?.addEventListener("click", (e) => {
      if (e.target.closest("button, .vmp-controls, .vmp-error")) return;
      togglePlayback();
      revealChrome();
    });

    // Auto-hide User Activity Handlers
    player.addEventListener("mousemove", () => revealChrome());
    player.addEventListener("pointerdown", () => revealChrome());
    player.addEventListener("mouseleave", () => {
      if (!video.paused && !video.ended) armHideTimer();
    });

    // Seek / Progress Scrubbing
    progress?.addEventListener("pointerdown", (e) => {
      if (!Number.isFinite(video.duration) || video.duration <= 0) return;
      isDragging = true;
      progress.classList.add("is-dragging");
      progress.setPointerCapture?.(e.pointerId);
      seekFromPointer(e);
      revealChrome();
      e.preventDefault();
    });

    progress?.addEventListener("pointermove", (e) => {
      if (!isDragging) return;
      seekFromPointer(e);
      e.preventDefault();
    });

    ["pointerup", "pointercancel"].forEach((type) => {
      progress?.addEventListener(type, (e) => {
        if (!isDragging) return;
        isDragging = false;
        progress.classList.remove("is-dragging");
        try {
          progress.releasePointerCapture?.(e.pointerId);
        } catch (_) {}
        revealChrome();
      });
    });

    // Video Lifecycle Events
    video.addEventListener("loadedmetadata", () => {
      setLoading(false);
      syncTime();
    });

    video.addEventListener("timeupdate", syncTime);
    video.addEventListener("durationchange", syncTime);
    video.addEventListener("progress", syncBuffered);
    video.addEventListener("volumechange", syncVolumeUI);

    video.addEventListener("waiting", () => setLoading(true));
    video.addEventListener("canplay", () => setLoading(false));

    video.addEventListener("play", () => {
      player.classList.add("is-playing");
      player.classList.remove("is-paused", "is-ended");
      syncPlayUI();
      armHideTimer();
    });

    video.addEventListener("pause", () => {
      if (!video.ended) {
        player.classList.add("is-paused");
        player.classList.remove("is-playing");
      }
      syncPlayUI();
      revealChrome();
    });

    video.addEventListener("ended", () => {
      player.classList.add("is-ended", "is-paused", "is-chrome-visible");
      player.classList.remove("is-playing");
      syncPlayUI();
      clearHideTimer();
    });

    video.addEventListener("error", () => {
      setLoading(false);
      if (errorBox) errorBox.hidden = false;
      syncPlayUI();
    });

    // Global Keydown Handler
    document.addEventListener("keydown", (e) => {
      if (modal.hidden) return;
      const tag = e.target?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea") return;

      const key = e.key;
      if (key === "Escape") {
        e.preventDefault();
        if (getFullscreenElement()) {
          exitFullscreen();
        } else {
          closeModal();
        }
      } else if (key === " " || key.toLowerCase() === "k") {
        e.preventDefault();
        togglePlayback();
        revealChrome();
      } else if (key === "ArrowLeft") {
        if (e.shiftKey) {
          e.preventDefault();
          navigatePlaylist(-1);
        } else {
          e.preventDefault();
          seekRelative(-SEEK_STEP);
          revealChrome();
        }
      } else if (key === "ArrowRight") {
        if (e.shiftKey) {
          e.preventDefault();
          navigatePlaylist(1);
        } else {
          e.preventDefault();
          seekRelative(SEEK_STEP);
          revealChrome();
        }
      } else if (key === "ArrowUp") {
        e.preventDefault();
        setVolume(video.volume + VOLUME_STEP);
        revealChrome();
      } else if (key === "ArrowDown") {
        e.preventDefault();
        setVolume(video.volume - VOLUME_STEP);
        revealChrome();
      } else if (key.toLowerCase() === "m") {
        e.preventDefault();
        toggleMute();
        revealChrome();
      } else if (key.toLowerCase() === "f") {
        e.preventDefault();
        toggleFullscreen();
      }
    });

    // Fullscreen Listeners
    document.addEventListener("fullscreenchange", syncFullscreenUI);
    document.addEventListener("webkitfullscreenchange", syncFullscreenUI);

    document.addEventListener("click", (e) => {
      if (modal.hidden) return;
      if (!e.target.closest("#vmp-speed-wrap")) setSpeedMenu(false);
    });

    /* ------------------------------------------------------------------------
       CORE MODAL & PLAYLIST FUNCTIONS
       ------------------------------------------------------------------------ */
    function openModal(index, trigger) {
      if (!playlist.length) collectPlaylist();
      if (!playlist.length) return;

      lastTrigger = trigger || null;
      currentIndex = clamp(index, 0, playlist.length - 1);

      modal.hidden = false;
      modal.classList.add("active");
      document.documentElement.classList.add("vmp-open");
      document.body.style.overflow = "hidden";

      syncSidebarMetadata();
      loadCurrentVideo(true);
      revealChrome();

      requestAnimationFrame(() => {
        player.focus({ preventScroll: true });
      });
    }

    async function closeModal() {
      if (getFullscreenElement()) {
        await exitFullscreen();
      }

      video.pause();
      try {
        video.currentTime = 0;
      } catch (_) {}
      video.removeAttribute("src");
      video.load();

      modal.hidden = true;
      modal.classList.remove("active");
      document.documentElement.classList.remove("vmp-open");
      document.body.style.overflow = "";
      resetPlayerState();

      if (lastTrigger && typeof lastTrigger.focus === "function") {
        lastTrigger.focus({ preventScroll: true });
      }
    }

    function navigatePlaylist(direction) {
      if (!playlist.length) return;
      const total = playlist.length;
      currentIndex = (currentIndex + direction + total) % total;
      syncSidebarMetadata();
      loadCurrentVideo(true);
    }

    function goToIndex(idx) {
      if (idx < 0 || idx >= playlist.length) return;
      currentIndex = idx;
      syncSidebarMetadata();
      loadCurrentVideo(true);
    }

    function syncSidebarMetadata() {
      const item = playlist[currentIndex];
      if (!item) return;

      if (titleEl) titleEl.textContent = item.title;
      if (categoryEl) categoryEl.textContent = item.category.toUpperCase();
      if (dateEl) dateEl.textContent = item.date || "";
      if (descEl) descEl.textContent = item.desc || "A cherished moment from our college journey.";

      if (counterEl) {
        const cur = String(currentIndex + 1).padStart(2, "0");
        const tot = String(playlist.length).padStart(2, "0");
        counterEl.textContent = `${cur} / ${tot}`;
      }

      if (previewThumb) {
        if (item.poster) {
          previewThumb.src = item.poster;
          previewThumb.hidden = false;
        } else {
          previewThumb.hidden = true;
        }
      }

      // Update active thumbnail rail
      if (thumbRail) {
        const thumbBtns = Array.from(thumbRail.querySelectorAll("[data-vmp-thumb-idx]"));
        thumbBtns.forEach((btn, i) => {
          const isActive = i === currentIndex;
          btn.classList.toggle("active", isActive);
          if (isActive) {
            btn.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
          }
        });
      }
    }

    function loadCurrentVideo(autoplay) {
      const item = playlist[currentIndex];
      if (!item || !item.src) return;

      if (errorBox) errorBox.hidden = true;
      setLoading(true);
      video.pause();
      video.src = item.src;
      video.load();

      if (autoplay) {
        const promise = video.play();
        if (promise && typeof promise.catch === "function") {
          promise.catch(() => {
            player.classList.add("is-paused");
            player.classList.remove("is-playing");
            syncPlayUI();
            revealChrome();
          });
        }
      }
    }

    function resetPlayerState() {
      player.classList.remove("is-playing", "is-ended");
      player.classList.add("is-paused", "is-chrome-visible");
      video.playbackRate = 1;
      if (speedLabel) speedLabel.textContent = "1x";
      speedMenu?.querySelectorAll(".vmp-speed-opt").forEach((opt) => {
        opt.classList.toggle("is-active", opt.dataset.speed === "1");
      });
      if (errorBox) errorBox.hidden = true;
      setLoading(false);
      setSpeedMenu(false);
      syncPlayUI();
      updateProgressUI(0);
      if (timeCurrent) timeCurrent.textContent = "00:00";
      if (timeDuration) timeDuration.textContent = "00:00";
    }

    function togglePlayback() {
      if (video.paused || video.ended) {
        if (video.ended) {
          try {
            video.currentTime = 0;
          } catch (_) {}
        }
        const promise = video.play();
        if (promise && typeof promise.catch === "function") {
          promise.catch(() => {
            player.classList.add("is-paused");
            player.classList.remove("is-playing");
            syncPlayUI();
            revealChrome();
          });
        }
      } else {
        video.pause();
      }
    }

    function seekRelative(seconds) {
      if (!Number.isFinite(video.duration)) return;
      video.currentTime = clamp(video.currentTime + seconds, 0, video.duration);
      syncTime();
    }

    function seekFromPointer(e) {
      if (!progress || !Number.isFinite(video.duration) || video.duration <= 0) return;
      const rect = progress.getBoundingClientRect();
      if (rect.width <= 0) return;
      const ratio = clamp((e.clientX - rect.left) / rect.width, 0, 1);
      video.currentTime = ratio * video.duration;
      syncTime();
    }

    function setVolume(value) {
      const next = clamp(value, 0, 1);
      video.muted = next === 0;
      video.volume = next;
      if (next > 0) lastVolume = next;
      persistVolume();
      syncVolumeUI();
    }

    function toggleMute() {
      if (video.muted || video.volume === 0) {
        video.muted = false;
        video.volume = lastVolume > 0 ? lastVolume : 0.85;
      } else {
        if (video.volume > 0) lastVolume = video.volume;
        video.muted = true;
      }
      persistVolume();
      syncVolumeUI();
    }

    function restoreVolume() {
      const muted = readStoredBool(MUTE_KEY, false);
      video.volume = clamp(lastVolume, 0, 1);
      video.muted = muted;
      if (volumeSlider) volumeSlider.value = String(video.volume);
      syncVolumeUI();
    }

    function persistVolume() {
      try {
        localStorage.setItem(VOLUME_KEY, String(video.volume));
        localStorage.setItem(MUTE_KEY, String(video.muted));
      } catch (_) {}
    }

    function syncPlayUI() {
      const isPlaying = !video.paused && !video.ended;
      const isEnded = video.ended;

      toggleElement(playBtn?.querySelector(".vmp-icon-play"), !isPlaying);
      toggleElement(playBtn?.querySelector(".vmp-icon-pause"), isPlaying);
      toggleElement(centerBtn?.querySelector(".vmp-icon-play"), !isEnded);
      toggleElement(centerBtn?.querySelector(".vmp-icon-replay"), isEnded);

      playBtn?.setAttribute("aria-label", isPlaying ? "Pause video" : isEnded ? "Replay video" : "Play video");
      centerBtn?.setAttribute("aria-label", isEnded ? "Replay video" : isPlaying ? "Pause video" : "Play video");
    }

    function syncTime() {
      const dur = Number.isFinite(video.duration) ? video.duration : 0;
      const cur = Number.isFinite(video.currentTime) ? video.currentTime : 0;
      const pct = dur > 0 ? (cur / dur) * 100 : 0;

      if (timeCurrent) timeCurrent.textContent = formatTime(cur);
      if (timeDuration) timeDuration.textContent = formatTime(dur);
      updateProgressUI(pct);

      progress?.setAttribute("aria-valuemax", String(Math.round(dur) || 100));
      progress?.setAttribute("aria-valuenow", String(Math.round(cur)));
    }

    function updateProgressUI(percent) {
      const safe = clamp(percent, 0, 100);
      if (playedEl) playedEl.style.width = `${safe}%`;
      if (handleEl) handleEl.style.left = `${safe}%`;
    }

    function syncBuffered() {
      if (!bufferedEl || !video.buffered.length || !Number.isFinite(video.duration) || video.duration <= 0) {
        return;
      }
      const end = video.buffered.end(video.buffered.length - 1);
      bufferedEl.style.width = `${clamp((end / video.duration) * 100, 0, 100)}%`;
    }

    function syncVolumeUI() {
      const isMuted = video.muted || video.volume === 0;
      const isLow = !isMuted && video.volume < 0.45;

      toggleElement(muteBtn?.querySelector(".vmp-vol-high"), !isMuted && !isLow);
      toggleElement(muteBtn?.querySelector(".vmp-vol-low"), isLow);
      toggleElement(muteBtn?.querySelector(".vmp-vol-mute"), isMuted);

      muteBtn?.setAttribute("aria-label", isMuted ? "Unmute video" : "Mute video");
      muteBtn?.setAttribute("aria-pressed", String(isMuted));
      if (volumeSlider && !isDragging) {
        volumeSlider.value = String(isMuted ? 0 : video.volume);
      }
    }

    function syncFullscreenUI() {
      const isFs = Boolean(getFullscreenElement());
      toggleElement(fsBtn?.querySelector(".vmp-fs-enter"), !isFs);
      toggleElement(fsBtn?.querySelector(".vmp-fs-exit"), isFs);
      fsBtn?.setAttribute("aria-label", isFs ? "Exit fullscreen" : "Enter fullscreen");
    }

    async function toggleFullscreen() {
      try {
        if (getFullscreenElement()) {
          await exitFullscreen();
        } else if (player.requestFullscreen) {
          await player.requestFullscreen();
        } else if (player.webkitRequestFullscreen) {
          player.webkitRequestFullscreen();
        } else if (video.webkitEnterFullscreen) {
          video.webkitEnterFullscreen();
        }
      } catch (err) {
        console.warn("Fullscreen Error:", err);
      }
    }

    function getFullscreenElement() {
      return document.fullscreenElement || document.webkitFullscreenElement || null;
    }

    async function exitFullscreen() {
      try {
        if (document.exitFullscreen) await document.exitFullscreen();
        else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
      } catch (_) {}
    }

    function setSpeedMenu(open) {
      if (!speedMenu || !speedBtn) return;
      speedMenu.hidden = !open;
      speedBtn.setAttribute("aria-expanded", String(open));
    }

    function setLoading(active) {
      if (loader) loader.hidden = !active;
    }

    function revealChrome() {
      player.classList.add("is-chrome-visible");
      if (video.paused || video.ended) {
        clearHideTimer();
        return;
      }
      armHideTimer();
    }

    function armHideTimer() {
      clearHideTimer();
      hideTimer = window.setTimeout(() => {
        if (!video.paused && !video.ended) {
          player.classList.remove("is-chrome-visible");
          setSpeedMenu(false);
        }
      }, HIDE_DELAY_MS);
    }

    function clearHideTimer() {
      if (hideTimer) {
        window.clearTimeout(hideTimer);
        hideTimer = null;
      }
    }
  }

  /* --------------------------------------------------------------------------
     UTILITY HELPERS
     -------------------------------------------------------------------------- */
  function toggleElement(el, show) {
    if (el) el.hidden = !show;
  }

  function formatTime(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return "00:00";
    const whole = Math.floor(seconds);
    const hours = Math.floor(whole / 3600);
    const minutes = Math.floor((whole % 3600) / 60);
    const secs = String(whole % 60).padStart(2, "0");
    if (hours > 0) {
      return `${hours}:${String(minutes).padStart(2, "0")}:${secs}`;
    }
    return `${String(minutes).padStart(2, "0")}:${secs}`;
  }

  function clamp(val, min, max) {
    return Math.min(max, Math.max(min, val));
  }

  function readStoredNumber(key, fallback) {
    try {
      const val = localStorage.getItem(key);
      const num = parseFloat(val);
      return Number.isFinite(num) ? num : fallback;
    } catch (_) {
      return fallback;
    }
  }

  function readStoredBool(key, fallback) {
    try {
      const val = localStorage.getItem(key);
      if (val === null) return fallback;
      return val === "true";
    } catch (_) {
      return fallback;
    }
  }
})();
