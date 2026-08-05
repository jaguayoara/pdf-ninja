/* ===========================================================
   PDF Ninja - JavaScript principal (toast, helpers, drop zone, theme)
   =========================================================== */

(function initTheme() {
  const saved = localStorage.getItem('pdfninja-theme');
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const theme = saved || (prefersDark ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', theme);

  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('themeToggle');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('pdfninja-theme', next);
    });
  });
})();

window.PdfNinja = (function () {
  // Toast
  function toast(msg, type = 'info', duration = 3500) {
    const host = document.getElementById('toast-host');
    if (!host) return;
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = msg;
    host.appendChild(el);
    setTimeout(() => {
      el.style.transition = 'opacity 0.2s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 200);
    }, duration);
  }

  // Fetch JSON con manejo de errores
  async function fetchJson(url, options = {}) {
    const res = await fetch(url, options);
    let data;
    try { data = await res.json(); } catch { data = null; }
    if (!res.ok) {
      const msg = (data && data.error) || `Error HTTP ${res.status}`;
      throw new Error(msg);
    }
    return data;
  }

  // Fetch que devuelve blob (para descargas)
  async function fetchBlob(url, options = {}) {
    const res = await fetch(url, options);
    if (!res.ok) {
      let msg = `Error HTTP ${res.status}`;
      try {
        const j = await res.json();
        if (j && j.error) msg = j.error;
      } catch {}
      throw new Error(msg);
    }
    const disp = res.headers.get('Content-Disposition') || '';
    let filename = 'archivo';
    const m = disp.match(/filename="?([^"]+)"?/);
    if (m) filename = m[1];
    const blob = await res.blob();
    return { blob, filename };
  }

  // Dispara descarga de un blob
  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || 'archivo';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(url);
      a.remove();
    }, 100);
  }

  // Formatea tamano
  function humanSize(n) {
    if (n == null) return '';
    for (const u of ['B', 'KB', 'MB', 'GB']) {
      if (n < 1024) return `${n.toFixed(1)} ${u}`;
      n /= 1024;
    }
    return `${n.toFixed(1)} TB`;
  }

  // Drop zone generica
  function setupDropZone(opts) {
    const {
      zone, input, browseBtn,
      multiple = false,
      accept = '.pdf',
      onFiles,
    } = opts;
    if (!zone || !input) return;

    const open = () => input.click();
    zone.addEventListener('click', (e) => {
      // Evitar click cuando se presiona un boton dentro
      if (e.target.closest('button')) return;
      open();
    });
    zone.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); }
    });
    if (browseBtn) browseBtn.addEventListener('click', (e) => { e.stopPropagation(); open(); });

    input.addEventListener('change', () => {
      const files = Array.from(input.files || []);
      if (files.length && typeof onFiles === 'function') onFiles(files);
      input.value = '';
    });

    let dragDepth = 0;
    const onEnter = (e) => {
      e.preventDefault();
      dragDepth++;
      zone.classList.add('drag-over');
    };
    const onLeave = (e) => {
      e.preventDefault();
      dragDepth--;
      if (dragDepth <= 0) { dragDepth = 0; zone.classList.remove('drag-over'); }
    };
    const onOver = (e) => { e.preventDefault(); };
    const onDrop = (e) => {
      e.preventDefault();
      dragDepth = 0;
      zone.classList.remove('drag-over');
      const files = Array.from(e.dataTransfer.files || []);
      if (files.length && typeof onFiles === 'function') onFiles(files);
    };
    zone.addEventListener('dragenter', onEnter);
    zone.addEventListener('dragleave', onLeave);
    zone.addEventListener('dragover', onOver);
    zone.addEventListener('drop', onDrop);
  }

  return { toast, fetchJson, fetchBlob, downloadBlob, humanSize, setupDropZone };
})();
