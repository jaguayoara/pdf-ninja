/* ===========================================================
   PDF Ninja - JS para la pagina generica de herramienta
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
    if (n.match(/\.docx?$/)) return 'DOC';
    if (n.match(/\.xlsx?$/)) return 'XLS';
    if (n.match(/\.pptx?$/)) return 'PPT';
    if (n.match(/\.(txt|md|csv|log)$/)) return 'TXT';
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

  // Formatea un valor de metadata para mostrar (string vacio -> "—")
  function fmtVal(v) {
    if (v == null) return '—';
    const s = String(v).trim();
    return s === '' ? '—' : escapeHtml(s);
  }

  function fmtDate(s) {
    if (!s) return null;
    // ISO 8601 -> mostrar legible
    try {
      const d = new Date(s);
      if (isNaN(d.getTime())) return escapeHtml(String(s));
      return escapeHtml(d.toLocaleString('es-CL'));
    } catch {
      return escapeHtml(String(s));
    }
  }

  function rowsFrom(obj, labels) {
    return Object.entries(obj || {}).map(([k, v]) =>
      `<tr><th>${escapeHtml(labels[k] || k)}</th><td>${fmtVal(v)}</td></tr>`
    ).join('');
  }

  // Render especifico para respuestas JSON (herramienta de metadatos).
  // Soporta multiples tipos: pdf, docx, xlsx, pptx, image, text.
  function renderJsonResult(data) {
    if (!data || !data.ok || !data.info) {
      return '<p class="muted">Sin datos.</p>';
    }
    const info = data.info;
    const kind = info.kind || 'pdf';

    // Bloque "Informacion general" comun a todos
    const kindLabel = {
      pdf: 'PDF', docx: 'Word', xlsx: 'Excel',
      pptx: 'PowerPoint', image: 'Imagen', text: 'Texto',
    }[kind] || kind.toUpperCase();
    const main = [
      ['Tipo', kindLabel],
      ['Nombre del archivo', fmtVal(info.filename)],
      ['Tamano', fmtVal(info.size_human)],
      ['Tamano (bytes)', fmtVal(info.size_bytes)],
    ];
    const mainHtml = `<table class="meta-table">${main.map(([k,v]) =>
      `<tr><th>${escapeHtml(k)}</th><td>${v}</td></tr>`).join('')}</table>`;

    // Labels amigables para campos de metadatos
    const metaLabels = {
      title: 'Titulo', author: 'Autor', subject: 'Asunto',
      keywords: 'Palabras clave', creator: 'Creador', producer: 'Productor',
      creationDate: 'Fecha de creacion', modDate: 'Fecha de modificacion',
      trapped: 'Trapped', description: 'Descripcion',
      lastModifiedBy: 'Ultima edicion por', revision: 'Revision',
      category: 'Categoria', contentStatus: 'Estado',
      created: 'Fecha de creacion', modified: 'Ultima modificacion',
      format: 'Formato', company: 'Empresa', manager: 'Responsable',
      application: 'Aplicacion', appVersion: 'Version de la app',
      totalTime: 'Tiempo total de edicion', pages: 'Paginas',
      words: 'Palabras', characters: 'Caracteres',
      charactersWithSpaces: 'Caracteres (con espacios)',
      lines: 'Lineas', paragraphs: 'Parrafos', slides: 'Slides',
      notes: 'Notas', hiddenSlides: 'Slides ocultas',
    };

    const meta = info.metadata || {};
    const metaHtml = meta && Object.keys(meta).length
      ? `<table class="meta-table">${rowsFrom(meta, metaLabels)}</table>`
      : '<p class="muted">El documento no expone metadatos estandar.</p>';

    // App (Application, AppVersion, etc. — comun a docx/xlsx/pptx)
    let appHtml = '';
    const app = info.app || {};
    if (Object.keys(app).length) {
      appHtml = `<h4>Datos de la aplicacion</h4><table class="meta-table">${rowsFrom(app, metaLabels)}</table>`;
    }

    // Render especifico por tipo
    let typeSpecific = '';
    if (kind === 'pdf') {
      const encrypted = info.encrypted ? 'Si' : 'No';
      typeSpecific = `
        <h4>Contenido</h4>
        <table class="meta-table">
          <tr><th>Paginas</th><td>${fmtVal(info.pages)}</td></tr>
          <tr><th>Cifrado</th><td>${encrypted}</td></tr>
        </table>
        <h4>Indice (TOC) &mdash; ${(info.outline||[]).length} entrada(s)</h4>
        ${renderOutline(info.outline || [])}
      `;
    } else if (kind === 'docx') {
      const s = info.stats || {};
      typeSpecific = `
        <h4>Contenido &mdash; Word</h4>
        <table class="meta-table">
          <tr><th>Parrafos</th><td>${fmtVal(s.paragraphs)}</td></tr>
          <tr><th>Palabras</th><td>${fmtVal(s.words)}</td></tr>
          <tr><th>Tablas</th><td>${fmtVal(s.tables)}</td></tr>
        </table>
        <h4>Tablas del documento &mdash; ${(info.tables||[]).length}</h4>
        ${renderTables(info.tables || [])}
      `;
    } else if (kind === 'xlsx') {
      const s = info.stats || {};
      typeSpecific = `
        <h4>Contenido &mdash; Excel</h4>
        <table class="meta-table">
          <tr><th>Hojas</th><td>${fmtVal(s.sheets)}</td></tr>
          <tr><th>Celdas con valor</th><td>${fmtVal(s.cells_with_value)}</td></tr>
          <tr><th>Nombres definidos</th><td>${fmtVal(s.defined_names)}</td></tr>
        </table>
        <h4>Hojas &mdash; ${(info.sheets||[]).length}</h4>
        ${renderSheets(info.sheets || [])}
        ${(info.defined_names||[]).length ? `<h4>Nombres definidos &mdash; ${info.defined_names.length}</h4>${renderDefinedNames(info.defined_names)}` : ''}
      `;
    } else if (kind === 'pptx') {
      const s = info.stats || {};
      const slideSize = s.slide_w_cm && s.slide_h_cm
        ? `${s.slide_w_cm} x ${s.slide_h_cm} cm`
        : '—';
      typeSpecific = `
        <h4>Contenido &mdash; PowerPoint</h4>
        <table class="meta-table">
          <tr><th>Slides</th><td>${fmtVal(s.slides)}</td></tr>
          <tr><th>Tablas</th><td>${fmtVal(s.tables)}</td></tr>
          <tr><th>Tamano de slide</th><td>${slideSize}</td></tr>
        </table>
        <h4>Slides &mdash; ${(info.slides||[]).length}</h4>
        ${renderSlides(info.slides || [])}
      `;
    } else if (kind === 'image') {
      const s = info.stats || {};
      typeSpecific = `
        <h4>Contenido &mdash; Imagen</h4>
        <table class="meta-table">
          <tr><th>Formato</th><td>${fmtVal(info.format)}</td></tr>
          <tr><th>Modo de color</th><td>${fmtVal(info.mode)}</td></tr>
          <tr><th>Dimensiones</th><td>${fmtVal(s.ancho)} x ${fmtVal(s.alto)} px</td></tr>
          <tr><th>Megapixeles</th><td>${fmtVal(s.megapixeles)}</td></tr>
          ${info.dpi ? `<tr><th>DPI</th><td>${fmtVal(info.dpi)}</td></tr>` : ''}
        </table>
        ${info.exif && Object.keys(info.exif).length
          ? `<h4>Metadatos EXIF &mdash; ${Object.keys(info.exif).length}</h4><table class="meta-table">${rowsFrom(info.exif, {})}</table>`
          : ''}
      `;
    } else if (kind === 'text') {
      const s = info.stats || {};
      typeSpecific = `
        <h4>Contenido &mdash; Texto</h4>
        <table class="meta-table">
          <tr><th>Encoding</th><td>${fmtVal(info.encoding)}</td></tr>
          <tr><th>Lineas</th><td>${fmtVal(s.lineas)}</td></tr>
          <tr><th>Palabras</th><td>${fmtVal(s.palabras)}</td></tr>
          <tr><th>Caracteres</th><td>${fmtVal(s.caracteres)}</td></tr>
          <tr><th>Caracteres (sin espacios)</th><td>${fmtVal(s.caracteres_sin_espacios)}</td></tr>
          ${s.separador ? `<tr><th>Separador CSV</th><td>${escapeHtml(s.separador)}</td></tr>` : ''}
          ${s.columnas ? `<tr><th>Columnas (CSV)</th><td>${fmtVal(s.columnas)}</td></tr>` : ''}
        </table>
      `;
    }

    return `<h4>Informacion general</h4>${mainHtml}<h4>Metadatos</h4>${metaHtml}${appHtml}${typeSpecific}`;
  }

  function renderOutline(outline) {
    if (!outline.length) {
      return '<p class="muted">El PDF no tiene un indice (tabla de contenido) navegable.</p>';
    }
    return `<ol class="meta-outline">${outline.map(item => {
      const lvl = Math.min(item.level || 1, 4);
      return `<li><span class="meta-outline-l${lvl}">${'— '.repeat(Math.max(0, (item.level || 1) - 1))}</span><span class="meta-outline-title">${fmtVal(item.title)}</span><span class="meta-outline-page">p. ${fmtVal(item.page)}</span></li>`;
    }).join('')}</ol>`;
  }

  function renderTables(tables) {
    if (!tables.length) {
      return '<p class="muted">El documento no contiene tablas.</p>';
    }
    return `<table class="meta-table">
      <thead><tr><th>#</th><th>Filas</th><th>Columnas</th><th>Vista previa</th></tr></thead>
      <tbody>${tables.map(t => `<tr>
        <td>${t.index}</td>
        <td>${fmtVal(t.rows)}</td>
        <td>${fmtVal(t.cols)}</td>
        <td class="meta-table-preview">${fmtVal(t.preview)}</td>
      </tr>`).join('')}</tbody>
    </table>`;
  }

  function renderSheets(sheets) {
    if (!sheets.length) {
      return '<p class="muted">El archivo no contiene hojas.</p>';
    }
    return `<table class="meta-table">
      <thead><tr><th>Hoja</th><th>Filas</th><th>Columnas</th><th>Celdas con valor</th><th>Estado</th></tr></thead>
      <tbody>${sheets.map(s => `<tr>
        <td><strong>${fmtVal(s.name)}</strong></td>
        <td>${fmtVal(s.rows)}</td>
        <td>${fmtVal(s.cols)}</td>
        <td>${fmtVal(s.cells)}</td>
        <td>${fmtVal(s.state)}</td>
      </tr>`).join('')}</tbody>
    </table>`;
  }

  function renderDefinedNames(names) {
    return `<table class="meta-table">
      <thead><tr><th>Nombre</th><th>Destino</th></tr></thead>
      <tbody>${names.map(n => `<tr>
        <td><code>${fmtVal(n.name)}</code></td>
        <td>${fmtVal(n.destinations)}</td>
      </tr>`).join('')}</tbody>
    </table>`;
  }

  function renderSlides(slides) {
    if (!slides.length) {
      return '<p class="muted">La presentacion no contiene slides.</p>';
    }
    return `<table class="meta-table">
      <thead><tr><th>#</th><th>Tablas en el slide</th><th>Dimensiones (filas x cols)</th></tr></thead>
      <tbody>${slides.map(s => `<tr>
        <td>${s.index}</td>
        <td>${fmtVal(s.tables)}</td>
        <td>${(s.table_dims || []).map(d => `${d.rows}x${d.cols}`).join(', ') || '—'}</td>
      </tr>`).join('')}</tbody>
    </table>`;
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

        // Herramientas de tipo "json" devuelven datos para mostrar en pantalla
        // (no descargan un archivo). Por ejemplo: metadata del PDF.
        if (cfg.responseKind === 'json') {
          const data = await res.json();
          showResult(renderJsonResult(data));
          setStatus('Completado', 'success');
          PdfNinja.toast('Inspeccion completada', 'success');
          return;
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
