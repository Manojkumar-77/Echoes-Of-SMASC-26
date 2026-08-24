/**
 * College Memories '26 - Home Page JavaScript (home.js)
 * ====================================================
 * 1. Hero slideshow auto-switching with natural aspect-ratio classification.
 * 2. Featured Highlights Best Moments Coverflow Carousel Engine.
 *    - Single Source of Truth architecture (updateCarousel, nextSlide, prevSlide)
 *    - True infinite bidirectional loop: 01 <- PREV -> 10 and 10 <- NEXT -> 01
 *    - Absolute-centered card positioning: translate3d(-50%, -50%, z)
 *    - Touch swipe & desktop mouse drag in both directions with threshold protection
 *    - Continuous autoplay (4800ms delay) with auto-pause on user interaction
 *    - Dynamic fraction counter pill "01 / 10"
 *    - Preserves normal vertical page scrolling (touch-action: pan-y)
 */

document.addEventListener('DOMContentLoaded', () => {
  initHomeHero();
  init3DCoverFlowCarousel();
});

/**
 * 1. Hero Slideshow Controller
 */
function initHomeHero() {
  const slides = Array.from(document.querySelectorAll('[data-home-slide]'));
  const dots = Array.from(document.querySelectorAll('[data-home-slide-dot]'));

  if (!slides.length) return;

  let currentIndex = 0;
  let slideInterval = null;
  let touchStartX = 0;
  let isTransitioning = false;

  // Preload and classify slide images
  slides.forEach((slide, idx) => {
    const img = slide.querySelector('.home-hero-image');
    if (!img) return;

    function applyAspectClass() {
      if (!img.naturalWidth || !img.naturalHeight) return;
      const ratio = img.naturalWidth / img.naturalHeight;

      slide.style.setProperty('--hero-photo-ratio', `${img.naturalWidth} / ${img.naturalHeight}`);
      slide.classList.remove('is-ultrawide', 'is-landscape', 'is-squareish', 'is-portrait', 'is-tall');

      if (ratio >= 1.75) {
        slide.classList.add('is-ultrawide');
      } else if (ratio >= 1.30) {
        slide.classList.add('is-landscape');
      } else if (ratio >= 0.90) {
        slide.classList.add('is-squareish');
      } else if (ratio >= 0.68) {
        slide.classList.add('is-portrait');
      } else {
        slide.classList.add('is-tall');
      }
    }

    if (img.complete && img.naturalWidth) {
      applyAspectClass();
    } else {
      img.addEventListener('load', applyAspectClass, { once: true });
    }
  });

  // Preload adjacent images ahead of time
  function preloadAdjacentSlides(index) {
    const nextIdx = (index + 1) % slides.length;
    const nextImg = slides[nextIdx]?.querySelector('.home-hero-image');
    if (nextImg && !nextImg.complete) {
      if ('decode' in nextImg) {
        nextImg.decode().catch(() => {});
      } else {
        const dummy = new Image();
        dummy.src = nextImg.src;
      }
    }
  }

  function showSlide(index) {
    if (index >= slides.length) index = 0;
    if (index < 0) index = slides.length - 1;
    if (index === currentIndex && slides[currentIndex].classList.contains('is-active')) return;

    const targetSlide = slides[index];
    const targetImg = targetSlide?.querySelector('.home-hero-image');

    // Ensure image is ready before making slide active
    function activateTarget() {
      slides.forEach((slide, i) => {
        if (i === index) {
          slide.classList.add('is-active');
          slide.setAttribute('aria-hidden', 'false');
        } else {
          slide.classList.remove('is-active');
          slide.setAttribute('aria-hidden', 'true');
        }
      });

      dots.forEach((dot, i) => {
        if (i === index) {
          dot.classList.add('is-active');
          dot.setAttribute('aria-selected', 'true');
        } else {
          dot.classList.remove('is-active');
          dot.setAttribute('aria-selected', 'false');
        }
      });

      currentIndex = index;
      isTransitioning = false;
      preloadAdjacentSlides(currentIndex);
    }

    isTransitioning = true;
    if (!targetImg || (targetImg.complete && targetImg.naturalWidth > 0)) {
      if ('decode' in targetImg) {
        targetImg.decode().then(activateTarget).catch(activateTarget);
      } else {
        activateTarget();
      }
    } else {
      targetImg.addEventListener('load', activateTarget, { once: true });
      // Fallback timeout so slideshow never deadlocks
      setTimeout(activateTarget, 800);
    }
  }

  function nextSlide() {
    if (isTransitioning) return;
    showSlide(currentIndex + 1);
  }

  function prevSlide() {
    if (isTransitioning) return;
    showSlide(currentIndex - 1);
  }

  function startSlideshow() {
    if (slides.length <= 1) return;
    stopSlideshow();
    slideInterval = setInterval(nextSlide, 3200);
  }

  function stopSlideshow() {
    if (slideInterval) {
      clearInterval(slideInterval);
      slideInterval = null;
    }
  }

  dots.forEach((dot, idx) => {
    dot.addEventListener('click', () => {
      showSlide(idx);
      startSlideshow();
    });
  });

  const heroSection = document.getElementById('home-hero');
  if (heroSection) {
    heroSection.addEventListener('touchstart', (e) => {
      if (e.touches && e.touches.length === 1) {
        touchStartX = e.touches[0].clientX;
      }
    }, { passive: true });

    heroSection.addEventListener('touchend', (e) => {
      if (!e.changedTouches || !e.changedTouches.length) return;
      const touchEndX = e.changedTouches[0].clientX;
      const deltaX = touchEndX - touchStartX;
      if (Math.abs(deltaX) > 40) {
        if (deltaX < 0) nextSlide();
        else prevSlide();
        startSlideshow();
      }
    }, { passive: true });
  }

  showSlide(0);
  startSlideshow();
}

/**
 * 2. Featured Highlights Best Moments Coverflow Engine
 */
function init3DCoverFlowCarousel() {
  const stage = document.getElementById('home-3d-stage');
  const track = document.getElementById('home-3d-track');
  const cards = Array.from(document.querySelectorAll('[data-3d-slide]'));
  const counterDisplay = document.getElementById('home-3d-counter');

  const prevBtn = document.getElementById('home-3d-prev');
  const nextBtn = document.getElementById('home-3d-next');
  const mobilePrevBtn = document.getElementById('home-3d-mobile-prev');
  const mobileNextBtn = document.getElementById('home-3d-mobile-next');

  if (!stage || !track || !cards.length) return;

  // Prevent duplicate initialization
  if (stage.dataset.carouselInitialized === 'true') return;
  stage.dataset.carouselInitialized = 'true';

  const N = cards.length;
  let activeIndex = 0;

  let dragStartX = 0;
  let dragStartY = 0;
  let dragX = 0;
  let isDragging = false;
  let hasDragged = false;

  let autoplayTimer = null;
  let isUserInteracting = false;
  let rafId = null;

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ------------------------------------------------------------------
     1. Single Source of Truth Index Normalization
     ------------------------------------------------------------------ */
  function wrapIndex(idx, total) {
    return ((idx % total) + total) % total;
  }

  /* ------------------------------------------------------------------
     2. Image Preloader for Smooth Texture Delivery
     ------------------------------------------------------------------ */
  function preloadAdjacentImages(centerIdx) {
    const indicesToPreload = [
      wrapIndex(centerIdx - 1, N),
      wrapIndex(centerIdx, N),
      wrapIndex(centerIdx + 1, N),
      wrapIndex(centerIdx + 2, N),
    ];
    indicesToPreload.forEach(i => {
      const img = cards[i]?.querySelector('img');
      if (img && img.src && !img.complete) {
        const preloader = new Image();
        preloader.src = img.src;
      }
    });
  }

  /* ------------------------------------------------------------------
     3. Batch Carousel Render Cycle (Compositor-Only Transforms)
     ------------------------------------------------------------------ */
  function renderCarousel() {
    if (rafId) cancelAnimationFrame(rafId);

    rafId = requestAnimationFrame(() => {
      activeIndex = wrapIndex(activeIndex, N);

      // Update Counter Pill (e.g. "01 / 15")
      if (counterDisplay) {
        const curFmt = String(activeIndex + 1).padStart(2, '0');
        const totFmt = String(N).padStart(2, '0');
        counterDisplay.textContent = `${curFmt} / ${totFmt}`;
      }

      const stageWidth = stage.clientWidth || window.innerWidth;
      const isMobile = stageWidth <= 640;
      const spread = isMobile ? Math.min(stageWidth * 0.75, 290) : (stageWidth > 1366 ? 340 : (stageWidth > 1024 ? 300 : 260));

      cards.forEach((card, idx) => {
        let offset = idx - activeIndex;

        // Circular Relative Offset Math (15 <-> 01 seamless loop)
        if (N > 2) {
          if (offset > N / 2) offset -= N;
          if (offset < -N / 2) offset += N;
        }

        const absDist = Math.abs(offset);
        const bodyEl = card.querySelector('.home-3d-body');

        if (prefersReducedMotion) {
          const isCurrent = offset === 0;
          card.style.transform = isCurrent ? 'translate3d(-50%, -50%, 0)' : 'translate3d(calc(-50% + 200vw), -50%, 0)';
          card.style.opacity = isCurrent ? '1' : '0';
          card.style.visibility = isCurrent ? 'visible' : 'hidden';
          card.style.zIndex = isCurrent ? '30' : '1';
          card.style.pointerEvents = isCurrent ? 'auto' : 'none';
          if (bodyEl) bodyEl.style.opacity = isCurrent ? '1' : '0';
        } else if (absDist <= (isMobile ? 1.6 : 2.5)) {
          card.style.visibility = 'visible';

          if (offset === 0) {
            // Active Center Slide
            card.style.transform = 'translate3d(-50%, -50%, 0) scale(1) rotateY(0deg)';
            card.style.opacity = '1';
            card.style.zIndex = '30';
            card.style.pointerEvents = 'auto';
            card.classList.add('is-active');
            card.setAttribute('aria-hidden', 'false');
            if (bodyEl) bodyEl.style.opacity = '1';
          } else {
            // Side / Depth Slides
            const translateX = offset * spread;
            const rotateY = -Math.sign(offset) * Math.min(absDist * 10, 18);
            const scale = Math.max(0.82, 1 - absDist * 0.12);
            const opacity = Math.max(0.25, 1 - absDist * 0.48);
            const zIndex = Math.max(1, Math.round(30 - absDist * 10));

            card.style.transform = `translate3d(calc(-50% + ${translateX}px), -50%, -${absDist * 80}px) scale(${scale}) rotateY(${rotateY}deg)`;
            card.style.opacity = String(opacity);
            card.style.zIndex = String(zIndex);
            card.style.pointerEvents = absDist <= 1.1 ? 'auto' : 'none';
            card.classList.remove('is-active');
            card.setAttribute('aria-hidden', 'true');
            if (bodyEl) bodyEl.style.opacity = String(Math.max(0.5, 1 - absDist * 0.8));
          }
        } else {
          // Culled Slides
          card.style.visibility = 'hidden';
          card.style.opacity = '0';
          card.style.pointerEvents = 'none';
          card.style.transform = `translate3d(calc(-50% + ${offset > 0 ? 150 : -150}vw), -50%, -350px)`;
          card.classList.remove('is-active');
          card.setAttribute('aria-hidden', 'true');
          if (bodyEl) bodyEl.style.opacity = '0';
        }
      });

      preloadAdjacentImages(activeIndex);
    });
  }

  /* ------------------------------------------------------------------
     4. Navigation Triggers (Single Source of Truth)
     ------------------------------------------------------------------ */
  function goToIndex(targetIdx) {
    activeIndex = wrapIndex(targetIdx, N);
    renderCarousel();
  }

  function goToNext() {
    goToIndex(activeIndex + 1);
  }

  function goToPrevious() {
    goToIndex(activeIndex - 1);
  }

  /* ------------------------------------------------------------------
     5. Arrow Button Listeners (Never Locked, Always Responsive)
     ------------------------------------------------------------------ */
  [prevBtn, mobilePrevBtn].forEach(btn => {
    if (btn) {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        pauseAutoplay();
        goToPrevious();
      });
    }
  });

  [nextBtn, mobileNextBtn].forEach(btn => {
    if (btn) {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        pauseAutoplay();
        goToNext();
      });
    }
  });

  /* ------------------------------------------------------------------
     6. Side Card Direct Click Listener
     ------------------------------------------------------------------ */
  cards.forEach((card, idx) => {
    card.addEventListener('click', (e) => {
      if (hasDragged) {
        e.preventDefault();
        return;
      }
      if (idx !== activeIndex) {
        e.preventDefault();
        pauseAutoplay();
        goToIndex(idx);
      }
    });
  });

  /* ------------------------------------------------------------------
     7. Reliable Pointer Drag / Touch Swipe Handler
     ------------------------------------------------------------------ */
  stage.addEventListener('pointerdown', (e) => {
    if (e.button && e.button !== 0) return;
    isDragging = true;
    hasDragged = false;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    dragX = 0;
    pauseAutoplay();
  });

  stage.addEventListener('pointermove', (e) => {
    if (!isDragging) return;

    const deltaX = e.clientX - dragStartX;
    const deltaY = e.clientY - dragStartY;

    if (!hasDragged && Math.abs(deltaX) > 8 && Math.abs(deltaX) > Math.abs(deltaY)) {
      hasDragged = true;
    }

    if (hasDragged) {
      dragX = deltaX;
    }
  });

  function handlePointerRelease() {
    if (!isDragging) return;
    isDragging = false;

    if (hasDragged) {
      const threshold = 40;
      if (dragX < -threshold) {
        goToNext();
      } else if (dragX > threshold) {
        goToPrevious();
      }
    }
    dragX = 0;
  }

  stage.addEventListener('pointerup', handlePointerRelease);
  stage.addEventListener('pointercancel', handlePointerRelease);

  /* ------------------------------------------------------------------
     8. Keyboard Navigation
     ------------------------------------------------------------------ */
  stage.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') {
      pauseAutoplay();
      goToPrevious();
    } else if (e.key === 'ArrowRight') {
      pauseAutoplay();
      goToNext();
    }
  });

  /* ------------------------------------------------------------------
     9. Autoplay Engine
     ------------------------------------------------------------------ */
  function startAutoplay() {
    if (N <= 1 || prefersReducedMotion) return;
    stopAutoplay();
    autoplayTimer = setInterval(() => {
      if (!isUserInteracting && !isDragging) {
        goToNext();
      }
    }, 4800);
  }

  function stopAutoplay() {
    if (autoplayTimer) {
      clearInterval(autoplayTimer);
      autoplayTimer = null;
    }
  }

  function pauseAutoplay() {
    isUserInteracting = true;
    stopAutoplay();
    setTimeout(() => {
      isUserInteracting = false;
      startAutoplay();
    }, 8000);
  }

  stage.addEventListener('mouseenter', stopAutoplay);
  stage.addEventListener('mouseleave', startAutoplay);

  window.addEventListener('resize', renderCarousel, { passive: true });

  // Initial render
  goToIndex(0);
  startAutoplay();
}
