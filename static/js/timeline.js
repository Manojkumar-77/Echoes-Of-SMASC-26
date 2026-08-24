/**
 * College Memories '26 - Modular Timeline JavaScript
 * ===================================================
 * Illuminated scroll spine progress tracker, lerp progress interpolation,
 * node activation, category filtering, and Vertical Thumbnail Viewer.
 */

document.addEventListener('DOMContentLoaded', () => {
  initTimelineSpine();
  initTimelineFilters();
  initTimelineLightbox();
});

/**
 * Vertical Spine Scroll Progress Tracker & Hollow Node Activator
 * Uses GPU-accelerated transform: scaleY() with smooth lerp interpolation (0.12).
 */
function initTimelineSpine() {
  const spineProgress = document.getElementById('timeline-spine-progress');
  const wrapper = document.getElementById('timeline-wrapper');

  if (!spineProgress || !wrapper) return;

  let targetProgress = 0;
  let currentProgress = 0;
  let isAnimating = false;

  let cachedNodes = [];
  let wrapperTop = 0;
  let wrapperHeight = 0;

  // Cache node positions and wrapper height on setup / resize / filter
  const cacheBounds = () => {
    const rect = wrapper.getBoundingClientRect();
    const scrollY = window.scrollY || window.pageYOffset;

    wrapperTop = rect.top + scrollY;
    wrapperHeight = rect.height;

    const rows = Array.from(document.querySelectorAll('.timeline-story-row:not(.is-filtered-out)'));
    cachedNodes = rows.map(row => {
      const node = row.querySelector('.timeline-node');
      if (!node) return null;

      const nodeRect = node.getBoundingClientRect();
      const nodeCenterY = nodeRect.top + scrollY + (nodeRect.height / 2);
      const relativeRatio = wrapperHeight > 0 ? (nodeCenterY - wrapperTop) / wrapperHeight : 0;

      return {
        element: node,
        ratio: Math.max(0, Math.min(1, relativeRatio))
      };
    }).filter(Boolean);
  };

  const updateTarget = () => {
    if (!wrapperHeight) cacheBounds();

    const viewportHeight = window.innerHeight;
    const scrollY = window.scrollY || window.pageYOffset;

    // Trigger point: 40% into viewport height
    const triggerY = scrollY + (viewportHeight * 0.4);
    let traveled = triggerY - wrapperTop;

    if (traveled < 0) traveled = 0;
    if (traveled > wrapperHeight) traveled = wrapperHeight;

    targetProgress = wrapperHeight > 0 ? traveled / wrapperHeight : 0;

    if (!isAnimating) {
      isAnimating = true;
      requestAnimationFrame(animationLoop);
    }
  };

  const animationLoop = () => {
    // Lerp towards targetProgress smoothly
    const diff = targetProgress - currentProgress;

    if (Math.abs(diff) > 0.0005) {
      currentProgress += diff * 0.12;
      requestAnimationFrame(animationLoop);
    } else {
      currentProgress = targetProgress;
      isAnimating = false;
    }

    // GPU-accelerated transform scaling
    spineProgress.style.transform = `scaleY(${currentProgress})`;

    // Activate hollow nodes as progress line reaches them
    cachedNodes.forEach(item => {
      if (currentProgress >= (item.ratio - 0.02)) {
        item.element.classList.add('is-active');
      } else {
        item.element.classList.remove('is-active');
      }
    });
  };

  // Check reduced motion preference
  const prefersReduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (prefersReduced) {
    window.addEventListener('scroll', () => {
      cacheBounds();
      const rect = wrapper.getBoundingClientRect();
      const traveled = (window.innerHeight * 0.4) - rect.top;
      const prog = Math.max(0, Math.min(1, rect.height > 0 ? traveled / rect.height : 0));
      spineProgress.style.transform = `scaleY(${prog})`;
      cachedNodes.forEach(item => {
        if (prog >= item.ratio) item.element.classList.add('is-active');
        else item.element.classList.remove('is-active');
      });
    }, { passive: true });
    cacheBounds();
    return;
  }

  cacheBounds();
  updateTarget();

  window.addEventListener('scroll', updateTarget, { passive: true });
  window.addEventListener('resize', () => {
    cacheBounds();
    updateTarget();
  }, { passive: true });

  // Expose recalculate helper for filter events
  window.recalculateTimelineSpine = () => {
    cacheBounds();
    updateTarget();
  };
}

/**
 * Category Filter Handler for Story Rows
 */
function initTimelineFilters() {
  const filterBtns = document.querySelectorAll('.timeline-filter-btn');
  const rows = document.querySelectorAll('.timeline-story-row');

  if (!filterBtns.length || !rows.length) return;

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const selectedCategory = btn.getAttribute('data-filter');

      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      rows.forEach(row => {
        const rowCategory = row.getAttribute('data-category');

        if (selectedCategory === 'all' || rowCategory === selectedCategory) {
          row.classList.remove('is-filtered-out');
        } else {
          row.classList.add('is-filtered-out');
        }
      });

      // Recalculate spine scroll bounds & node positions after filtering
      if (window.recalculateTimelineSpine) {
        window.recalculateTimelineSpine();
      }
    });
  });
}

/**
 * Vertical Thumbnail Autostart Timeline Event Viewer
 */
function initTimelineLightbox() {
  if (!window.VerticalThumbnailViewer) return;

  const viewer = new window.VerticalThumbnailViewer({
    overlay: '#timeline-lightbox',
    shell: '.vertical-viewer-shell',
    stage: '#timeline-viewer-stage',
    img: '#timeline-lightbox-img',
    blur: '#timeline-lightbox-blur',
    thumbStrip: '#timeline-viewer-thumbs',
    title: '#timeline-lightbox-title',
    category: '#timeline-lightbox-category',
    date: '#timeline-lightbox-date',
    description: '#timeline-lightbox-description',
    counter: '#timeline-lightbox-counter',
    prevBtn: '#timeline-lightbox-prev',
    nextBtn: '#timeline-lightbox-next',
    closeBtn: '#timeline-lightbox-close',
    bodyLockClass: 'timeline-lightbox-open',
    autoplayDelay: 2000,
    getItems: () => {
      const photos = Array.from(document.querySelectorAll('.timeline-story-row:not(.is-filtered-out) .timeline-photo-cell'));
      return photos.map(photo => ({
        src: photo.getAttribute('data-src') || '',
        title: photo.getAttribute('data-title') || '',
        category: photo.getAttribute('data-category') || 'Memory',
        date: photo.getAttribute('data-date') || '',
        description: photo.getAttribute('data-description') || ''
      })).filter(item => item.src);
    }
  });

  document.querySelectorAll('.timeline-photo-cell').forEach(photo => {
    photo.addEventListener('click', () => {
      const visiblePhotos = Array.from(document.querySelectorAll('.timeline-story-row:not(.is-filtered-out) .timeline-photo-cell'));
      const idx = visiblePhotos.indexOf(photo);
      viewer.open(idx >= 0 ? idx : 0);
    });
  });
}
