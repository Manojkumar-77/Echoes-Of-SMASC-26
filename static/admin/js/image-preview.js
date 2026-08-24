/**
 * College Memories '26 - Universal Image Upload Live Preview for Django Unfold Admin
 * Supports instant client-side preview for newly selected local images and existing saved photos.
 */

(function() {
  'use strict';

  const IMAGE_EXTENSIONS = /\.(jpe?g|png|webp|gif|bmp|svg|avif|heic|heif)$/i;

  function isImageFile(file) {
    if (!file) return false;
    if (file.type && file.type.startsWith('image/')) return true;
    return IMAGE_EXTENSIONS.test(file.name || '');
  }

  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function findWidgetContainer(input) {
    // In Django Unfold, the file input is nested inside a zero-width div inside a flex row (.border or .flex-row).
    // We must mount the preview card AFTER this interactive row, inside the column container.
    const widgetRow = input.closest('.border') ||
                      input.closest('.flex-row') ||
                      input.closest('[class*="rounded-default"]') ||
                      input.parentElement?.parentElement?.parentElement ||
                      input.parentElement;

    return widgetRow;
  }

  function handleFileInputChange(input) {
    if (!input || input.type !== 'file') return;

    const widgetRow = findWidgetContainer(input);
    if (!widgetRow || !widgetRow.parentElement) return;

    const parentCol = widgetRow.parentElement;
    let previewBox = parentCol.querySelector('.admin-upload-live-preview');

    const file = input.files && input.files[0];

    if (!file || !isImageFile(file)) {
      if (previewBox) {
        if (previewBox.dataset.objUrl) {
          URL.revokeObjectURL(previewBox.dataset.objUrl);
        }
        previewBox.remove();
      }
      return;
    }

    const objUrl = URL.createObjectURL(file);
    const fileName = file.name || 'Selected image';
    const fileSize = formatBytes(file.size);

    if (previewBox) {
      if (previewBox.dataset.objUrl) {
        URL.revokeObjectURL(previewBox.dataset.objUrl);
      }
      previewBox.dataset.objUrl = objUrl;
      renderPreviewContent(previewBox, objUrl, fileName, fileSize, true);
    } else {
      previewBox = document.createElement('div');
      previewBox.className = 'admin-upload-live-preview';
      previewBox.dataset.objUrl = objUrl;
      renderPreviewContent(previewBox, objUrl, fileName, fileSize, true);

      // Insert immediately after the file input widget row
      if (widgetRow.nextSibling) {
        parentCol.insertBefore(previewBox, widgetRow.nextSibling);
      } else {
        parentCol.appendChild(previewBox);
      }
    }
  }

  function renderPreviewContent(container, src, name, size, isNew) {
    container.innerHTML = `
      <div class="admin-preview-card">
        <div class="admin-preview-header">
          <span class="admin-preview-badge ${isNew ? 'is-new' : 'is-saved'}">
            ${isNew ? '✦ Live Upload Preview' : 'Saved Image'}
          </span>
          <span class="admin-preview-filename" title="${name}">${name}</span>
          ${size ? `<span class="admin-preview-filesize">${size}</span>` : ''}
        </div>
        <div class="admin-preview-body">
          <img src="${src}" alt="${name}" class="admin-preview-img" loading="eager">
        </div>
        <div class="admin-preview-footer">
          <span class="admin-preview-meta-dim">Loading dimensions...</span>
        </div>
      </div>
    `;

    const img = container.querySelector('.admin-preview-img');
    const dimSpan = container.querySelector('.admin-preview-meta-dim');

    if (img && dimSpan) {
      img.onload = function() {
        if (this.naturalWidth && this.naturalHeight) {
          dimSpan.textContent = `${this.naturalWidth} × ${this.naturalHeight} px`;
        } else {
          dimSpan.textContent = 'Image Ready';
        }
      };
      img.onerror = function() {
        dimSpan.textContent = 'Preview unavailable';
      };
    }
  }

  // Scan for existing saved images on initial load if Unfold did not render an image
  function initExistingPreviews() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach((input) => {
      const widgetRow = findWidgetContainer(input);
      if (!widgetRow || !widgetRow.parentElement) return;

      const parentCol = widgetRow.parentElement;
      if (parentCol.querySelector('.admin-upload-live-preview')) return;

      // Check for existing image link rendered by Django / Unfold
      const existingLink = parentCol.querySelector('a[href*="/media/"]') ||
                           widgetRow.querySelector('a[href*="/media/"]') ||
                           parentCol.querySelector('a[href*=".jpg"], a[href*=".jpeg"], a[href*=".png"], a[href*=".webp"]');

      if (existingLink && existingLink.href) {
        const href = existingLink.href;
        if (IMAGE_EXTENSIONS.test(href) || href.includes('/media/')) {
          const hasImg = parentCol.querySelector('img');
          if (!hasImg) {
            const previewBox = document.createElement('div');
            previewBox.className = 'admin-upload-live-preview is-initial';
            const fileName = href.split('/').pop() || 'Saved Image';
            renderPreviewContent(previewBox, href, fileName, '', false);

            if (widgetRow.nextSibling) {
              parentCol.insertBefore(previewBox, widgetRow.nextSibling);
            } else {
              parentCol.appendChild(previewBox);
            }
          }
        }
      }
    });
  }

  // Global delegated listener for changes
  document.addEventListener('change', function(e) {
    const target = e.target;
    if (target && target.matches && target.matches('input[type="file"]')) {
      handleFileInputChange(target);
    }
  });

  // Initial scan on load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initExistingPreviews);
  } else {
    initExistingPreviews();
  }

  setTimeout(initExistingPreviews, 400);
})();
