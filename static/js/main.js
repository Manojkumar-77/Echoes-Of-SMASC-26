/**
 * College Memories '26 - Core Site JavaScript (main.js)
 * ====================================================
 * Header scroll effects, Theme Toggle System (Dark/Light),
 * Memory Chapters animated burger navigation, smooth scroll,
 * and scroll reveal animation engine.
 */

document.addEventListener('DOMContentLoaded', () => {
  initThemeSystem();
  initGlobalHeader();
  initMobileNav();
  initHeroScrollLink();
  initBackToBeginning();
  initScrollReveal();
});

/**
 * Complete Global Dark / Light Theme System (Uiverse Switch Integration)
 * Features:
 * - LocalStorage persistence ('college-memories-theme')
 * - System preference fallback (prefers-color-scheme)
 * - FOUT protection (inline head script + instant JS sync)
 * - State sync with #theme-switch-checkbox (checked = light, unchecked = dark)
 */
function initThemeSystem() {
  const switchInput = document.getElementById('theme-switch-checkbox');
  const THEME_KEY = 'college-memories-theme';

  function getCurrentTheme() {
    return document.documentElement.getAttribute('data-theme') || 'dark';
  }

  function applyTheme(theme, save = true) {
    document.documentElement.setAttribute('data-theme', theme);
    if (save) {
      try {
        localStorage.setItem(THEME_KEY, theme);
      } catch (e) {}
    }

    if (switchInput) {
      const isLight = theme === 'light';
      switchInput.checked = isLight;
    }
  }

  // Initial sync with DOM state
  const current = getCurrentTheme();
  applyTheme(current, false);

  if (switchInput) {
    switchInput.addEventListener('change', () => {
      const next = switchInput.checked ? 'light' : 'dark';
      applyTheme(next, true);
    });
  }

  // Listen for system theme changes if user hasn't explicitly saved a preference
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', (e) => {
      try {
        const saved = localStorage.getItem(THEME_KEY);
        if (!saved) {
          applyTheme(e.matches ? 'light' : 'dark', false);
        }
      } catch (err) {}
    });
  }
}

/**
 * Global Header Scroll & Shadow Controller
 */
function initGlobalHeader() {
  const header = document.querySelector('.site-header') || document.querySelector('.header');
  if (!header) return;

  function updateHeader() {
    if (window.scrollY > 20) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }
  }

  window.addEventListener('scroll', updateHeader, { passive: true });
  updateHeader();
}

/**
 * Half-Screen Height Mobile Navigation Controller (Uiverse Single-SVG Morph Sync)
 * Features:
 * - Half-screen height menu panel (~52dvh) at top of viewport
 * - Single-SVG Uiverse stroke-dash morphing hamburger -> X
 * - Translucent dark backdrop covering lower viewport area
 * - Authoritative state sync with #mobile-menu-hamburger-input checkbox
 * - Body scroll lock when open
 * - Closes on: X click, backdrop click, nav link click, CTA click, Escape key, desktop resize
 */
function initMobileNav() {
  const toggleInput = document.getElementById('mobile-menu-hamburger-input');
  const toggleLabel = document.querySelector('.mobile-menu-hamburger');
  const menu        = document.getElementById('mob-full-menu');
  const backdrop    = document.getElementById('mob-nav-backdrop');
  if (!toggleInput || !menu) return;

  const navLinks = menu.querySelectorAll('.mob-index-link, .mob-menu-link, .mob-menu-contact-btn');
  const ctaLink  = document.getElementById('mob-menu-cta');

  function openNav() {
    menu.classList.add('open');
    menu.setAttribute('aria-hidden', 'false');
    if (backdrop) backdrop.classList.add('visible');
    if (toggleLabel) toggleLabel.classList.add('active');
    toggleInput.checked = true;
    toggleInput.setAttribute('aria-expanded', 'true');
    toggleInput.setAttribute('aria-label', 'Close navigation');
    document.body.classList.add('menu-open');
  }

  function closeNav() {
    menu.classList.remove('open');
    menu.setAttribute('aria-hidden', 'true');
    if (backdrop) backdrop.classList.remove('visible');
    if (toggleLabel) toggleLabel.classList.remove('active');
    toggleInput.checked = false;
    toggleInput.setAttribute('aria-expanded', 'false');
    toggleInput.setAttribute('aria-label', 'Open navigation');
    document.body.classList.remove('menu-open');
  }

  function isOpen() {
    return menu.classList.contains('open');
  }

  // Checkbox change listener
  toggleInput.addEventListener('change', () => {
    if (toggleInput.checked) openNav(); else closeNav();
  });

  // Backdrop click
  if (backdrop) {
    backdrop.addEventListener('click', closeNav);
  }

  // Nav link clicks
  navLinks.forEach(link => {
    link.addEventListener('click', () => closeNav());
  });

  // CTA link click
  if (ctaLink) {
    ctaLink.addEventListener('click', () => closeNav());
  }

  // Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && isOpen()) closeNav();
  });

  // Close on desktop resize
  window.addEventListener('resize', () => {
    if (window.innerWidth > 900 && isOpen()) closeNav();
  }, { passive: true });
}


/**
 * Home Hero "Scroll To Begin" Controller
 */
function initHeroScrollLink() {
  const scrollLink = document.getElementById('home-scroll-link') || document.querySelector('.home-scroll-indicator');
  if (!scrollLink) return;

  scrollLink.addEventListener('click', (e) => {
    const targetId = scrollLink.getAttribute('href');
    if (targetId && targetId.startsWith('#')) {
      const destSection = document.querySelector(targetId) || document.getElementById('home-intro-section');
      if (destSection) {
        e.preventDefault();
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        destSection.scrollIntoView({
          behavior: prefersReducedMotion ? 'auto' : 'smooth',
          block: 'start'
        });
      }
    }
  });
}

/**
 * Back To The Beginning Handler (Smooth Scroll)
 */
function initBackToBeginning() {
  const btn = document.getElementById('back-to-beginning') || document.querySelector('.back-to-top');
  if (!btn) return;

  btn.addEventListener('click', (e) => {
    e.preventDefault();
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({
      top: 0,
      behavior: prefersReducedMotion ? 'auto' : 'smooth'
    });
  });
}

/**
 * Scroll Reveal Animation Engine (With Progressive Enhancement & Safe Fallback)
 */
function initScrollReveal() {
  const revealElements = document.querySelectorAll('.reveal');
  if (!revealElements.length) return;

  document.documentElement.classList.add('js-reveal-active');

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('active');
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    });

    revealElements.forEach(el => observer.observe(el));
  } else {
    revealElements.forEach(el => el.classList.add('active'));
  }

  // Safety timer: ensure all elements are visible after 1.5s
  setTimeout(() => {
    revealElements.forEach(el => el.classList.add('active'));
  }, 1500);
}