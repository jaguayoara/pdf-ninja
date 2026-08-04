/* ===========================================================
   Pdf Ninja - JS para la pagina generica de herramienta
   Lee window.TOOL_CONFIG (inyectado por el template) y configura
   el drop zone + envio segun el slug.
   =========================================================== */

(function () {
  const cfg = window.TOOL_CONFIG || {};
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const browseBtn = document.getElementById('browseBtn');
  const fileList = document.getElementById('fileList');
  const actionBtn = document.getElementById('actionBtn');
  const actionStatus = document.getElementById('actionStatus');
  const resultPane = document.getElementById('resultPane');
  const resultBody = document.getElementById('resultBody');
  const optionsPane = document.querySelector('.options-pane');

  let selectedFiles = [];

  // Renderizar lista de archivos seleccionados
  function renderFileList() {
    if (!fileList) return;
    if (selectedFiles.length === 0) {
      fileList.hidden = true;
      fileList.innerHTML = '';
    } else {
      fileList.hidden = false;
      fileList.innerHTML = selectedFiles.map((f, i) => `
        <div class="file-row" data-i="${i}">
          <div class="file-icon">${getFileBadge(f)}</div>
          <div class="file-name" title="${escapeHtml(f.name)}">${escapeHtml(f.name)}</div>
          <div class="file-size">${PdfNinja.humanSize(f.size)}</div>
          <button class="file-remove" data-i="${i}" title="Quitar">&times;</button>
        </div>
      `).join('');
      fileList.querySelectorAll('.file-remove').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const i = parseInt(btn.dataset.i, 10);
          selectedFiles.splice(i, 1);
          renderFileList();
          updateActionState();
        });
      });
    }
  }

  function getFileBadge(f) {
    const n = f.name.toLowerCase();
    if (n.endsWith('.pdf')) return 'PDF';
    if (n.match(/\.(png|jpg|jpeg)$/)) return 'IMG';
    if (n.match(/\.(webp|bmp|tiff|gif)$/)) return 'IMG';
    if (n.endsWith('.docx')) return 'DOC';
    if (n.endsWith('.xlsx')) return 'XLS';
    if (n.endsWith('.txt')) return 'TXT';
    return 'FILE';
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  function updateActionState() {
    if (!actionBtn) return;
    if (cfg.multiple) {
      // merge: necesita >=2; images-to-pdf: >=1
      if (cfg.slug === 'merge') {
        actionBtn.disabled = selectedFiles.length < 2;
      } else {
        actionBtn.disabled = selectedFiles.length < 1;
      }
    } else {
      actionBtn.disabled = selectedFiles.length !== 1;
    }
  }

  function addFiles(files) {
    if (cfg.multiple) {
      selectedFiles = selectedFiles.concat(files);
    } else {
      selectedFiles = [files[0]];
    }
    renderFileList();
    updateActionState();
  }

  // Configurar drop zone
  PdfNinja.setupDropZone({
    zone: dropZone,
    input: fileInput,
    browseBtn,
    multiple: !!cfg.multiple,
    accept: fileInput.accept || '.pdf',
    onFiles: addFiles,
  });

  // Para images-to-pdf arrastrar directamente al dropZone
  // (ya manejado por setupDropZone)

  // Recolectar opciones del pane
  function collectOptions() {
    const out = {};
    if (!optionsPane) return out;
    optionsPane.querySelectorAll('input, select, textarea').forEach(el => {
      if (!el.name) return;
      if (el.type === 'checkbox') { out[el.name] = el.checked ? '1' : '0'; return; }
      if (el.type === 'color' || el.type === 'range' || el.type === 'number' || el.type === 'text'
          || el.type === 'password' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA') {
        out[el.name] = el.value;
      }
    });
    return out;
  }

  function setStatus(msg, kind = '') {
    if (!actionStatus) return;
    actionStatus.textContent = msg;
    actionStatus.className = 'action-status ' + kind;
  }

  function showResult(html) {
    if (!resultPane || !resultBody) return;
    resultBody.innerHTML = html;
    resultPane.hidden = false;
    resultPane.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function hideResult() {
    if (resultPane) resultPane.hidden = true;
  }

  // Click en procesar
  if (actionBtn) {
    actionBtn.addEventListener('click', async () => {
      if (selectedFiles.length === 0) return;
      hideResult();
      const label = actionBtn.querySelector('#actionBtnLabel');
      const originalLabel = label ? label.innerHTML : actionBtn.innerHTML;
      actionBtn.disabled = true;
      if (label) {
        label.innerHTML = '<span class="spinner"></span> Procesando...';
      } else {
        actionBtn.innerHTML = '<span class="spinner"></span> Procesando...';
      }
      setStatus('');

      try {
        const fd = new FormData();
        if (cfg.multiple) {
          selectedFiles.forEach(f => fd.append('files', f, f.name));
        } else {
          fd.append('file', selectedFiles[0], selectedFiles[0].name);
        }
        const opts = collectOptions();
        for (const [k, v] of Object.entries(opts)) {
          fd.append(k, v);
        }

        const res = await fetch(cfg.endpoint, { method: 'POST', body: fd });
        if (!res.ok) {
          let msg = `Error HTTP ${res.status}`;
          try {
            const j = await res.json();
            if (j && j.error) msg = j.error;
          } catch {}
          throw new Error(msg);
        }

        // Detectar tipo de salida por Content-Disposition o content-type
        const disp = res.headers.get('Content-Disposition') || '';
        const m = disp.match(/filename="?([^"]+)"?/);
        const filename = m ? m[1] : 'archivo';
        const blob = await res.blob();

        PdfNinja.downloadBlob(blob, filename);
        const sizeKb = (blob.size / 1024).toFixed(1);
        showResult(`
          <p><strong>Listo.</strong> Tu archivo <code>${escapeHtml(filename)}</code> (${sizeKb} KB) se ha descargado.</p>
          <p class="muted small">Si la descarga no comenzó automáticamente, <a href="#" id="redownload">haz clic aquí</a>.</p>
        `);
        const redl = document.getElementById('redownload');
        if (redl) redl.addEventListener('click', (e) => { e.preventDefault(); PdfNinja.downloadBlob(blob, filename); });
        setStatus('Completado', 'success');
        PdfNinja.toast('Proceso completado', 'success');
      } catch (err) {
        console.error(err);
        setStatus(err.message, 'error');
        PdfNinja.toast(err.message, 'error');
      } finally {
        if (label) {
          label.innerHTML = originalLabel;
        } else {
          actionBtn.innerHTML = original;
        }
        actionBtn.disabled = false;
        updateActionState();
      }
    });
  }

  updateActionState();
})();
