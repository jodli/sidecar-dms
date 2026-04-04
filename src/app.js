// Sidecar DMS — Vanilla JS SPA

const TAG_COLORS = ['tag-b', 'tag-g', 'tag-p', 'tag-a', 'tag-r'];
const TYPE_COLOR = 'tag-a';

let manifests = {};       // { "2025": [...entries] }
let currentDoc = null;    // currently selected document path
let currentTab = 'pdf';   // 'pdf' or 'ocr'
let sidebarMode = 'folders';
let pdfJsLoaded = false;
let pagefind = null;

// ── Init ──

async function init() {
  // Load manifest for current year, then expand to discover others
  const years = await discoverManifests();
  for (const year of years) {
    try {
      const resp = await fetch(`manifest-${year}.json`);
      if (resp.ok) manifests[year] = await resp.json();
    } catch { /* skip */ }
  }

  buildSidebarTree();
  setupEventListeners();

  // Select first document
  const firstYear = Object.keys(manifests).sort().reverse()[0];
  if (firstYear && manifests[firstYear].length > 0) {
    selectDocument(manifests[firstYear][0].path);
  }
}

async function discoverManifests() {
  // Try common years — in a real app this could be a manifest index
  const years = [];
  const currentYear = new Date().getFullYear();
  for (let y = currentYear; y >= currentYear - 10; y--) {
    try {
      const resp = await fetch(`manifest-${y}.json`, { method: 'HEAD' });
      if (resp.ok) years.push(String(y));
    } catch { /* skip */ }
  }
  // Also try older years for certificates
  for (const y of ['1990', '1991', '1992', '2000', '2010', '2015', '2018', '2019']) {
    if (!years.includes(y)) {
      try {
        const resp = await fetch(`manifest-${y}.json`, { method: 'HEAD' });
        if (resp.ok) years.push(y);
      } catch { /* skip */ }
    }
  }
  return years.length > 0 ? years : [String(currentYear)];
}

// ── Sidebar ──

function buildSidebarTree() {
  const container = document.getElementById('sidebar-tree');
  container.innerHTML = '';

  if (sidebarMode === 'folders') {
    buildFolderTree(container);
  } else {
    buildTagTree(container);
  }
}

function buildFolderTree(container) {
  const sortedYears = Object.keys(manifests).sort().reverse();

  for (const year of sortedYears) {
    const entries = manifests[year];
    const yearEl = document.createElement('div');
    yearEl.className = 'tree-year';

    // Group by category (second path segment)
    const categories = {};
    for (const entry of entries) {
      const parts = entry.path.split('/');
      const cat = parts.length >= 2 ? parts[1] : 'Uncategorized';
      if (!categories[cat]) categories[cat] = [];
      categories[cat].push(entry);
    }

    const isFirst = year === sortedYears[0];

    yearEl.innerHTML = `
      <div class="tree-toggle" data-year="${year}">
        <span class="tree-arrow ${isFirst ? '' : 'collapsed'}">&#9660;</span> ${year}
      </div>
    `;

    const yearContent = document.createElement('div');
    if (!isFirst) yearContent.className = 'tree-items collapsed';

    for (const [cat, catEntries] of Object.entries(categories).sort()) {
      const catEl = document.createElement('div');
      catEl.className = 'tree-cat';
      catEl.innerHTML = `
        <div class="tree-cat-label" data-cat="${cat}">
          <span class="tree-arrow">&#9660;</span>
          ${cat}
          <span class="tree-cat-count">${catEntries.length}</span>
        </div>
      `;

      const itemsEl = document.createElement('div');
      itemsEl.className = 'tree-items';

      for (const entry of catEntries) {
        const item = document.createElement('div');
        item.className = 'tree-item';
        if (entry.path === currentDoc) item.classList.add('sel');
        item.dataset.path = entry.path;
        item.textContent = entry.title;
        item.title = entry.title;
        itemsEl.appendChild(item);
      }

      catEl.appendChild(itemsEl);
      yearContent.appendChild(catEl);
    }

    yearEl.appendChild(yearContent);
    container.appendChild(yearEl);
  }
}

function buildTagTree(container) {
  // Collect all tags across all manifests
  const tagMap = {};
  for (const entries of Object.values(manifests)) {
    for (const entry of entries) {
      for (const tag of (entry.tags || [])) {
        if (!tagMap[tag]) tagMap[tag] = [];
        tagMap[tag].push(entry);
      }
    }
  }

  for (const [tag, entries] of Object.entries(tagMap).sort()) {
    const tagEl = document.createElement('div');
    tagEl.className = 'tree-tag';
    tagEl.innerHTML = `
      <div class="tree-tag-label" data-tag="${tag}">
        <span class="tree-arrow">&#9660;</span>
        ${tag}
        <span class="tree-cat-count">${entries.length}</span>
      </div>
    `;

    const itemsEl = document.createElement('div');
    itemsEl.className = 'tree-items';

    for (const entry of entries) {
      const item = document.createElement('div');
      item.className = 'tree-item';
      if (entry.path === currentDoc) item.classList.add('sel');
      item.dataset.path = entry.path;
      item.textContent = entry.title;
      item.title = entry.title;
      itemsEl.appendChild(item);
    }

    tagEl.appendChild(itemsEl);
    container.appendChild(tagEl);
  }
}

// ── Document selection ──

async function selectDocument(path) {
  currentDoc = path;

  // Update sidebar selection
  document.querySelectorAll('.tree-item').forEach(el => {
    el.classList.toggle('sel', el.dataset.path === path);
  });

  // Load and display metadata
  try {
    const resp = await fetch(`archive/${path}.meta.yml`);
    const text = await resp.text();
    const meta = jsyaml.load(text);
    renderMetadataPanel(meta, path);
  } catch (err) {
    document.getElementById('meta-panel').innerHTML =
      `<div class="meta-empty">Failed to load metadata</div>`;
  }

  // Show content for current tab
  showTab(currentTab);
}

// ── Metadata panel ──

function renderMetadataPanel(meta, path) {
  const panel = document.getElementById('meta-panel');
  const baseName = path.split('/').pop();

  // Assign colors to tags by cycling through palette
  const tagHTML = (meta.tags || []).map((tag, i) =>
    `<span class="tag ${TAG_COLORS[i % TAG_COLORS.length]}">${esc(tag)}</span>`
  ).join('');

  const fieldsHTML = meta.fields
    ? Object.entries(meta.fields).map(([k, v]) =>
        `<div class="field-row"><span class="field-key">${esc(k)}</span><span class="field-val">${esc(String(v))}</span></div>`
      ).join('')
    : '';

  const proc = meta.processing || {};
  const ocrDot = proc.ocr_engine ? 'dot-g' : 'dot-r';
  const classifierDot = proc.classifier && proc.classifier !== 'manual' ? 'dot-g' : 'dot-o';
  const textLayerDot = proc.text_layer_embedded ? 'dot-g' : 'dot-o';

  panel.innerHTML = `
    <div class="ml">Title</div>
    <div class="mv meta-title">${esc(meta.title || '')}</div>

    <div class="ml">Date</div>
    <div class="mv m">${esc(String(meta.date || ''))}</div>

    <div class="ml">Type</div>
    <div><span class="tag ${TYPE_COLOR}">${esc(meta.document_type || '')}</span></div>

    <div class="ml">Sender</div>
    <div class="mv">${esc(meta.sender || '—')}</div>

    <div class="ml">Tags</div>
    <div style="margin-top:2px;">${tagHTML || '<span style="color:var(--color-text-tertiary)">—</span>'}</div>

    <div class="ml">Summary</div>
    <div class="meta-summary">${esc(meta.summary || '')}</div>

    <div class="dv"></div>

    <div class="ml">Document fields</div>
    ${fieldsHTML || '<div style="font-size:12px;color:var(--color-text-tertiary)">—</div>'}

    <div class="dv"></div>

    <div class="ml">Files</div>
    <div style="display:flex;flex-direction:column;gap:2px;margin-top:2px;">
      <div class="frow"><span class="dot dot-g"></span> ${esc(baseName)}.pdf</div>
      <div class="frow"><span class="dot dot-g"></span> ${esc(baseName)}.md</div>
      <div class="frow"><span class="dot dot-g"></span> ${esc(baseName)}.meta.yml</div>
    </div>

    <div class="dv"></div>

    <div class="ml">Processing</div>
    <div style="display:flex;flex-direction:column;gap:2px;margin-top:2px;">
      <div class="frow"><span class="dot ${ocrDot}"></span> ${esc(proc.ocr_engine || 'unknown')}</div>
      <div class="frow"><span class="dot ${classifierDot}"></span> ${esc(proc.classifier || 'unknown')}</div>
      <div class="frow"><span class="dot ${textLayerDot}"></span> ${proc.text_layer_embedded ? 'Text layer embedded' : 'No text layer in PDF'}</div>
    </div>
  `;
}

// ── Content tabs ──

function showTab(tab) {
  currentTab = tab;

  // Update tab bar
  document.querySelectorAll('.tab').forEach(el => {
    el.classList.toggle('act', el.dataset.tab === tab);
  });

  // Hide all content
  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('pdf-container').style.display = 'none';
  document.getElementById('ocr-container').style.display = 'none';

  if (!currentDoc) {
    document.getElementById('empty-state').style.display = 'flex';
    return;
  }

  if (tab === 'pdf') {
    showPDF(currentDoc);
  } else {
    showOCR(currentDoc);
  }
}

async function showPDF(path) {
  const container = document.getElementById('pdf-container');
  container.style.display = 'flex';
  container.innerHTML = '<div class="pdf-loading">Loading PDF...</div>';

  if (!pdfJsLoaded) {
    await loadPdfJs();
  }

  try {
    const url = `archive/${path}.pdf`;
    const pdf = await pdfjsLib.getDocument(url).promise;
    container.innerHTML = '';

    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const scale = 1.5;
      const viewport = page.getViewport({ scale });

      const canvas = document.createElement('canvas');
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      container.appendChild(canvas);

      await page.render({
        canvasContext: canvas.getContext('2d'),
        viewport,
      }).promise;
    }
  } catch (err) {
    container.innerHTML = `<div class="pdf-loading">Failed to load PDF: ${esc(err.message)}</div>`;
  }
}

async function showOCR(path) {
  const container = document.getElementById('ocr-container');
  container.style.display = 'block';
  container.innerHTML = '<div class="pdf-loading">Loading...</div>';

  try {
    const resp = await fetch(`archive/${path}.md`);
    const md = await resp.text();
    container.innerHTML = marked.parse(md);
  } catch (err) {
    container.innerHTML = `<div class="pdf-loading">Failed to load OCR text</div>`;
  }
}

function loadPdfJs() {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@4/build/pdf.min.mjs';
    script.type = 'module';

    // pdf.js 4.x is an ES module — use a different loading strategy
    const loader = document.createElement('script');
    loader.type = 'module';
    loader.textContent = `
      import * as pdfjsLib from 'https://cdn.jsdelivr.net/npm/pdfjs-dist@4/build/pdf.min.mjs';
      pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@4/build/pdf.worker.min.mjs';
      window.pdfjsLib = pdfjsLib;
      window.dispatchEvent(new Event('pdfjs-ready'));
    `;
    document.head.appendChild(loader);

    window.addEventListener('pdfjs-ready', () => {
      pdfJsLoaded = true;
      resolve();
    }, { once: true });

    setTimeout(() => reject(new Error('pdf.js load timeout')), 15000);
  });
}

// ── Event listeners ──

function setupEventListeners() {
  // Sidebar tree clicks (event delegation)
  document.getElementById('sidebar-tree').addEventListener('click', (e) => {
    const item = e.target.closest('.tree-item');
    if (item) {
      selectDocument(item.dataset.path);
      return;
    }

    // Year toggle
    const yearToggle = e.target.closest('.tree-toggle');
    if (yearToggle) {
      const arrow = yearToggle.querySelector('.tree-arrow');
      const content = yearToggle.nextElementSibling;
      if (content) {
        content.classList.toggle('collapsed');
        arrow.classList.toggle('collapsed');
      }
      return;
    }

    // Category toggle
    const catLabel = e.target.closest('.tree-cat-label, .tree-tag-label');
    if (catLabel) {
      const arrow = catLabel.querySelector('.tree-arrow');
      const items = catLabel.nextElementSibling;
      if (items) {
        items.classList.toggle('collapsed');
        arrow.classList.toggle('collapsed');
      }
      return;
    }
  });

  // Tab switching
  document.querySelector('.tabs').addEventListener('click', (e) => {
    const tab = e.target.closest('.tab');
    if (tab) showTab(tab.dataset.tab);
  });

  // Sidebar mode toggle
  document.querySelector('.sb-mode').addEventListener('click', (e) => {
    const btn = e.target.closest('.sb-mode-btn');
    if (btn && btn.dataset.mode !== sidebarMode) {
      sidebarMode = btn.dataset.mode;
      document.querySelectorAll('.sb-mode-btn').forEach(b =>
        b.classList.toggle('act', b.dataset.mode === sidebarMode)
      );
      buildSidebarTree();
    }
  });

  // Search via Pagefind (full-text)
  const searchInput = document.getElementById('search-input');
  const searchResults = document.getElementById('search-results');
  const sidebarTree = document.getElementById('sidebar-tree');

  function showSearchResults(html) {
    sidebarTree.style.display = 'none';
    searchResults.style.display = '';
    searchResults.innerHTML = html;
  }

  function hideSearchResults() {
    searchResults.style.display = 'none';
    searchResults.innerHTML = '';
    sidebarTree.style.display = '';
  }

  const searchClear = document.getElementById('search-clear');

  function clearSearch() {
    searchInput.value = '';
    searchClear.style.display = 'none';
    hideSearchResults();
  }

  searchClear.addEventListener('click', clearSearch);

  searchInput.addEventListener('input', async (e) => {
    const query = e.target.value.trim();
    searchClear.style.display = query ? '' : 'none';

    if (!query) {
      hideSearchResults();
      return;
    }

    if (!pagefind) {
      try {
        pagefind = await import('/pagefind/pagefind.js');
        await pagefind.options({ bundlePath: '/pagefind/' });
      } catch (err) {
        console.warn('Pagefind not available:', err);
        showSearchResults('<div class="search-no-results">Search index not available</div>');
        return;
      }
    }

    try {
      const search = await pagefind.debouncedSearch(query, {}, 200);
      if (!search) return; // superseded by newer keystroke

      const data = await Promise.all(
        search.results.slice(0, 20).map(r => r.data())
      );

      if (data.length === 0) {
        showSearchResults('<div class="search-no-results">No results</div>');
        return;
      }

      showSearchResults(data.map(r => `
        <div class="search-result" data-path="${esc(r.url)}">
          <div class="search-result-title">${esc(r.meta?.title || r.url)}</div>
          <div class="search-result-excerpt">${r.excerpt || ''}</div>
        </div>
      `).join(''));
    } catch (err) {
      console.error('Search error:', err);
      showSearchResults('<div class="search-no-results">Search error</div>');
    }
  });

  searchResults.addEventListener('click', (e) => {
    const result = e.target.closest('.search-result');
    if (result) {
      selectDocument(result.dataset.path);
      clearSearch();
    }
  });
}

// ── Helpers ──

function esc(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ── Start ──

document.addEventListener('DOMContentLoaded', init);
