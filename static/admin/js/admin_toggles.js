document.addEventListener("DOMContentLoaded", function () {
  // 1. One-click Admin List Toggles via POST AJAX
  document.addEventListener("click", function (event) {
    const btn = event.target.closest(".js-admin-toggle");
    if (!btn) return;

    event.preventDefault();
    event.stopPropagation();

    const photoId = btn.dataset.photoId;
    const field = btn.dataset.field;
    if (!photoId || !field) return;

    // Robust CSRF token extraction helper
    function getCsrfToken() {
      const input = document.querySelector('input[name="csrfmiddlewaretoken"]') || btn.closest('form')?.querySelector('input[name="csrfmiddlewaretoken"]');
      if (input && input.value) return input.value;
      const meta = document.querySelector('meta[name="csrf-token"]');
      if (meta && meta.content) return meta.content;
      const match = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/);
      if (match) return decodeURIComponent(match[1]);
      return "";
    }

    const csrfToken = getCsrfToken();
    btn.style.opacity = "0.5";
    btn.disabled = true;

    fetch(`/admin/core/photo/${photoId}/toggle/${field}/`, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": csrfToken,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json",
      },
    })
      .then((res) => {
        if (!res.ok) {
          return res.json().then((data) => {
            throw new Error(data.error || "Toggle failed");
          });
        }
        return res.json();
      })
      .then((data) => {
        btn.style.opacity = "1";
        btn.disabled = false;
        if (data.success) {
          const is_on = data.new_state;
          let bg = "#334155";
          if (is_on) {
            if (field === "scrapbook") bg = "#D7B377";
            else if (field === "memory_fragments" || field === "fragments" || field === "mosaic") bg = "#C5A3E6";
            else if (field === "film_strip_1") bg = "#60A5FA";
            else if (field === "film_strip_2") bg = "#3B82F6";
            else bg = "#10B981";
          }
          const label = is_on ? (field === "scrapbook" ? "PINNED" : "ON") : "OFF";
          const align = is_on ? "flex-end" : "flex-start";

          btn.style.background = bg;
          btn.style.justifyContent = align;
          const span = btn.querySelector("span:first-child");
          if (span) span.textContent = label;
        }
      })
      .catch((err) => {
        btn.style.opacity = "1";
        btn.disabled = false;
        alert(err.message || "Failed to update status.");
      });
  });

  // 2. Conditional Form Hiding on Photo Edit Page
  const inScrapbookCheckbox = document.querySelector('input[name="in_scrapbook"]');
  const scrapbookFieldset = document.querySelector('.scrapbook-config-fieldset');

  function updateScrapbookVisibility() {
    if (!inScrapbookCheckbox || !scrapbookFieldset) return;
    if (inScrapbookCheckbox.checked) {
      scrapbookFieldset.style.opacity = "1";
      scrapbookFieldset.style.pointerEvents = "auto";
    } else {
      scrapbookFieldset.style.opacity = "0.45";
      scrapbookFieldset.style.pointerEvents = "none";
    }
  }

  if (inScrapbookCheckbox) {
    inScrapbookCheckbox.addEventListener("change", updateScrapbookVisibility);
    updateScrapbookVisibility();
  }
});

