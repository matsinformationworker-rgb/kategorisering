/**
 * raizemore.com - Frontend Application
 * Handles interactive tree navigation, product browsing, live mapping simulator, and detail modals.
 */

// Global State
const state = {
  currentTab: 'browse',
  selectedCategoryId: null,
  selectedMerchant: 'all',
  searchQuery: '',
  sort: 'price_asc',
  page: 1,
  limit: 24,
  treeData: null,
  openNodes: new Set(['sport-traning', 'leksaker-spel'])
};

// Preset data for Simulator
const SIM_PRESETS = {
  stadium: {
    merchant: 'Stadium',
    category: 'Dammode > Träning > Kompressionstights',
    title: 'Nike Pro Dri-FIT Tights Dam 7/8',
    gender: 'Dam'
  },
  webhallen: {
    merchant: 'Webhallen',
    category: 'Ljud & Bild > Hörlurar > True Wireless',
    title: 'Sony WF-1000XM5 Trådlösa In-Ear',
    gender: ''
  },
  cervera: {
    merchant: 'Cervera',
    category: 'Kök & Dukning > Matlagning > Stekpannor',
    title: 'Skeppshult Gjutjärnspanna 28cm',
    gender: ''
  },
  jollyroom: {
    merchant: 'Jollyroom',
    category: 'Leksaker & Spel > Pussel > 1000 Bitar',
    title: 'Ravensburger Vuxenpussel 1000 Bitar Konst',
    gender: ''
  },
  outnorth: {
    merchant: 'Outnorth',
    category: 'Vattensport > Våtdräkter & Simning',
    title: 'Zone3 Neopren Våtdräkt Herr',
    gender: 'Herr'
  },
  apoteket: {
    merchant: 'Apoteket',
    category: 'Skönhet & Hälsa > Ansikte > Dagkräm',
    title: 'ACO Re-Fresh Fuktgivande Dagkräm 50ml',
    gender: ''
  }
};

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initCategoryTree();
  initProductSearch();
  initMerchantFilters();
  initSorting();
  initPagination();
  initSimulator();
  initModal();
  loadProducts();
});

// --- Tabs ---
function initTabs() {
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const tabId = tab.dataset.tab;
      document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      
      tab.classList.add('active');
      const targetPane = document.getElementById(`tab-${tabId}`);
      if (targetPane) targetPane.classList.add('active');
      state.currentTab = tabId;
    });
  });
}

// --- Category Tree ---
async function initCategoryTree() {
  const container = document.getElementById('category-tree');
  try {
    const res = await fetch('/api/tree');
    const data = await res.json();
    state.treeData = data.tree;
    renderTree(data.tree, container);
  } catch (err) {
    container.innerHTML = '<div class="tree-loading" style="color:red">Kunde inte ladda kategoriträdet.</div>';
  }
}

function renderTree(nodes, container) {
  container.innerHTML = '';
  
  // "All categories" root option
  const allRow = document.createElement('div');
  allRow.className = `node-row ${!state.selectedCategoryId ? 'active' : ''}`;
  allRow.innerHTML = `
    <div class="node-left">
      <span class="lvl-badge lvl-1">ALLA</span>
      <span class="node-title">Alla kategorier</span>
    </div>
  `;
  allRow.addEventListener('click', () => selectCategory(null));
  container.appendChild(allRow);

  nodes.forEach(node => {
    container.appendChild(createTreeNodeElement(node));
  });
}

function createTreeNodeElement(node) {
  const item = document.createElement('div');
  item.className = 'tree-node';

  const hasChildren = node.children && node.children.length > 0;
  const isOpen = state.openNodes.has(node.id);
  const isSelected = state.selectedCategoryId === node.id;

  const row = document.createElement('div');
  row.className = `node-row ${isSelected ? 'active' : ''}`;
  row.innerHTML = `
    <div class="node-left">
      <span class="toggle-arrow ${hasChildren ? (isOpen ? 'open' : '') : 'leaf'}">&#9656;</span>
      <span class="lvl-badge lvl-${node.level}">L${node.level}</span>
      <span class="node-title" title="${node.name}">${node.name}</span>
    </div>
    <span class="node-count">${node.product_count.toLocaleString('sv-SE')}</span>
  `;

  // Arrow click (toggle expansion)
  const arrow = row.querySelector('.toggle-arrow');
  arrow.addEventListener('click', (e) => {
    e.stopPropagation();
    if (!hasChildren) return;
    if (state.openNodes.has(node.id)) {
      state.openNodes.delete(node.id);
    } else {
      state.openNodes.add(node.id);
    }
    const childrenContainer = item.querySelector('.node-children');
    if (childrenContainer) {
      childrenContainer.classList.toggle('open');
      arrow.classList.toggle('open');
    }
  });

  // Row click (select category)
  row.addEventListener('click', () => {
    selectCategory(node.id);
  });

  item.appendChild(row);

  if (hasChildren) {
    const childrenContainer = document.createElement('div');
    childrenContainer.className = `node-children ${isOpen ? 'open' : ''}`;
    node.children.forEach(child => {
      childrenContainer.appendChild(createTreeNodeElement(child));
    });
    item.appendChild(childrenContainer);
  }

  return item;
}

function setMerchant(merchantId, triggerLoad = true) {
  state.selectedMerchant = merchantId;
  state.page = 1;
  document.querySelectorAll('.merchant-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.merchant === merchantId);
  });
  if (triggerLoad) {
    loadProducts();
  }
}

function selectCategory(catId) {
  state.selectedCategoryId = catId;
  state.page = 1;
  
  // Smart auto-switch: if the selected merchant has no products in this domain, switch to 'all'
  if (catId) {
    if (catId.startsWith('leksaker-spel') && state.selectedMerchant === '2xu') {
      setMerchant('all', false);
    } else if (catId.startsWith('sport-traning') && state.selectedMerchant === 'adlibris') {
      setMerchant('all', false);
    }
  }

  // Highlight active in tree
  document.querySelectorAll('.node-row').forEach(r => r.classList.remove('active'));
  // re-render tree or update active
  if (state.treeData) {
    renderTree(state.treeData, document.getElementById('category-tree'));
  }
  
  loadProducts();
}

// --- Product Search & Controls ---
function initProductSearch() {
  const searchInput = document.getElementById('product-search');
  const clearBtn = document.getElementById('search-clear');
  let debounceTimer;

  searchInput.addEventListener('input', (e) => {
    const val = e.target.value.trim();
    clearBtn.style.display = val ? 'block' : 'none';
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      state.searchQuery = val;
      state.page = 1;
      loadProducts();
    }, 250);
  });

  clearBtn.addEventListener('click', () => {
    searchInput.value = '';
    clearBtn.style.display = 'none';
    state.searchQuery = '';
    state.page = 1;
    loadProducts();
  });

  document.getElementById('btn-reset-filters').addEventListener('click', () => {
    state.selectedCategoryId = null;
    setMerchant('all', false);
    state.searchQuery = '';
    searchInput.value = '';
    clearBtn.style.display = 'none';
    state.page = 1;
    if (state.treeData) {
      renderTree(state.treeData, document.getElementById('category-tree'));
    }
    loadProducts();
  });
}

function initMerchantFilters() {
  document.querySelectorAll('.merchant-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      setMerchant(btn.dataset.merchant, true);
    });
  });
}

function initSorting() {
  const sortSelect = document.getElementById('sort-select');
  sortSelect.addEventListener('change', (e) => {
    state.sort = e.target.value;
    state.page = 1;
    loadProducts();
  });
}

function initPagination() {
  document.getElementById('page-prev').addEventListener('click', () => {
    if (state.page > 1) {
      state.page--;
      loadProducts();
      window.scrollTo({ top: 120, behavior: 'smooth' });
    }
  });

  document.getElementById('page-next').addEventListener('click', () => {
    state.page++;
    loadProducts();
    window.scrollTo({ top: 120, behavior: 'smooth' });
  });
}

// --- Load Products ---
async function loadProducts() {
  const grid = document.getElementById('product-grid');
  grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #94a3b8;">Laddar produkter...</div>';

  const params = new URLSearchParams({
    page: state.page,
    limit: state.limit,
    sort: state.sort
  });

  if (state.selectedCategoryId) params.append('category_id', state.selectedCategoryId);
  if (state.selectedMerchant && state.selectedMerchant !== 'all') params.append('merchant', state.selectedMerchant);
  if (state.searchQuery) params.append('q', state.searchQuery);

  try {
    const res = await fetch(`/api/products?${params.toString()}`);
    const data = await res.json();
    renderProducts(data);
  } catch (err) {
    grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: red;">Kunde inte hämta produkter.</div>';
  }
}

function renderProducts(data) {
  const grid = document.getElementById('product-grid');
  const paginationBar = document.getElementById('pagination-bar');
  const activeFiltersContainer = document.getElementById('active-filters');
  grid.innerHTML = '';

  // Update Breadcrumb Bar
  const breadcrumbBar = document.getElementById('breadcrumb-bar');
  breadcrumbBar.innerHTML = '';

  const rootCrumb = document.createElement('span');
  rootCrumb.className = `crumb ${!data.category ? 'active' : ''}`;
  rootCrumb.textContent = 'Alla kategorier';
  rootCrumb.addEventListener('click', () => selectCategory(null));
  breadcrumbBar.appendChild(rootCrumb);

  if (data.category && data.category.breadcrumb) {
    data.category.breadcrumb.forEach((b, idx) => {
      const sep = document.createElement('span');
      sep.className = 'sep';
      sep.textContent = '>';
      breadcrumbBar.appendChild(sep);

      const isLast = idx === data.category.breadcrumb.length - 1;
      const crumb = document.createElement('span');
      crumb.className = `crumb ${isLast ? 'active' : ''}`;
      crumb.textContent = b.name;
      if (!isLast) {
        crumb.addEventListener('click', () => selectCategory(b.id));
      }
      breadcrumbBar.appendChild(crumb);
    });
  }

  // Update Active Filter Badges
  if (activeFiltersContainer) {
    activeFiltersContainer.innerHTML = '';
    
    if (state.selectedMerchant && state.selectedMerchant !== 'all') {
      const merchantName = state.selectedMerchant === '2xu' ? '2XU (Adtraction)' : 'Adlibris (Tradedoubler)';
      const pill = document.createElement('span');
      pill.className = 'filter-chip';
      pill.innerHTML = `Butik: <strong>${merchantName}</strong> <span class="chip-remove">&times;</span>`;
      pill.querySelector('.chip-remove').addEventListener('click', () => {
        setMerchant('all');
      });
      activeFiltersContainer.appendChild(pill);
    }

    if (state.searchQuery) {
      const pill = document.createElement('span');
      pill.className = 'filter-chip';
      pill.innerHTML = `Sök: "<strong>${state.searchQuery}</strong>" <span class="chip-remove">&times;</span>`;
      pill.querySelector('.chip-remove').addEventListener('click', () => {
        document.getElementById('product-search').value = '';
        document.getElementById('search-clear').style.display = 'none';
        state.searchQuery = '';
        state.page = 1;
        loadProducts();
      });
      activeFiltersContainer.appendChild(pill);
    }
  }

  // Update Result Count
  const countText = document.getElementById('results-count-text');
  const start = data.total > 0 ? (data.page - 1) * data.limit + 1 : 0;
  const end = Math.min(data.page * data.limit, data.total);
  countText.textContent = `Visar ${start}–${end} av ${data.total.toLocaleString('sv-SE')} produkter`;

  // Empty state handling
  if (data.items.length === 0) {
    paginationBar.style.display = 'none';
    
    let reasonMessage = '';
    if (state.selectedMerchant === '2xu' && state.selectedCategoryId && state.selectedCategoryId.startsWith('leksaker-spel')) {
      reasonMessage = `
        <div style="margin: 16px 0;">
          <p style="font-size: 14px; color: #475569; margin-bottom: 12px;">
            Butiken <strong>2XU</strong> är ett sportklädesmärke och har inga produkter i <em>Leksaker & Spel</em>.<br>
            Alla spel och pussel i denna kategori levereras från <strong>Adlibris (Tradedoubler)</strong>.
          </p>
          <div style="display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
            <button id="btn-switch-to-adlibris" class="btn-primary-sim" style="width: auto; padding: 8px 16px; font-size: 13px;">
              Visa alla produkter från Adlibris &rarr;
            </button>
            <button id="btn-switch-to-all" class="preset-btn" style="padding: 8px 16px; font-size: 13px;">
              Visa alla butiker
            </button>
          </div>
        </div>
      `;
    } else if (state.selectedMerchant && state.selectedMerchant !== 'all') {
      reasonMessage = `
        <div style="margin: 16px 0;">
          <p style="font-size: 14px; color: #475569; margin-bottom: 12px;">
            Inga produkter matchade i den valda butiken (<strong>${state.selectedMerchant.toUpperCase()}</strong>).
          </p>
          <button id="btn-switch-to-all" class="btn-primary-sim" style="width: auto; padding: 8px 16px; font-size: 13px; margin: 0 auto;">
            Återställ butiksfilter (Visa alla butiker)
          </button>
        </div>
      `;
    } else {
      reasonMessage = `
        <p style="font-size: 13px; color: #64748b; margin-top: 6px;">Prova att rensa sökordet eller välj en bredare kategori i trädet.</p>
      `;
    }

    grid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 48px 24px; background: white; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: var(--shadow-sm);">
        <div style="width: 48px; height: 48px; background: #f1f5f9; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 12px;">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
        </div>
        <h3 style="font-size: 17px; font-weight: 700; color: #1e293b;">Inga produkter matchade sökningen</h3>
        ${reasonMessage}
      </div>
    `;

    // Hook up switch buttons if present
    const btnSwitchAdlibris = document.getElementById('btn-switch-to-adlibris');
    if (btnSwitchAdlibris) {
      btnSwitchAdlibris.addEventListener('click', () => setMerchant('adlibris'));
    }
    const btnSwitchAll = document.getElementById('btn-switch-to-all');
    if (btnSwitchAll) {
      btnSwitchAll.addEventListener('click', () => setMerchant('all'));
    }
    return;
  }

  // Show pagination when items exist
  paginationBar.style.display = 'flex';

  // Render Product Cards
  data.items.forEach(p => {
    const card = document.createElement('div');
    card.className = 'product-card';

    const merchantClass = p.network === 'adtraction' ? 'adtraction' : 'tradedoubler';
    const networkLabel = p.network === 'adtraction' ? 'Adtraction' : 'Tradedoubler';
    const merchantName = p.merchant.toUpperCase();

    card.innerHTML = `
      <div class="product-thumb-box">
        <span class="merchant-badge ${merchantClass}">${merchantName} &bull; ${networkLabel}</span>
        <img class="product-thumb" src="${p.image_url}" alt="${p.title}" loading="lazy" onerror="this.src='https://via.placeholder.com/200x200?text=Bild+saknas'">
      </div>
      <div class="product-info">
        <span class="product-brand">${p.brand || 'Okänt märke'}</span>
        <h4 class="product-name" title="${p.title}">${p.title}</h4>
        <span class="product-cat-pill" title="${p.category_path}">${p.category_path ? p.category_path.split(' > ').slice(-1)[0] : 'Okategoriserad'}</span>
        <div class="product-bottom-row">
          <span class="product-price">${p.price > 0 ? p.price.toLocaleString('sv-SE') + ' kr' : 'Pris saknas'}</span>
          <button class="btn-mapping-info" data-pid="${p.id}">Mappningsinfo &rarr;</button>
        </div>
      </div>
    `;

    card.querySelector('.btn-mapping-info').addEventListener('click', () => {
      openProductModal(p);
    });

    grid.appendChild(card);
  });

  // Update Pagination
  document.getElementById('page-prev').disabled = data.page <= 1;
  document.getElementById('page-next').disabled = data.page >= data.total_pages;
  document.getElementById('page-indicator').textContent = `Sida ${data.page} av ${data.total_pages || 1}`;
}

// --- Simulator ---
function initSimulator() {
  const form = document.getElementById('sim-form');
  const merchantInput = document.getElementById('sim-merchant');
  const catInput = document.getElementById('sim-cat');
  const titleInput = document.getElementById('sim-title');
  const genderInput = document.getElementById('sim-gender');

  // Presets
  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const p = SIM_PRESETS[btn.dataset.preset];
      if (p) {
        merchantInput.value = p.merchant;
        catInput.value = p.category;
        titleInput.value = p.title;
        genderInput.value = p.gender;
        runSimulation();
      }
    });
  });

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    runSimulation();
  });
}

async function runSimulation() {
  const merchant = document.getElementById('sim-merchant').value.trim();
  const source_category = document.getElementById('sim-cat').value.trim();
  const title = document.getElementById('sim-title').value.trim();
  const gender = document.getElementById('sim-gender').value;

  if (!source_category) {
    alert('Vänligen fyll i källkategori');
    return;
  }

  const resultBox = document.getElementById('sim-result-box');
  resultBox.innerHTML = '<div style="text-align:center; padding: 40px; color:#94a3b8;">Kör semantisk analys...</div>';

  try {
    const res = await fetch('/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_category, title, merchant, gender })
    });
    const data = await res.json();
    renderSimulationResult(data, resultBox);
  } catch (err) {
    resultBox.innerHTML = '<div style="color:red; padding:20px;">Ett fel uppstod vid simulering.</div>';
  }
}

function renderSimulationResult(data, container) {
  const r = data.result;
  const confidencePercent = Math.round(r.confidence * 100);

  let candidateRows = '';
  if (r.top_candidates && r.top_candidates.length > 0) {
    candidateRows = r.top_candidates.map(c => `
      <tr>
        <td><strong>L${c.level}</strong> ${c.name}</td>
        <td style="color:#64748b;">${c.path}</td>
        <td><span style="font-weight:700;">${Math.round(c.score * 100)}%</span></td>
      </tr>
    `).join('');
  }

  const breadcrumbSteps = r.breadcrumb.map((b, idx) => `
    <span class="crumb-step ${idx === r.breadcrumb.length - 1 ? 'highlight' : ''}">
      L${b.level}: ${b.name}
    </span>
  `).join(' <span style="color:#94a3b8;">&rarr;</span> ');

  container.innerHTML = `
    <div class="match-banner">
      <div class="match-header">
        <span class="match-title-tag">Mappad Master-Kategori</span>
        <span class="match-confidence">Konfidens: ${confidencePercent}%</span>
      </div>
      <div class="match-path">${r.path_string}</div>
      <div class="match-rule">Regel: ${r.rule_applied}</div>
    </div>

    <div class="sim-details-box">
      <div>
        <label style="font-size:12px; font-weight:700; color:#64748b; text-transform:uppercase; display:block; margin-bottom:6px;">Hierarkisk Struktur (Max 4 Nivåer):</label>
        <div class="crumb-trail-visual">
          ${breadcrumbSteps}
        </div>
      </div>

      <div>
        <label style="font-size:12px; font-weight:700; color:#64748b; text-transform:uppercase; display:block; margin-bottom:6px;">Övriga Utvärderade Kandidater:</label>
        <table class="candidates-table">
          <thead>
            <tr>
              <th>Kategori</th>
              <th>Sökväg</th>
              <th>Likhet</th>
            </tr>
          </thead>
          <tbody>
            ${candidateRows}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// --- Product Modal ---
function initModal() {
  const modal = document.getElementById('product-modal');
  const closeBtn = document.getElementById('modal-close');

  closeBtn.addEventListener('click', () => {
    modal.style.display = 'none';
  });

  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.style.display = 'none';
  });
}

function openProductModal(p) {
  const modal = document.getElementById('product-modal');
  const body = document.getElementById('modal-body');

  const rawAttrs = Object.entries(p.attributes || {})
    .filter(([k, v]) => v)
    .map(([k, v]) => `${k}: ${v}`)
    .join(', ');

  body.innerHTML = `
    <div style="display:flex; gap:16px; margin-bottom:16px; align-items:flex-start;">
      <img src="${p.image_url}" style="width:100px; height:100px; object-fit:contain; border:1px solid #e2e8f0; border-radius:8px; padding:4px;" onerror="this.src='https://via.placeholder.com/100x100'">
      <div>
        <span style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase;">${p.brand} &bull; ${p.merchant.toUpperCase()}</span>
        <h3 style="font-size:16px; font-weight:700; margin:4px 0 6px;">${p.title}</h3>
        <span style="font-size:16px; font-weight:800; color:#0f172a;">${p.price > 0 ? p.price.toLocaleString('sv-SE') + ' kr' : 'Pris saknas'}</span>
      </div>
    </div>

    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:12px; margin-bottom:16px;">
      <div class="detail-row">
        <div class="detail-label">Affiliatenätverk:</div>
        <div class="detail-value">${p.network.toUpperCase()}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Källkategori i feed:</div>
        <div class="detail-value" style="color:#b91c1c; font-weight:600;">${p.source_category || 'Ej angivet'}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Attribut (kön m.m.):</div>
        <div class="detail-value">${rawAttrs || 'Inga extra attribut'}</div>
      </div>
    </div>

    <div style="background:#ecfdf5; border:1px solid #a7f3d0; border-radius:8px; padding:14px; margin-bottom:16px;">
      <div style="font-size:11px; font-weight:700; color:#059669; text-transform:uppercase; margin-bottom:4px;">Tilldelad Master-Kategori (Max 4 Nivåer)</div>
      <div style="font-size:15px; font-weight:800; color:#064e3b; margin-bottom:6px;">${p.category_path}</div>
      <div class="detail-row" style="border:none; padding:0;">
        <div class="detail-label" style="color:#047857;">Mappningsregel:</div>
        <div class="detail-value" style="color:#047857;">${p.mapping_rule}</div>
      </div>
      <div class="detail-row" style="border:none; padding:0;">
        <div class="detail-label" style="color:#047857;">Konfidens:</div>
        <div class="detail-value" style="color:#047857;">${Math.round(p.mapping_confidence * 100)}%</div>
      </div>
    </div>

    ${p.url ? `<a href="${p.url}" target="_blank" rel="noopener noreferrer" style="display:block; text-align:center; background:#2563eb; color:white; font-weight:700; padding:10px; border-radius:6px; text-decoration:none;">Öppna produktsida hos butik &rarr;</a>` : ''}
  `;

  modal.style.display = 'flex';
}
