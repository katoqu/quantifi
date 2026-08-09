import {
  createCategory,
  createChangeEvent,
  createEntry,
  createMetric,
  deleteCategory,
  deleteEntry,
  exportDataAsCsv,
  getMetricByName,
  importCsvText,
  listCategories,
  listChangeEvents,
  listEntries,
  listMetrics,
  seedBaseData,
  updateCategory,
  updateEntry,
  updateMetric,
  updateChangeEvent,
  deleteChangeEvent,
  STORE_NAMES,
} from './db.js';

const ui = {
  tabs: Array.from(document.querySelectorAll('.tab')),
  views: Array.from(document.querySelectorAll('.view')),
  metricGrid: document.querySelector('#metricGrid'),
  metricSelect: document.querySelector('#metricSelect'),
  metricName: document.querySelector('#metricName'),
  metricCategory: document.querySelector('#metricCategory'),
  metricUnit: document.querySelector('#metricUnit'),
  metricType: document.querySelector('#metricType'),
  metricKind: document.querySelector('#metricKind'),
  metricDescription: document.querySelector('#metricDescription'),
  metricList: document.querySelector('#metricList'),
  metricSearch: document.querySelector('#metricSearch'),
  metricSearchDatalist: document.querySelector('#metricSearchDatalist'),
  metricEditForm: document.querySelector('#metricEditForm'),
  metricEditFields: document.querySelector('#metricEditFields'),
  editMetricName: document.querySelector('#editMetricName'),
  editMetricDescription: document.querySelector('#editMetricDescription'),
  addMetricBtn: document.querySelector('#addMetricBtn'),
  editMetricBtn: document.querySelector('#editMetricBtn'),
  saveMetricEdit: document.querySelector('#saveMetricEdit'),
  cancelMetricEdit: document.querySelector('#cancelMetricEdit'),
  archiveMetricEdit: document.querySelector('#archiveMetricEdit'),
  cancelMetric: document.querySelector('#cancelMetric'),
  categoryList: document.querySelector('#categoryList'),
  categoryForm: document.querySelector('#categoryForm'),
  categoryName: document.querySelector('#categoryName'),
  categoryDescriptionAdd: document.querySelector('#categoryDescriptionAdd'),
  categorySearch: document.querySelector('#categorySearch'),
  categorySearchDatalist: document.querySelector('#categorySearchDatalist'),
  categoryEditForm: document.querySelector('#categoryEditForm'),
  categoryEditFields: document.querySelector('#categoryEditFields'),
  editCategoryName: document.querySelector('#editCategoryName'),
  editCategoryDescription: document.querySelector('#editCategoryDescription'),
  addCategoryBtn: document.querySelector('#addCategoryBtn'),
  editCategoryBtn: document.querySelector('#editCategoryBtn'),
  deleteCategoryBtn: document.querySelector('#deleteCategoryBtn'),
  saveCategoryEdit: document.querySelector('#saveCategoryEdit'),
  cancelCategoryEdit: document.querySelector('#cancelCategoryEdit'),
  cancelCategory: document.querySelector('#cancelCategory'),
  changeList: document.querySelector('#changeList'),
  statsSummary: document.querySelector('#statsSummary'),
  entryForm: document.querySelector('#entryForm'),
  changeForm: document.querySelector('#changeForm'),
  metricForm: document.querySelector('#metricForm'),
  exportButton: document.querySelector('#exportButton'),
  importButton: document.querySelector('#importButton'),
  importFile: document.querySelector('#importFile'),
  installButton: document.querySelector('#installButton'),
  numericValueField: document.querySelector('#numericValueField'),
  entryValue: document.querySelector('#entryValue'),
  strengthWorkoutFields: document.querySelector('#strengthWorkoutFields'),
  strengthLoadInput: document.querySelector('#strengthLoadInput'),
  strengthRepsInput: document.querySelector('#strengthRepsInput'),
  strengthAddSetButton: document.querySelector('#strengthAddSetButton'),
  strengthSetList: document.querySelector('#strengthSetList'),
  strengthBaseline: document.querySelector('#strengthBaseline'),
  entryTargetAction: document.querySelector('#entryTargetAction'),
  targetActionField: document.querySelector('#targetActionField'),
  entryDatePills: document.querySelector('#entryDatePills'),
  entryDate: document.querySelector('#entryDate'),
  entryTime: document.querySelector('#entryTime'),
  dateTimeFields: document.querySelector('#dateTimeFields'),
  targetActionPills: document.querySelector('#targetActionPills'),
  homeSearch: document.querySelector('#homeSearch'),
  homeSearchDatalist: document.querySelector('#homeSearchDatalist'),
  showCategoriesBtn: document.querySelector('#showCategoriesBtn'),
  showMetricsBtn: document.querySelector('#showMetricsBtn'),
  settingsCategoriesPanel: document.querySelector('#settingsCategoriesPanel'),
  settingsMetricsPanel: document.querySelector('#settingsMetricsPanel'),
  backupReminderBanner: document.querySelector('#backupReminderBanner'),
  unsavedCount: document.querySelector('#unsavedCount'),
  logShowArchived: document.querySelector('#logShowArchived'),
  changeCategory: document.querySelector('#changeCategory'),
  changeDate: document.querySelector('#changeDate'),
  changeTime: document.querySelector('#changeTime'),
  statsMetricSelect: document.querySelector('#statsMetricSelect'),
  statsControls: document.querySelector('#statsControls'),
  statsPeriodControl: document.querySelector('#statsPeriodControl'),
  statsZerosToggle: document.querySelector('#statsZerosToggle'),
  statsStrengthControl: document.querySelector('#statsStrengthControl'),
  statsStrengthSelect: document.querySelector('#statsStrengthSelect'),
  statsChartContainer: document.querySelector('#statsChartContainer'),
  themeToggle: document.querySelector('#themeToggle'),
  entriesModal: document.querySelector('#entriesModal'),
  entriesModalTitle: document.querySelector('#entriesModalTitle'),
  entriesTableBody: document.querySelector('#entriesTableBody'),
  closeEntriesModal: document.querySelector('#closeEntriesModal'),
  modalOverlay: document.querySelector('.modal-overlay'),
};

let deferredPrompt = null;
let strengthSets = [];
let editingSetIndex = null;

let editingEventId = null;
let endingEventId = null;
let revivingEventId = null;
let editingEntryId = null;

let activeFilters = { home: 'Recent', add: 'Recent', stats: 'Recent', log: 'Recent' };
let homeSearchTerm = '';

let activeVizSettings = {
  metricId: null,
  period: 'Month',
  zeros: false,
  strengthAgg: 'Max Load',
};

function renderMarkdown(text) {
  if (!text) return '';
  let html = text
    .replace(/&/g, '&')
    .replace(/</g, '<')
    .replace(/>/g, '>');

  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  html = html.replace(/`(.*?)`/g, '<code>$1</code>');

  const lines = html.split('\n');
  let inList = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.startsWith('- ') || line.startsWith('* ')) {
      const content = line.substring(2);
      if (!inList) {
        lines[i] = '<ul><li>' + content + '</li>';
        inList = true;
      } else {
        lines[i] = '<li>' + content + '</li>';
      }
    } else {
      if (inList) {
        lines[i] = '</ul>' + lines[i];
        inList = false;
      }
    }
  }
  if (inList) {
    lines.push('</ul>');
  }
  html = lines.join('\n');

  const blocks = html.split(/\n\s*\n/);
  html = blocks.map(block => {
    block = block.trim();
    if (!block) return '';
    if (block.startsWith('<h') || block.startsWith('<ul') || block.startsWith('<li') || block.startsWith('<ol')) {
      return block;
    }
    return `<p>${block.replace(/\n/g, '<br />')}</p>`;
  }).join('');

  return html;
}

function resetChangeFormDateTime() {
  const now = new Date();
  const dateStr = now.toISOString().split('T')[0];
  const timeStr = now.toTimeString().slice(0, 5);
  if (ui.changeDate) ui.changeDate.value = dateStr;
  if (ui.changeTime) ui.changeTime.value = timeStr;
}

async function getRecentMetricIds(entries, limit = 5) {
  if (!entries || entries.length === 0) return [];
  const sorted = [...entries].sort((a, b) => new Date(b.recordedAt) - new Date(a.recordedAt));
  const seen = new Set();
  const recentIds = [];
  for (const entry of sorted) {
    if (!seen.has(entry.metricId)) {
      seen.add(entry.metricId);
      recentIds.push(entry.metricId);
      if (recentIds.length >= limit) break;
    }
  }
  return recentIds;
}

async function filterMetricsForView(viewName, metrics, entries, categories) {
  const filter = activeFilters[viewName];
  if (!filter || filter === 'Recent') {
    const recentIds = await getRecentMetricIds(entries, 5);
    if (recentIds.length > 0) {
      const recentMap = new Map(recentIds.map((id, index) => [id, index]));
      return [...metrics].sort((a, b) => {
        const aIndex = recentMap.has(a.id) ? recentMap.get(a.id) : Infinity;
        const bIndex = recentMap.has(b.id) ? recentMap.get(b.id) : Infinity;
        if (aIndex !== bIndex) return aIndex - bIndex;
        return a.name.localeCompare(b.name);
      });
    }
    return [...metrics].sort((a, b) => a.name.localeCompare(b.name));
  }
  const cat = categories.find((c) => c.name.toLowerCase() === filter.toLowerCase());
  if (!cat) return [];
  return metrics.filter((m) => m.categoryId === cat.id);
}

function filterMetricsBySearch(metrics, categories, searchTerm) {
  if (!searchTerm) return metrics;
  const term = searchTerm.trim().toLowerCase();
  const categoryMap = new Map(categories.map((c) => [c.id, c.name.toLowerCase()]));
  return metrics.filter((metric) => {
    const nameMatch = metric.name.toLowerCase().includes(term);
    const categoryName = categoryMap.get(metric.categoryId) || '';
    const catMatch = categoryName.includes(term);
    return nameMatch || catMatch;
  });
}

function updateBackupBanner() {
  const count = Number(localStorage.getItem('quantifi-unsaved-count') || 0);
  ui.unsavedCount.textContent = count;
  if (count >= 5) {
    ui.backupReminderBanner.classList.remove('hidden');
  } else {
    ui.backupReminderBanner.classList.add('hidden');
  }
}

function incrementUnsavedCount() {
  const count = Number(localStorage.getItem('quantifi-unsaved-count') || 0) + 1;
  localStorage.setItem('quantifi-unsaved-count', count);
  updateBackupBanner();
}

function resetUnsavedCount() {
  localStorage.setItem('quantifi-unsaved-count', 0);
  updateBackupBanner();
}

function formatStrengthSession(entry) {
  if (!entry) return '—';
  const sets = entry.sets || [];
  if (!Array.isArray(sets) || sets.length === 0) {
    return entry.value !== null && entry.value !== undefined ? `${Number(entry.value).toFixed(1)} kg` : '—';
  }
  const summaryLoad = Number(entry.loadKg ?? entry.value ?? 0).toFixed(1);
  const repsSeries = sets.map((s) => s.reps).join('/');
  return `${summaryLoad} kg × ${repsSeries} reps × ${sets.length} sets`;
}

function resetEntryFormDateTime() {
  const now = new Date();
  const dateStr = now.toISOString().split('T')[0];
  const timeStr = now.toTimeString().slice(0, 5);
  if (ui.entryDate) ui.entryDate.value = dateStr;
  if (ui.entryTime) ui.entryTime.value = timeStr;
}

async function initializeDatabase() {
  // Initialize light/dark theme preference
  const savedTheme = localStorage.getItem('quantifi-pwa-theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  if (ui.themeToggle) {
    ui.themeToggle.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('quantifi-pwa-theme', newTheme);
    });
  }

  await seedBaseData();
  resetEntryFormDateTime();
  resetChangeFormDateTime();
  updateBackupBanner();
  renderAll();
}

async function renderAll() {
  await renderMetricDropdown();
  await renderHome();
  await renderLogs();
  await renderStats();
  await renderSettings();
}

function renderStrengthSetList() {
  ui.strengthSetList.innerHTML = strengthSets.length
    ? strengthSets.map((set, index) => {
        const isEditing = editingSetIndex === index;
        if (isEditing) {
          return `
            <div class="item edit-mode">
              <strong>Set ${index + 1} (Editing)</strong>
              <div class="strength-grid" style="margin: 0.5rem 0;">
                <label>
                  Load (kg)
                  <input type="number" id="editSetLoad" step="0.5" min="0" value="${set.loadKg}" style="width: 100%;" />
                </label>
                <label>
                  Reps
                  <input type="number" id="editSetReps" step="1" min="1" value="${set.reps}" style="width: 100%;" />
                </label>
              </div>
              <div style="display: flex; gap: 0.5rem; width: 100%;">
                <button type="button" id="saveEditSetButton" class="primary" style="flex: 1;">Save</button>
                <button type="button" id="cancelEditSetButton" class="secondary" style="flex: 1;">Cancel</button>
              </div>
            </div>
          `;
        }
        return `
          <div class="item">
            <strong>Set ${index + 1}</strong>
            <div>${Number(set.loadKg).toFixed(1)} kg × ${set.reps} reps</div>
            <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
              <button type="button" data-edit-set="${index}" class="secondary">Edit</button>
              <button type="button" data-remove-set="${index}" class="secondary">Remove</button>
            </div>
          </div>
        `;
      }).join('')
    : '<p>No sets yet.</p>';
}

async function syncAddFormMode() {
  const metrics = await listMetrics(false);
  const metric = metrics.find((item) => item.id === ui.metricSelect.value) || metrics[0] || null;

  const isStrength = metric?.metricKind === 'strength_session';
  ui.numericValueField.classList.toggle('hidden', isStrength);
  ui.strengthWorkoutFields.classList.toggle('hidden', !isStrength);

  const isScore = metric?.metricKind === 'score' || metric?.unitType === 'integer_range';
  ui.targetActionField.classList.toggle('hidden', isScore);

  if (isStrength) {
    const [entries] = await Promise.all([listEntries()]);
    const metricEntries = entries.filter((entry) => entry.metricId === metric.id);
    const lastEntry = metricEntries.sort((a, b) => new Date(b.recordedAt) - new Date(a.recordedAt))[0];
    ui.strengthLoadInput.value = lastEntry?.loadKg ?? lastEntry?.value ?? 0;
    
    if (lastEntry && Array.isArray(lastEntry.sets) && lastEntry.sets.length > 0) {
      const formattedSets = lastEntry.sets
        .map((set, index) => `Set ${index + 1}: ${Number(set.loadKg || set.load_kg || 0).toFixed(1)} kg × ${set.reps} reps`)
        .join(' — ');
      const dateStr = new Date(lastEntry.recordedAt).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
      ui.strengthBaseline.innerHTML = `<strong>📊 Previous Session (${dateStr}):</strong><br>${formattedSets}`;
      ui.strengthBaseline.classList.remove('hidden');
    } else {
      ui.strengthBaseline.innerHTML = '';
      ui.strengthBaseline.classList.add('hidden');
    }

    renderStrengthSetList();
  }
}

async function renderMetricDropdown() {
  const [metrics, entries, categories] = await Promise.all([
    listMetrics(false),
    listEntries(),
    listCategories(),
  ]);

  // Render date pills
  if (ui.entryDatePills) {
    ui.entryDatePills.innerHTML = ['Now', 'Yesterday', 'Custom']
      .map((opt) => `<button class="pill ${opt === 'Now' ? 'active' : ''}" data-date="${opt}">${opt}</button>`)
      .join('');
    
    // Set default date/time for Now
    const now = new Date();
    if (ui.entryDate) ui.entryDate.value = now.toISOString().split('T')[0];
    if (ui.entryTime) ui.entryTime.value = now.toTimeString().slice(0, 5);
  }

  // Render target action pills
  if (ui.targetActionPills) {
    ui.targetActionPills.innerHTML = ['None', 'Reduce', 'Stay', 'Increase', 'Pause']
      .map((opt) => `<button class="pill ${opt === 'None' ? 'active' : ''}" data-target="${opt}">${opt}</button>`)
      .join('');
  }

  const filteredMetrics = await filterMetricsForView('add', metrics, entries, categories);
  const previousValue = ui.metricSelect.value;

  ui.metricSelect.innerHTML = filteredMetrics
    .map((metric) => `<option value="${metric.id}">${metric.name}</option>`)
    .join('');

  if (filteredMetrics.some((m) => m.id === previousValue)) {
    ui.metricSelect.value = previousValue;
  } else {
    ui.metricSelect.value = filteredMetrics[0]?.id ?? '';
  }

  await syncAddFormMode();
}

function renderSparkline(values, color, { kind = 'quantitative', higherIsBetter = true, rangeStart = null, rangeEnd = null } = {}) {
  const clean = (values || []).map(Number).filter(v => !Number.isNaN(v));
  if (clean.length === 0) {
    return '<span style="font-size: 0.85rem; opacity: 0.6; padding: 4px 0; display: inline-block;">—</span>';
  }

  const width = 192;
  const height = 28;
  const pad = 4;

  const vmin = Math.min(...clean);
  const vmax = Math.max(...clean);

  const toY = (v) => {
    if (clean.length === 1 || vmax === vmin) {
      return height / 2;
    }
    const span = vmax - vmin;
    return height - pad - ((v - vmin) / span) * (height - pad * 2);
  };

  let lastX = 0;
  let lastY = height / 2;

  if (kind === 'count') {
    const n = clean.length;
    const barGap = 1.0;
    const available = width - pad * 2;
    const barW = Math.max(2.0, (available - barGap * (n - 1)) / Math.max(1, n));
    const vmaxLocal = Math.max(1.0, vmax);
    const rects = [];
    let lastCx = null;
    let lastCy = null;

    for (let i = 0; i < n; i++) {
      const v = clean[i];
      const x = pad + i * (barW + barGap);
      const h = vmaxLocal ? (v / vmaxLocal) * (height - pad * 2) : 0;
      const y = height - pad - h;
      const isLast = i === n - 1;
      if (isLast) {
        lastCx = x + barW / 2;
        lastCy = y;
      }
      rects.push(
        `<rect x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="${barW.toFixed(2)}" height="${h.toFixed(2)}" rx="1.2" ry="1.2" fill="${color}" opacity="0.85" stroke="rgba(0,0,0,0.22)" stroke-width="${isLast ? 1 : 0}"/>`
      );
    }

    let lollipop = '';
    if (lastCx !== null && lastCy !== null) {
      lollipop = `
        <line x1="${lastCx.toFixed(2)}" x2="${lastCx.toFixed(2)}" y1="${lastCy.toFixed(2)}" y2="${pad.toFixed(2)}" stroke="rgba(0,0,0,0.16)" stroke-width="1"/>
        <circle cx="${lastCx.toFixed(2)}" cy="${lastCy.toFixed(2)}" r="2.6" fill="${color}" stroke="white" stroke-width="1.2"/>
      `;
    }

    return `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" preserveAspectRatio="none" aria-hidden="true">${rects.join('')}${lollipop}</svg>`;
  }

  if (kind === 'score') {
    let rs = rangeStart !== null && rangeStart !== undefined ? Number(rangeStart) : Math.round(vmin);
    let re = rangeEnd !== null && rangeEnd !== undefined ? Number(rangeEnd) : Math.round(vmax);
    if (Number.isNaN(rs)) rs = Math.round(vmin);
    if (Number.isNaN(re)) re = Math.round(vmax);
    const span = Math.max(1, re - rs);
    const n = clean.length;
    const gap = 1.0;
    const available = width - pad * 2;
    const blockW = Math.max(2.0, (available - gap * (n - 1)) / Math.max(1, n));
    const rects = [];
    let lastCx = null;
    let lastCy = null;
    let lastFill = null;

    for (let i = 0; i < n; i++) {
      const v = clean[i];
      const x = pad + i * (blockW + gap);
      const tHeight = Math.min(1.0, Math.max(0.0, (v - rs) / span));
      const tColor = !higherIsBetter ? (1.0 - tHeight) : tHeight;
      const r = Math.round(220 * (1.0 - tColor) + 40 * tColor);
      const g = Math.round(60 * (1.0 - tColor) + 180 * tColor);
      const b = Math.round(70 * (1.0 - tColor) + 80 * tColor);
      const fill = `rgb(${r},${g},${b})`;
      const h = Math.max(2.0, tHeight * (height - pad * 2));
      const y = height - pad - h;
      const isLast = i === n - 1;
      if (isLast) {
        lastCx = x + blockW / 2;
        lastCy = y;
        lastFill = fill;
      }
      rects.push(
        `<rect x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="${blockW.toFixed(2)}" height="${h.toFixed(2)}" rx="2" ry="2" fill="${fill}" opacity="0.95" stroke="rgba(0,0,0,0.22)" stroke-width="${isLast ? 1 : 0}"/>`
      );
    }

    let lollipop = '';
    if (lastCx !== null && lastCy !== null) {
      lollipop = `
        <line x1="${lastCx.toFixed(2)}" x2="${lastCx.toFixed(2)}" y1="${lastCy.toFixed(2)}" y2="${pad.toFixed(2)}" stroke="rgba(0,0,0,0.16)" stroke-width="1"/>
        <circle cx="${lastCx.toFixed(2)}" cy="${lastCy.toFixed(2)}" r="2.6" fill="${lastFill || color}" stroke="white" stroke-width="1.2"/>
      `;
    }

    return `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" preserveAspectRatio="none" aria-hidden="true">${rects.join('')}${lollipop}</svg>`;
  }

  // quantitative
  let points = '';
  if (clean.length === 1 || vmax === vmin) {
    points = `${pad},${height / 2} ${width - pad},${height / 2}`;
    lastX = width - pad;
    lastY = height / 2;
  } else {
    const step = (width - pad * 2) / (clean.length - 1);
    const pts = [];
    for (let i = 0; i < clean.length; i++) {
      const x = pad + i * step;
      const y = toY(clean[i]);
      pts.push(`${x.toFixed(2)},${y.toFixed(2)}`);
      lastX = x;
      lastY = y;
    }
    points = pts.join(' ');
  }

  return `
    <svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" preserveAspectRatio="none" aria-hidden="true">
      <line x1="${lastX.toFixed(2)}" x2="${lastX.toFixed(2)}" y1="${lastY.toFixed(2)}" y2="${pad.toFixed(2)}" stroke="rgba(0,0,0,0.16)" stroke-width="1"/>
      <polyline fill="none" stroke="${color}" stroke-width="2" points="${points}" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="${lastX.toFixed(2)}" cy="${lastY.toFixed(2)}" r="2.6" fill="${color}" stroke="white" stroke-width="1.2"/>
    </svg>
  `;
}

async function renderHome() {
  console.log('renderHome called');
  const [metrics, entries, categories] = await Promise.all([
    listMetrics(true),
    listEntries(),
    listCategories(),
  ]);
  console.log('Metrics:', metrics.length, 'Active:', metrics.filter(m => !m.isArchived).length);

  const activeMetrics = metrics.filter((m) => !m.isArchived);
  renderHomeSearchDatalist(categories, activeMetrics);
  let filteredMetrics = await filterMetricsForView('home', activeMetrics, entries, categories);
  const currentSearchTerm = ui.homeSearch ? ui.homeSearch.value.trim().toLowerCase() : homeSearchTerm;
  homeSearchTerm = currentSearchTerm;
  filteredMetrics = filterMetricsBySearch(filteredMetrics, categories, currentSearchTerm);

  const categoryMap = Object.fromEntries(categories.map((category) => [category.id, category.name]));

  ui.metricGrid.innerHTML = filteredMetrics.map((metric) => {
    const metricEntries = entries.filter((entry) => entry.metricId === metric.id);
    const sortedEntries = [...metricEntries].sort((a, b) => new Date(a.recordedAt) - new Date(b.recordedAt));
    const latest = sortedEntries[sortedEntries.length - 1];
    const categoryName = categoryMap[metric.categoryId] || 'General';

    const cleanValues = sortedEntries
      .map(e => metric.metricKind === 'strength_session' ? computeStrengthValue(e, 'Total Volume') : e.value)
      .filter(v => v !== null && v !== undefined && !Number.isNaN(v));
    const sparkValues = cleanValues.slice(-12);

    const safeCatName = categoryName.toUpperCase();
    const safeMName = metric.name.charAt(0).toUpperCase() + metric.name.slice(1);
    
    let latestLabel = '—';
    let suffix = '';
    if (latest) {
      if (metric.metricKind === 'strength_session') {
        const aggValue = computeStrengthValue(latest, activeVizSettings.strengthAgg || 'Max Load');
        latestLabel = aggValue !== null && aggValue !== undefined ? Number(aggValue).toFixed(1) : '—';
        suffix = metric.unitName ? ` ${metric.unitName}` : '';
      } else {
        latestLabel = latest.value !== null && latest.value !== undefined ? latest.value : '—';
        suffix = metric.unitName ? ` ${metric.unitName}` : '';
      }
    }

    const latestValueStr = latestLabel !== '—' ? `${latestLabel}${suffix}` : '';
    const lastDateStr = latest ? new Date(latest.recordedAt).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : '';

    let targetHtml = '';
    if (latest && latest.targetAction) {
      const colorMap = {
        'Increase': '#10b981',
        'Reduce': '#ef4444',
        'Stay': '#3b82f6',
        'Pause': '#64748b',
      };
      const tx = colorMap[latest.targetAction] || '#64748b';
      targetHtml = `<div class="overview-target" style="color: ${tx}; border-color: ${tx};">${latest.targetAction.toUpperCase()}</div>`;
    }

    const sparkSvg = renderSparkline(sparkValues, 'var(--primary)', {
      kind: metric.metricKind || metric.unitType || 'quantitative',
      higherIsBetter: metric.higherIsBetter !== false,
      rangeStart: metric.rangeStart,
      rangeEnd: metric.rangeEnd,
    });

    return `
      <div class="overview-card" data-metric-id="${metric.id}">
        <div class="overview-title-row">
          <div class="title-left">
            <span class="overview-cat">${safeCatName}</span>
            <span class="overview-name" title="${safeMName}">${safeMName}</span>
          </div>
          <div class="title-right">
            ${latestValueStr ? `<span class="metric-value">${latestValueStr}</span>` : ''}
            ${lastDateStr ? `<span class="metric-date">${lastDateStr}</span>` : ''}
          </div>
        </div>
        <div class="overview-spark-wrap">
          ${targetHtml}
          ${sparkSvg}
        </div>
        <div class="card-pills">
          <button class="card-pill" data-action="add" data-id="${metric.id}" title="Add Entry">➕</button>
          ${metric.metricKind === 'strength_session' ? `<button class="card-pill" data-action="last-session" data-id="${metric.id}" title="Last session">💡</button>` : ''}
          <button class="card-pill" data-action="stats" data-id="${metric.id}" title="View Stats">📊</button>
          <button class="card-pill" data-action="settings" data-id="${metric.id}" title="Edit Metric">⚙️</button>
          <button class="card-pill" data-action="edit-entries" data-id="${metric.id}" title="Edit Entries">📋</button>
        </div>
      </div>
    `;
  }).join('') || '<p>No metrics match this filter.</p>';
}

async function renderLogs() {
  const [events, categories] = await Promise.all([
    listChangeEvents(),
    listCategories(),
  ]);
  const catMap = Object.fromEntries(categories.map((item) => [item.id, item.name]));
  
  if (ui.changeCategory) {
    ui.changeCategory.innerHTML = '<option value="">Uncategorized</option>' + categories
      .map(c => `<option value="${c.id}">${c.name.charAt(0).toUpperCase() + c.name.slice(1)}</option>`)
      .join('');
  }

  const showArchived = ui.logShowArchived?.checked || false;
  const sortedEvents = [...events].sort((a, b) => {
    const aTime = showArchived
      ? new Date(a.endAt || a.recordedAt).getTime()
      : new Date(a.recordedAt).getTime();
    const bTime = showArchived
      ? new Date(b.endAt || b.recordedAt).getTime()
      : new Date(b.recordedAt).getTime();
    return bTime - aTime;
  });

  let filteredEvents = showArchived
    ? sortedEvents
    : sortedEvents.filter(e => !e.isArchived);

  const filter = activeFilters.log || 'Recent';
  if (filter !== 'Recent') {
    filteredEvents = filteredEvents.filter(e => {
      const catName = catMap[e.categoryId] || 'Uncategorized';
      return catName.toLowerCase() === filter.toLowerCase();
    });
  }

  if (filter === 'Recent') {
    filteredEvents = filteredEvents.slice(0, 8);
  }

  ui.changeList.innerHTML = filteredEvents.map((event) => {
    const isEditing = editingEventId === event.id;
    const isEnding = endingEventId === event.id;
    const isReviving = revivingEventId === event.id;

    const recordedDateStr = new Date(event.recordedAt).toISOString().split('T')[0];
    const recordedTimeStr = new Date(event.recordedAt).toTimeString().slice(0, 5);

    if (isEditing) {
      return `
        <div class="item edit-mode" style="padding: 12px; border: 1px solid var(--primary); border-radius: 8px; margin-bottom: 8px;">
          <strong>Edit Routine</strong>
          <form class="stacked-form" data-edit-form-id="${event.id}" style="margin-top: 8px;">
            <label>
              Category
              <select class="edit-category">
                <option value="">Uncategorized</option>
                ${categories.map(c => `<option value="${c.id}" ${c.id === event.categoryId ? 'selected' : ''}>${c.name.charAt(0).toUpperCase() + c.name.slice(1)}</option>`).join('')}
              </select>
            </label>
            <label>
              Title
              <input type="text" class="edit-title" value="${event.title}" required />
            </label>
            <label>
              Notes (Markdown supported)
              <textarea class="edit-notes" rows="4">${event.notes || ''}</textarea>
            </label>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
              <label>
                Date
                <input type="date" class="edit-date" value="${recordedDateStr}" required />
              </label>
              <label>
                Time
                <input type="time" class="edit-time" value="${recordedTimeStr}" required />
              </label>
            </div>
            <div style="display: flex; gap: 8px; margin-top: 8px;">
              <button type="submit" class="primary" style="flex: 1;">Save Changes</button>
              <button type="button" class="secondary cancel-action" style="flex: 1;">Cancel</button>
            </div>
          </form>
        </div>
      `;
    }

    if (isEnding) {
      const now = new Date();
      const nowDateStr = now.toISOString().split('T')[0];
      const nowTimeStr = now.toTimeString().slice(0, 5);
      return `
        <div class="item edit-mode" style="padding: 12px; border: 1px solid var(--primary); border-radius: 8px; margin-bottom: 8px;">
          <strong>End Routine</strong>
          <p style="font-size: 0.85rem; color: var(--muted); margin: 4px 0 8px 0;">Pick the date/time when this routine ended.</p>
          <form class="stacked-form" data-end-form-id="${event.id}">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
              <label>
                End Date
                <input type="date" class="end-date" value="${nowDateStr}" required />
              </label>
              <label>
                End Time
                <input type="time" class="end-time" value="${nowTimeStr}" required />
              </label>
            </div>
            <div style="display: flex; gap: 8px; margin-top: 8px;">
              <button type="submit" class="primary" style="flex: 1;">Confirm End Date</button>
              <button type="button" class="secondary cancel-action" style="flex: 1;">Cancel</button>
            </div>
          </form>
        </div>
      `;
    }

    if (isReviving) {
      const now = new Date();
      const nowDateStr = now.toISOString().split('T')[0];
      const nowTimeStr = now.toTimeString().slice(0, 5);
      return `
        <div class="item edit-mode" style="padding: 12px; border: 1px solid var(--primary); border-radius: 8px; margin-bottom: 8px;">
          <strong>Revive Routine</strong>
          <p style="font-size: 0.85rem; color: var(--muted); margin: 4px 0 8px 0;">Pick a new start date/time to revive this routine.</p>
          <form class="stacked-form" data-revive-form-id="${event.id}">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
              <label>
                New Start Date
                <input type="date" class="revive-date" value="${nowDateStr}" required />
              </label>
              <label>
                New Start Time
                <input type="time" class="revive-time" value="${nowTimeStr}" required />
              </label>
            </div>
            <div style="display: flex; gap: 8px; margin-top: 8px;">
              <button type="submit" class="primary" style="flex: 1;">Confirm New Start Date</button>
              <button type="button" class="secondary cancel-action" style="flex: 1;">Cancel</button>
            </div>
          </form>
        </div>
      `;
    }

    const startStr = new Date(event.recordedAt).toLocaleString(undefined, {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit'
    });
    const endStr = event.endAt ? new Date(event.endAt).toLocaleString(undefined, {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit'
    }) : null;

    const categoryLabel = catMap[event.categoryId] ? catMap[event.categoryId].charAt(0).toUpperCase() + catMap[event.categoryId].slice(1) : 'Uncategorized';
    const metadataStr = event.isArchived
      ? `Category: ${categoryLabel} | Started: ${startStr} | Ended: ${endStr}`
      : `Category: ${categoryLabel} | Started: ${startStr}`;

    const displayedTitle = event.isArchived ? `[Archived] ${event.title}` : event.title;

    return `
      <details class="routine-item" style="margin-bottom: 8px;">
        <summary style="padding: 12px 10px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); cursor: pointer; list-style: none; display: flex; justify-content: space-between; align-items: center;">
          <strong style="font-size: 1.1rem;">${displayedTitle}</strong>
          <span class="collapse-indicator">▶</span>
        </summary>
        <div class="item" style="padding: 12px; border: 1px solid var(--border); border-top: none; border-radius: 0 0 8px 8px; margin-top: -1px; background: var(--surface);">
          <div class="notes-content" style="margin-bottom: 8px; font-size: 0.95rem; line-height: 1.4;">
            ${event.notes ? renderMarkdown(event.notes) : '<span style="color: var(--muted); font-style: italic;">No notes.</span>'}
          </div>
          <div style="margin-bottom: 10px;"><small style="color: var(--muted); font-weight: 500;">${metadataStr}</small></div>
          <div style="display: flex; gap: 6px;">
          ${event.isArchived 
            ? `<button type="button" data-action="revive" data-id="${event.id}" class="primary" style="flex: 1; padding: 6px 8px; min-height: 32px; font-size: 0.85rem;">Revive</button>`
            : `<button type="button" data-action="end" data-id="${event.id}" class="primary" style="flex: 1; padding: 6px 8px; min-height: 32px; font-size: 0.85rem;">End routine</button>`
          }
          <button type="button" data-action="edit-event" data-id="${event.id}" style="flex: 1; padding: 6px 8px; min-height: 32px; font-size: 0.85rem;">Edit</button>
          <button type="button" data-action="delete-event" data-id="${event.id}" style="flex: 1; padding: 6px 8px; min-height: 32px; font-size: 0.85rem;" class="secondary">Delete</button>
        </div>
      </div>
      </details>
    `;
  }).join('') || '<p>No changes yet.</p>';
}

function getStartDateForPeriod(period, maxDate) {
  const end = maxDate ? new Date(maxDate) : new Date();
  const start = new Date(end);
  if (period === 'Week') {
    start.setDate(end.getDate() - 7);
  } else if (period === 'Month') {
    start.setMonth(end.getMonth() - 1);
  } else if (period === '6M') {
    start.setMonth(end.getMonth() - 6);
  } else if (period === 'Year') {
    start.setFullYear(end.getFullYear() - 1);
  } else {
    return new Date(0);
  }
  return start;
}

function resampleAndProcessData(entries, metric, period, zeros, strengthAgg) {
  const startDate = getStartDateForPeriod(period, new Date());
  const endDate = new Date();
  endDate.setHours(0, 0, 0, 0);
  const rows = entries
    .filter((entry) => entry.metricId === metric.id)
    .map((entry) => ({
      date: new Date(entry.recordedAt),
      entry,
    }))
    .filter((row) => !Number.isNaN(row.date.getTime()));

  const bucketMap = new Map();
  for (const { date, entry } of rows) {
    const day = new Date(date);
    day.setHours(0, 0, 0, 0);
    const key = day.toISOString();
    const value = metric.metricKind === 'strength_session'
      ? computeStrengthValue(entry, strengthAgg)
      : Number(entry.value);
    if (Number.isNaN(value)) continue;
    const existing = bucketMap.get(key);
    if (!existing || date > existing.date) {
      bucketMap.set(key, { date: new Date(day), value });
    }
  }

  const result = [];
  const cursor = new Date(startDate);
  cursor.setHours(0, 0, 0, 0);
  while (cursor <= endDate) {
    const key = cursor.toISOString();
    const bucket = bucketMap.get(key);
    if (bucket) {
      result.push({ date: bucket.date, value: bucket.value, dateStr: bucket.date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) });
    } else if (zeros) {
      result.push({ date: new Date(cursor), value: 0, dateStr: cursor.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) });
    }
    cursor.setDate(cursor.getDate() + 1);
  }
  return result;
}

function computeStrengthValue(entry, aggType) {
  const sets = entry.sets || [];
  if (!Array.isArray(sets) || sets.length === 0) {
    const baseValue = Number(entry.value ?? entry.loadKg ?? 0);
    if (aggType === 'Total Volume') {
      return baseValue * 10 * 3;
    } else if (aggType === 'Max e1RM') {
      return baseValue * (1 + 30 / 30);
    }
    return baseValue;
  }

  const setData = sets.map((s) => ({
    loadKg: Number(s.loadKg ?? s.load_kg ?? 0),
    reps: Number(s.reps ?? 10),
  }));

  if (aggType === 'Total Volume') {
    return setData.reduce((sum, s) => sum + s.loadKg * s.reps, 0);
  } else if (aggType === 'Max Load') {
    return Math.max(...setData.map((s) => s.loadKg));
  } else if (aggType === 'Average Load') {
    return setData.reduce((sum, s) => sum + s.loadKg, 0) / setData.length;
  } else if (aggType === 'Max e1RM') {
    const e1rms = setData.map((s) => s.loadKg * (1 + s.reps / 30));
    return Math.max(...e1rms);
  }
  return setData.reduce((sum, s) => sum + s.loadKg, 0);
}

function getLastStrengthSet(entry) {
  const sets = Array.isArray(entry.sets) ? entry.sets : [];
  if (sets.length > 0) {
    const lastSet = sets[sets.length - 1];
    return {
      loadKg: Number(lastSet.loadKg ?? lastSet.load_kg ?? 0),
      reps: Number(lastSet.reps ?? 0),
    };
  }
  return {
    loadKg: Number(entry.loadKg ?? entry.value ?? 0),
    reps: Number(entry.reps ?? 0),
  };
}

function roundIncrementToWeightStep(increment) {
  const steps = [0.5, 1, 1.25, 2.5, 5];
  return steps.reduce((best, step) => {
    return Math.abs(step - increment) < Math.abs(best - increment) ? step : best;
  }, steps[0]);
}

function buildStrengthProgressRecommendation(entries) {
  if (!entries || entries.length === 0) return null;
  const latest = entries[0];
  const latestSet = getLastStrengthSet(latest);

  if (latestSet.reps === 12) {
    const desiredIncrease = latestSet.loadKg * 0.05;
    const increment = roundIncrementToWeightStep(desiredIncrease);
    return `Try increasing your last set by +${increment.toFixed(2).replace(/\.00$/, '')} kg (about 5%).`;
  }

  const lastFour = entries.slice(0, 4);
  const unchangedCount = lastFour.filter((entry) => {
    const set = getLastStrengthSet(entry);
    return set.loadKg === latestSet.loadKg && set.reps === latestSet.reps;
  }).length;

  if (unchangedCount === 4) {
    return 'Your last set load and reps have been the same for 4 sessions. Try adding 2 more reps to the last set.';
  }

  return null;
}

function ensureEntriesTableMarkup() {
  const body = ui.entriesModal.querySelector('.modal-body');
  if (!body) return;
  if (!body.querySelector('#entriesTableContainer')) {
    body.innerHTML = `
      <div id="entriesTableContainer" class="table-container">
        <table id="entriesTable">
          <thead>
            <tr>
              <th>Date</th>
              <th>Value</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="entriesTableBody"></tbody>
        </table>
      </div>
    `;
  }
}

async function openStrengthSessionDetails(metricId) {
  const metrics = await listMetrics(true);
  const metric = metrics.find((m) => m.id === metricId);
  if (!metric) return;

  const entries = await listEntries();
  const metricEntries = entries
    .filter((entry) => entry.metricId === metricId)
    .sort((a, b) => new Date(b.recordedAt) - new Date(a.recordedAt));

  const body = ui.entriesModal.querySelector('.modal-body');
  if (!body) return;

  if (metricEntries.length === 0) {
    body.innerHTML = '<p>No strength sessions recorded yet for this metric.</p>';
  } else {
    const latest = metricEntries[0];
    const recommendation = buildStrengthProgressRecommendation(metricEntries);
    const sets = Array.isArray(latest.sets) ? latest.sets : [];
    const setLines = sets.length
      ? sets.map((set, index) => {
          const load = Number(set.loadKg ?? set.load_kg ?? 0).toFixed(1);
          const reps = Number(set.reps ?? 0);
          return `<li>Set ${index + 1}: ${load} kg × ${reps} reps</li>`;
        }).join('')
      : `<li>${Number(latest.loadKg ?? latest.value ?? 0).toFixed(1)} kg × ${Number(latest.reps ?? 0)} reps</li>`;
    const totalVolume = computeStrengthValue(latest, 'Total Volume');
    const maxLoad = computeStrengthValue(latest, 'Max Load');

    body.innerHTML = `
      <div class="session-detail">
        <p><strong>Last session:</strong> ${new Date(latest.recordedAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</p>
        <ul class="session-sets">${setLines}</ul>
        <p><strong>Total volume:</strong> ${Number(totalVolume).toFixed(1)} kg</p>
        <p><strong>Max load:</strong> ${Number(maxLoad).toFixed(1)} kg</p>
        <div class="recommendation">
          <strong>Recommendation</strong>
          <p>${recommendation ?? 'No progression recommendation for this session.'}</p>
        </div>
      </div>`;
  }

  ui.entriesModalTitle.textContent = `${metric.name} — Last session`;
  ui.entriesModal.classList.remove('hidden');
}

function generateSvgChart(data, metric) {
  if (data.length === 0) {
    return `<div style="text-align: center; padding: 40px; color: var(--muted, #64748b);">No data in this period.</div>`;
  }

  const width = 600;
  const height = 240;
  const padding = { top: 30, right: 20, bottom: 40, left: 50 };

  const xMax = width - padding.right;
  const xMin = padding.left;
  const yMax = height - padding.bottom;
  const yMin = padding.top;

  const values = data.map((d) => d.value);
  let minVal = Math.min(...values);
  let maxVal = Math.max(...values);

  const isScore = metric.metricKind === 'score' || metric.unitType === 'integer_range';
  if (isScore) {
    const start = metric.rangeStart ?? 1;
    const end = metric.rangeEnd ?? 5;
    minVal = Math.min(minVal, start);
    maxVal = Math.max(maxVal, end);
  } else {
    const range = maxVal - minVal;
    if (range === 0) {
      minVal = Math.max(0, minVal - 1);
      maxVal = maxVal + 1;
    } else {
      minVal = Math.max(0, minVal - range * 0.1);
      maxVal = maxVal + range * 0.1;
    }
  }

  const times = data.map((d) => d.date.getTime());
  const minTime = Math.min(...times);
  const maxTime = Math.max(...times);
  const timeRange = maxTime - minTime || 1;

  const getX = (date) => {
    return xMin + ((date.getTime() - minTime) / timeRange) * (xMax - xMin);
  };

  const getY = (val) => {
    const valRange = maxVal - minVal || 1;
    return yMax - ((val - minVal) / valRange) * (yMax - yMin);
  };

  const avgVal = values.reduce((s, v) => s + v, 0) / values.length;
  const yBaseline = getY(avgVal);

  const yTicks = 4;
  let yGridHtml = '';
  for (let i = 0; i <= yTicks; i++) {
    const ratio = i / yTicks;
    const val = minVal + ratio * (maxVal - minVal);
    const y = getY(val);
    yGridHtml += `
      <line x1="${xMin}" y1="${y}" x2="${xMax}" y2="${y}" stroke="var(--border, #cbd5e1)" stroke-dasharray="2,4" opacity="0.4" />
      <text x="${xMin - 10}" y="${y + 4}" font-size="10" fill="var(--muted, #64748b)" text-anchor="end">${val.toFixed(isScore ? 0 : 1)}</text>
    `;
  }

  const xTicksIndices = [0, Math.floor(data.length / 2), data.length - 1].filter((val, idx, self) => self.indexOf(val) === idx);
  let xGridHtml = '';
  xTicksIndices.forEach((idx) => {
    const d = data[idx];
    const x = getX(d.date);
    const dateStr = d.date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
    xGridHtml += `
      <line x1="${x}" y1="${yMin}" x2="${x}" y2="${yMax}" stroke="var(--border, #cbd5e1)" stroke-dasharray="2,4" opacity="0.4" />
      <text x="${x}" y="${yMax + 18}" font-size="10" fill="var(--muted, #64748b)" text-anchor="middle">${dateStr}</text>
    `;
  });

  let chartElements = '';
  if (isScore || metric.metricKind === 'count') {
    const barWidth = Math.max(2, Math.floor(((xMax - xMin) / data.length) * 0.7));
    chartElements = data.map((d) => {
      const x = getX(d.date) - barWidth / 2;
      const y = getY(d.value);
      const barHeight = yMax - y;
      const color = isScore ? 'var(--primary, #3b82f6)' : 'rgba(59, 130, 246, 0.8)';
      return `<rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" fill="${color}" rx="2" opacity="0.85">
        <title>${d.dateStr}: ${d.value.toFixed(1)}</title>
      </rect>`;
    }).join('');
  } else {
    let pathD = '';
    data.forEach((d, idx) => {
      const x = getX(d.date);
      const y = getY(d.value);
      if (idx === 0) {
        pathD += `M ${x} ${y}`;
      } else {
        const prev = data[idx - 1];
        const prevX = getX(prev.date);
        const prevY = getY(prev.value);
        const cpX1 = prevX + (x - prevX) / 3;
        const cpY1 = prevY;
        const cpX2 = prevX + 2 * (x - prevX) / 3;
        const cpY2 = y;
        pathD += ` C ${cpX1} ${cpY1}, ${cpX2} ${cpY2}, ${x} ${y}`;
      }
    });

    chartElements = `
      <path d="${pathD}" fill="none" stroke="var(--primary, #3b82f6)" stroke-width="3" />
      ${data.map((d) => `<circle cx="${getX(d.date)}" cy="${getY(d.value)}" r="4" fill="var(--primary, #3b82f6)" stroke="white" stroke-width="1">
        <title>${d.dateStr}: ${d.value.toFixed(1)}</title>
      </circle>`).join('')}
    `;
  }

  const unitStr = metric.unitName ? ` (${metric.unitName})` : '';

  return `
    <div style="font-size: 0.9rem; margin-bottom: 8px; display: flex; justify-content: space-between;">
      <span style="font-weight: 600; color: var(--text-color, #f8fafc);">Average: ${avgVal.toFixed(1)}${unitStr}</span>
      <span style="color: var(--muted, #64748b); font-size: 0.8rem;">${data.length} days plotted</span>
    </div>
    <svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" style="display: block; overflow: visible;">
      ${yGridHtml}
      ${xGridHtml}
      <line x1="${xMin}" y1="${yBaseline}" x2="${xMax}" y2="${yBaseline}" stroke="var(--muted, #64748b)" stroke-width="1.5" stroke-dasharray="4,4" opacity="0.6" />
      <text x="${xMax}" y="${yBaseline - 6}" font-size="9" fill="var(--muted, #64748b)" text-anchor="end" font-weight="600">Baseline (Avg): ${avgVal.toFixed(1)}</text>
      ${chartElements}
    </svg>
  `;
}

async function renderStats() {
  const [metrics, entries, categories] = await Promise.all([
    listMetrics(true),
    listEntries(),
    listCategories(),
  ]);

  const activeMetrics = metrics.filter((m) => !m.isArchived);

  const filteredMetrics = await filterMetricsForView('stats', activeMetrics, entries, categories);

  const prevSelectedValue = ui.statsMetricSelect.value;
  ui.statsMetricSelect.innerHTML = filteredMetrics
    .map((m) => `<option value="${m.id}">${m.name}</option>`)
    .join('');

  if (filteredMetrics.some((m) => m.id === prevSelectedValue)) {
    ui.statsMetricSelect.value = prevSelectedValue;
  } else {
    ui.statsMetricSelect.value = filteredMetrics[0]?.id ?? '';
  }

  const selectedMetricId = ui.statsMetricSelect.value;
  const selectedMetric = filteredMetrics.find((m) => m.id === selectedMetricId);

  if (selectedMetric) {
    ui.statsControls.classList.remove('hidden');
    ui.statsChartContainer.classList.remove('hidden');

    const isStrength = selectedMetric.metricKind === 'strength_session';
    ui.statsStrengthControl.classList.toggle('hidden', !isStrength);

    activeVizSettings.metricId = selectedMetricId;
    
    const segments = ui.statsPeriodControl.querySelectorAll('.segment');
    segments.forEach((seg) => {
      const isCurrent = seg.dataset.period === activeVizSettings.period;
      seg.classList.toggle('active', isCurrent);
      if (isCurrent) {
        seg.style.background = 'var(--primary, #3b82f6)';
        seg.style.color = 'white';
      } else {
        seg.style.background = 'transparent';
        seg.style.color = 'var(--text-color, #f8fafc)';
      }
    });

    ui.statsZerosToggle.checked = activeVizSettings.zeros;
    ui.statsStrengthSelect.value = activeVizSettings.strengthAgg;

    const processedData = resampleAndProcessData(
      entries,
      selectedMetric,
      activeVizSettings.period,
      activeVizSettings.zeros,
      activeVizSettings.strengthAgg
    );

    ui.statsChartContainer.innerHTML = generateSvgChart(processedData, selectedMetric);
  } else {
    ui.statsControls.classList.add('hidden');
    ui.statsChartContainer.classList.add('hidden');
    ui.statsChartContainer.innerHTML = '';
  }

  const summary = filteredMetrics
    .filter((metric) => metric.id === selectedMetricId)
    .map((metric) => {
      const metricEntries = entries.filter((entry) => entry.metricId === metric.id);
      const sortedEntries = [...metricEntries].sort((a, b) => new Date(a.recordedAt) - new Date(b.recordedAt));
      const latestEntry = sortedEntries[sortedEntries.length - 1];

      const values = metricEntries.map((entry) => Number(entry.value)).filter((n) => !Number.isNaN(n));
      const total = values.reduce((sum, value) => sum + value, 0);

      let latestLabel = '—';
      if (latestEntry) {
        if (metric.metricKind === 'strength_session') {
          latestLabel = formatStrengthSession(latestEntry);
        } else {
          latestLabel = latestEntry.value !== null && latestEntry.value !== undefined ? latestEntry.value : '—';
          if (latestEntry.targetAction) {
            latestLabel += ` (${latestEntry.targetAction})`;
          }
        }
      }

      const isSelected = metric.id === selectedMetricId;
      const highlightStyle = isSelected ? 'border: 1px solid var(--primary); background: rgba(59, 130, 246, 0.05);' : '';

      return `
        <div class="item" style="${highlightStyle} padding: 10px; border-radius: 8px; margin-bottom: 8px; cursor: pointer;" data-stats-metric-id="${metric.id}">
          <strong>${metric.name} ${isSelected ? '★' : ''}</strong>
          <div>${values.length} entries · total ${total.toFixed(1)} · latest ${latestLabel}</div>
        </div>
      `;
    });
  ui.statsSummary.innerHTML = summary.join('') || '<p>No stats match this filter.</p>';
}

let settingsShowCategories = false;
let isAddingCategory = false;
let isEditingCategory = false;
let selectedCategoryForEdit = null;
let categorySearchTerm = '';
let isAddingMetric = false;
let isEditingMetric = false;
let selectedMetricForEdit = null;
let metricSearchTerm = '';
let currentMetricId = null;
let suppressDetailsReset = false;
let settingsMode = 'categories';

function activateSettingsMode(mode) {
  settingsMode = mode;
  if (ui.settingsCategoriesPanel) {
    ui.settingsCategoriesPanel.classList.toggle('hidden', mode !== 'categories');
  }
  if (ui.settingsMetricsPanel) {
    ui.settingsMetricsPanel.classList.toggle('hidden', mode !== 'metrics');
  }
  if (ui.showCategoriesBtn && ui.showMetricsBtn) {
    ui.showCategoriesBtn.classList.toggle('active', mode === 'categories');
    ui.showMetricsBtn.classList.toggle('active', mode === 'metrics');
  }
}

if (ui.showCategoriesBtn) {
  ui.showCategoriesBtn.addEventListener('click', async () => {
    activateSettingsMode('categories');
    renderSettings();
  });
}

if (ui.showMetricsBtn) {
  ui.showMetricsBtn.addEventListener('click', async () => {
    activateSettingsMode('metrics');
    renderSettings();
  });
}

async function renderSettings() {
  activateSettingsMode(settingsMode);
  const [categories, metrics] = await Promise.all([
    listCategories(),
    listMetrics(true),
  ]);

  // Reset UI states
  ui.categoryForm.style.display = isAddingCategory ? 'grid' : 'none';
  ui.categoryEditForm.style.display = isEditingCategory ? 'grid' : 'none';
  ui.categoryEditFields.style.display = isEditingCategory && selectedCategoryForEdit ? 'block' : 'none';

  if (isEditingCategory && selectedCategoryForEdit) {
    const selectedCat = categories.find(c => c.id === selectedCategoryForEdit);
    if (selectedCat) {
      ui.editCategoryName.value = selectedCat.name || '';
      ui.editCategoryDescription.value = selectedCat.description || '';
    }
  }

  await updateDeleteCategoryButtonState(categories);
  renderCategorySearchDatalist(categories);

  // Only show category cards when searching (categorySearchTerm is set) but not when editing a specific category
  if (categorySearchTerm && !selectedCategoryForEdit) {
    // Filter categories based on search term
    const filteredCategories = categories.filter(category => 
      category.name.toLowerCase().includes(categorySearchTerm)
    );

    if (filteredCategories.length > 0) {
      ui.categoryList.innerHTML = filteredCategories.map((category) => `
        <div class="item">
          <strong>${category.name}</strong>
          ${category.description ? `<div style="opacity: 0.7;">${category.description}</div>` : ''}
          <div>
            <button data-action="rename-category" data-id="${category.id}" class="secondary">Rename</button>
            <button data-action="delete-category" data-id="${category.id}" class="secondary">Delete</button>
          </div>
        </div>
      `).join('');
    } else {
      ui.categoryList.innerHTML = '<p class="muted-text" style="padding: 1rem; text-align: center; opacity: 0.6;">No matching categories found</p>';
    }
  } else {
    ui.categoryList.innerHTML = '';
  }
  
  // Always show categories if there are any
  settingsShowCategories = categories.length > 0;

  // Reset UI states for metrics
  ui.metricForm.style.display = isAddingMetric ? 'grid' : 'none';
  ui.metricEditForm.style.display = isEditingMetric ? 'grid' : 'none';
  ui.metricEditFields.style.display = isEditingMetric && selectedMetricForEdit ? 'block' : 'none';

  if (isEditingMetric && selectedMetricForEdit) {
    const selectedMetric = metrics.find(m => m.id === selectedMetricForEdit);
    if (selectedMetric) {
      ui.editMetricName.value = selectedMetric.name || '';
      ui.editMetricDescription.value = selectedMetric.description || '';
      // Set archive button text based on current state
      ui.archiveMetricEdit.textContent = selectedMetric.isArchived ? 'Unarchive' : 'Archive';
    }
  }

  renderMetricSearchDatalist(metrics);

  // Don't show metric cards when searching - only show edit fields when there's an exact match
  ui.metricList.innerHTML = '';
  
  ui.metricCategory.innerHTML = categories.map((category) => `<option value="${category.id}">${category.name}</option>`).join('');
}

ui.tabs.forEach((tab) => {
  tab.addEventListener('click', async () => {
    ui.tabs.forEach((item) => item.classList.remove('active'));
    ui.views.forEach((view) => view.classList.remove('active'));
    tab.classList.add('active');
    const newActiveView = document.querySelector(`#view-${tab.dataset.view}`);
    newActiveView.classList.add('active');
    // Reset all collapsible panels in the new view
    suppressDetailsReset = true;
    newActiveView.querySelectorAll('details').forEach((d) => {
      d.removeAttribute('open');
    });
    suppressDetailsReset = false;
    // Initialize Add form if switching to Add tab
    if (tab.dataset.view === 'add') {
      await renderMetricDropdown();
      await syncAddFormMode();
      // Restore current metric selection if available
      if (currentMetricId) {
        ui.metricSelect.value = currentMetricId;
        syncAddFormMode();
      }
    }
    // Render Stats when switching to Stats tab
    if (tab.dataset.view === 'stats') {
      await renderStats();
      // Restore current metric selection if available
      if (currentMetricId) {
        ui.statsMetricSelect.value = currentMetricId;
        activeVizSettings.metricId = currentMetricId;
        renderStats();
      }
    }
    if (tab.dataset.view === 'settings') {
      activateSettingsMode(settingsMode);
      await renderSettings();
    }
    // Render Home when switching to Home tab
    if (tab.dataset.view === 'home') {
      await renderHome();
      // Store current metric selection from stats if available
      if (ui.statsMetricSelect.value) {
        currentMetricId = ui.statsMetricSelect.value;
      }
    }
  });
});

// Auto-close other collapsible panels when one is opened
document.querySelectorAll('details').forEach((detail) => {
  detail.addEventListener('toggle', (event) => {
    if (event.newState === 'open') {
      // Close all other details in the same view
      const view = detail.closest('.view');
      if (view) {
        view.querySelectorAll('details').forEach((d) => {
          if (d !== detail) {
            d.removeAttribute('open');
          }
        });
      }
    }
  });
});

// Back button handler
document.querySelectorAll('.back-button').forEach((btn) => {
  btn.addEventListener('click', () => {
    const homeTab = document.querySelector('.tab[data-view="home"]');
    if (homeTab) homeTab.click();
  });
});

ui.metricSelect.addEventListener('change', () => {
  currentMetricId = ui.metricSelect.value;
  syncAddFormMode();
});

if (ui.homeSearch) {
  ui.homeSearch.addEventListener('input', () => {
    homeSearchTerm = ui.homeSearch.value.trim().toLowerCase();
    renderHome();
  });
}

ui.statsMetricSelect.addEventListener('change', () => {
  currentMetricId = ui.statsMetricSelect.value;
});

ui.strengthAddSetButton.addEventListener('click', () => {
  const loadKg = Number(ui.strengthLoadInput.value);
  const reps = Number(ui.strengthRepsInput.value);
  if (!Number.isFinite(loadKg) || !Number.isFinite(reps) || reps < 1) {
    return;
  }

  strengthSets.push({ loadKg, reps: Math.round(reps) });
  renderStrengthSetList();
  ui.strengthLoadInput.value = loadKg;
  ui.strengthRepsInput.value = 5;
});

ui.strengthSetList.addEventListener('click', async (event) => {
  const removeButton = event.target.closest('[data-remove-set]');
  if (removeButton) {
    const index = Number(removeButton.dataset.removeSet);
    strengthSets.splice(index, 1);
    if (editingSetIndex === index) {
      editingSetIndex = null;
    } else if (editingSetIndex > index) {
      editingSetIndex -= 1;
    }
    renderStrengthSetList();
    return;
  }

  const editButton = event.target.closest('[data-edit-set]');
  if (editButton) {
    editingSetIndex = Number(editButton.dataset.editSet);
    renderStrengthSetList();
    return;
  }

  if (event.target.id === 'saveEditSetButton') {
    const editLoad = Number(document.querySelector('#editSetLoad').value);
    const editReps = Number(document.querySelector('#editSetReps').value);
    if (Number.isFinite(editLoad) && Number.isFinite(editReps) && editReps >= 1) {
      strengthSets[editingSetIndex] = { loadKg: editLoad, reps: Math.round(editReps) };
    }
    editingSetIndex = null;
    renderStrengthSetList();
    return;
  }

  if (event.target.id === 'cancelEditSetButton') {
    editingSetIndex = null;
    renderStrengthSetList();
    return;
  }
});

ui.entryForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const metricId = ui.metricSelect.value;
    if (!metricId) {
      window.alert('Please select a metric.');
      return;
    }

    const metrics = await listMetrics(false);
    const metric = metrics.find((item) => item.id === metricId) || null;
    const dateValue = ui.entryDate?.value;
    const timeValue = ui.entryTime?.value;
    const valueInput = ui.entryValue;
    
    if (metric?.metricKind !== 'strength_session' && !valueInput?.value) {
      window.alert('Please enter a value.');
      return;
    }
    if (!dateValue || !timeValue) {
      window.alert(`Date: "${dateValue}", Time: "${timeValue}"`);
      return;
    }
  const recordedAt = new Date(`${dateValue}T${timeValue}`).toISOString();

  // Get target action from active pill
  const activeTargetPill = ui.targetActionPills?.querySelector('.pill.active');
  const targetAction = activeTargetPill ? (activeTargetPill.dataset.target === 'None' ? null : activeTargetPill.dataset.target) : null;

  if (editingEntryId) {
    // Update existing entry
    const entry = (await listEntries()).find(e => e.id === editingEntryId);
    if (entry) {
      if (metric?.metricKind === 'strength_session') {
        if (!strengthSets.length) {
          window.alert('Add at least one set before saving the workout.');
          return;
        }
        const summaryLoad = strengthSets[0].loadKg;
        await updateEntry(editingEntryId, {
          metricId,
          value: summaryLoad,
          loadKg: summaryLoad,
          sets: strengthSets,
          targetAction,
          recordedAt,
        });
      } else {
        await updateEntry(editingEntryId, {
          metricId,
          value: Number(valueInput.value),
          targetAction,
          recordedAt,
        });
      }
      editingEntryId = null;
      // Refresh entries table if visible
      const modal = ui.entriesModal;
      if (modal && !modal.classList.contains('hidden')) {
        const metricId = ui.metricSelect.value;
        const metrics = await listMetrics(true);
        const metric = metrics.find(m => m.id === metricId);
        if (metricId && metric) {
          await renderEntriesTable(metricId, metric);
        }
      }
    }
  } else {
    // Create new entry
    if (metric?.metricKind === 'strength_session') {
      if (!strengthSets.length) {
        window.alert('Add at least one set before saving the workout.');
        return;
      }

      const summaryLoad = strengthSets[0].loadKg;
      await createEntry({
        metricId,
        value: summaryLoad,
        loadKg: summaryLoad,
        sets: strengthSets,
        targetAction,
        recordedAt,
      });
    } else {
      await createEntry({
        metricId,
        value: Number(valueInput.value),
        targetAction,
        recordedAt,
      });
    }
  }
  } catch (e) {
    console.error('Form submission error:', e);
    window.alert('Error: ' + e.message);
  }

  window.alert('Entry saved!');
  strengthSets = [];
  editingSetIndex = null;
  ui.entryForm.reset();
  resetEntryFormDateTime();
  incrementUnsavedCount();
  renderAll();
});

ui.categoryForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const name = ui.categoryName.value.trim();
  if (!name) return;
  
  // Check for duplicate category names
  const categories = await listCategories();
  const duplicate = categories.some(cat => cat.name.toLowerCase() === name.toLowerCase());
  if (duplicate) {
    window.alert('A category with this name already exists.');
    return;
  }
  
  const description = ui.categoryDescriptionAdd.value.trim();
  await createCategory(name, description);
  isAddingCategory = false;
  ui.categoryForm.reset();
  ui.categoryForm.style.display = 'none';
  
  // Clear active button states
  ui.addCategoryBtn.classList.remove('active');
  
  incrementUnsavedCount();
  renderAll();
});

// Add category button
ui.addCategoryBtn.addEventListener('click', () => {
  isAddingCategory = true;
  isEditingCategory = false;
  selectedCategoryForEdit = null;
  categorySearchTerm = '';
  ui.categoryName.value = '';
  ui.categoryForm.style.display = 'grid';
  ui.categoryEditForm.style.display = 'none';
  
  // Update active button states
  ui.addCategoryBtn.classList.add('active');
  ui.editCategoryBtn.classList.remove('active');
});

// Edit category button
ui.editCategoryBtn.addEventListener('click', () => {
  isAddingCategory = false;
  isEditingCategory = true;
  selectedCategoryForEdit = null;
  categorySearchTerm = '';
  ui.categorySearch.value = '';
  ui.categoryEditFields.style.display = 'none';
  ui.categoryEditForm.style.display = 'grid';
  ui.categoryForm.style.display = 'none';
  renderAll(); // Reset the category list filtering
  
  // Update active button states
  ui.addCategoryBtn.classList.remove('active');
  ui.editCategoryBtn.classList.add('active');
});

// Category search with autocomplete and filtering
ui.categorySearch.addEventListener('input', async () => {
  categorySearchTerm = ui.categorySearch.value.trim().toLowerCase();
  selectedCategoryForEdit = null;
  await updateDeleteCategoryButtonState();
  renderSettings();
});

ui.categorySearch.addEventListener('change', async () => {
  categorySearchTerm = ui.categorySearch.value.trim().toLowerCase();
  const categories = await listCategories();
  const exactMatch = categories.find(cat => cat.name.toLowerCase() === categorySearchTerm);
  if (exactMatch) {
    isAddingCategory = false;
    isEditingCategory = true;
    selectedCategoryForEdit = exactMatch.id;
    ui.categoryEditForm.style.display = 'grid';
    ui.categoryEditFields.style.display = 'block';
    ui.addCategoryBtn.classList.remove('active');
    ui.editCategoryBtn.classList.add('active');
    ui.editCategoryName.value = exactMatch.name || '';
    ui.editCategoryDescription.value = exactMatch.description || '';
    await updateDeleteCategoryButtonState(categories);
    renderSettings();
    return;
  }
  isAddingCategory = false;
  isEditingCategory = false;
  selectedCategoryForEdit = null;
  await updateDeleteCategoryButtonState(categories);
  renderSettings();
});

// Save category edit
ui.saveCategoryEdit.addEventListener('click', async () => {
  if (!selectedCategoryForEdit) return;
  
  const name = ui.editCategoryName.value.trim();
  if (!name) return;
  
  // Check for duplicate category names (excluding the current category being edited)
  const categories = await listCategories();
  const duplicate = categories.some(cat => 
    cat.id !== selectedCategoryForEdit && cat.name.toLowerCase() === name.toLowerCase()
  );
  if (duplicate) {
    window.alert('A category with this name already exists.');
    return;
  }
  
  const updates = { name: name.toLowerCase() };
  const description = ui.editCategoryDescription.value.trim();
  if (description) {
    updates.description = description;
  }
  
  await updateCategory(selectedCategoryForEdit, updates);
  isEditingCategory = false;
  selectedCategoryForEdit = null;
  categorySearchTerm = '';
  ui.categorySearch.value = '';
  ui.categoryEditForm.style.display = 'none';
  
  // Clear active button states
  ui.addCategoryBtn.classList.remove('active');
  ui.editCategoryBtn.classList.remove('active');
  
  incrementUnsavedCount();
  renderAll();
});

// Cancel category edit
ui.cancelCategoryEdit.addEventListener('click', () => {
  isEditingCategory = false;
  selectedCategoryForEdit = null;
  categorySearchTerm = '';
  ui.categorySearch.value = '';
  ui.categoryEditForm.style.display = 'none';
  ui.categoryEditFields.style.display = 'none';
  
  // Clear active button states
  ui.addCategoryBtn.classList.remove('active');
  ui.editCategoryBtn.classList.remove('active');
  
  renderAll();
});

// Cancel category add
ui.cancelCategory.addEventListener('click', () => {
  isAddingCategory = false;
  ui.categoryForm.style.display = 'none';
  ui.categoryForm.reset();
  
  // Clear active button states
  ui.addCategoryBtn.classList.remove('active');
  ui.editCategoryBtn.classList.remove('active');
  
  renderAll();
});

// Add metric button
ui.addMetricBtn.addEventListener('click', () => {
  isAddingMetric = true;
  isEditingMetric = false;
  selectedMetricForEdit = null;
  metricSearchTerm = '';
  ui.metricName.value = '';
  ui.metricUnit.value = '';
  ui.metricDescription.value = '';
  ui.metricForm.style.display = 'grid';
  ui.metricEditForm.style.display = 'none';
  
  // Update active button states
  ui.addMetricBtn.classList.add('active');
  ui.editMetricBtn.classList.remove('active');
});

// Edit metric button
ui.editMetricBtn.addEventListener('click', () => {
  isAddingMetric = false;
  isEditingMetric = true;
  selectedMetricForEdit = null;
  metricSearchTerm = '';
  ui.metricSearch.value = '';
  ui.metricEditFields.style.display = 'none';
  ui.metricEditForm.style.display = 'grid';
  ui.metricForm.style.display = 'none';
  renderAll(); // Reset the metric list filtering
  
  // Update active button states
  ui.addMetricBtn.classList.remove('active');
  ui.editMetricBtn.classList.add('active');
});

// Metric search (native datalist)
ui.metricSearch.addEventListener('input', async () => {
  metricSearchTerm = ui.metricSearch.value.trim().toLowerCase();
  selectedMetricForEdit = null;
  renderSettings();
});

ui.metricSearch.addEventListener('change', async () => {
  metricSearchTerm = ui.metricSearch.value.trim().toLowerCase();
  const metrics = await listMetrics(true);
  const exactMatch = metrics.find(metric => metric.name.toLowerCase() === metricSearchTerm);
  if (exactMatch) {
    isAddingMetric = false;
    isEditingMetric = true;
    selectedMetricForEdit = exactMatch.id;
    ui.metricEditForm.style.display = 'grid';
    ui.metricEditFields.style.display = 'block';
    ui.addMetricBtn.classList.remove('active');
    ui.editMetricBtn.classList.add('active');
    ui.editMetricName.value = exactMatch.name || '';
    ui.editMetricDescription.value = exactMatch.description || '';
    renderSettings();
    return;
  }
  isAddingMetric = false;
  isEditingMetric = false;
  selectedMetricForEdit = null;
  renderSettings();
});


// Save metric edit
ui.saveMetricEdit.addEventListener('click', async () => {
  if (!selectedMetricForEdit) return;
  
  const name = ui.editMetricName.value.trim();
  if (!name) return;
  
  // Check for duplicate metric names (excluding the current metric being edited)
  const metrics = await listMetrics(true);
  const duplicate = metrics.some(metric => 
    metric.id !== selectedMetricForEdit && metric.name.toLowerCase() === name.toLowerCase()
  );
  if (duplicate) {
    window.alert('A metric with this name already exists.');
    return;
  }
  
  const updates = { name: name.toLowerCase() };
  const description = ui.editMetricDescription.value.trim();
  if (description) {
    updates.description = description;
  }
  
  await updateMetric(selectedMetricForEdit, updates);
  isEditingMetric = false;
  selectedMetricForEdit = null;
  metricSearchTerm = '';
  ui.metricSearch.value = '';
  ui.metricEditForm.style.display = 'none';
  
  // Clear active button states
  ui.addMetricBtn.classList.remove('active');
  ui.editMetricBtn.classList.remove('active');
  
  incrementUnsavedCount();
  renderAll();
});

// Cancel metric edit
ui.cancelMetricEdit.addEventListener('click', () => {
  isEditingMetric = false;
  selectedMetricForEdit = null;
  metricSearchTerm = '';
  ui.metricSearch.value = '';
  ui.metricEditForm.style.display = 'none';
  ui.metricEditFields.style.display = 'none';
  
  // Clear active button states
  ui.addMetricBtn.classList.remove('active');
  ui.editMetricBtn.classList.remove('active');
  
  renderAll();
});

// Archive metric from edit view
ui.archiveMetricEdit.addEventListener('click', async () => {
  if (!selectedMetricForEdit) return;
  
  const metrics = await listMetrics(true);
  const metric = metrics.find(m => m.id === selectedMetricForEdit);
  if (!metric) return;
  
  // Toggle archive state
  const newArchiveState = !metric.isArchived;
  await updateMetric(selectedMetricForEdit, { isArchived: newArchiveState });
  
  // Update the button text based on new state
  ui.archiveMetricEdit.textContent = newArchiveState ? 'Unarchive' : 'Archive';
  
  incrementUnsavedCount();
  renderAll();
});

// Cancel metric add
ui.cancelMetric.addEventListener('click', () => {
  isAddingMetric = false;
  ui.metricForm.style.display = 'none';
  ui.metricForm.reset();
  
  // Clear active button states
  ui.addMetricBtn.classList.remove('active');
  ui.editMetricBtn.classList.remove('active');
  
  renderAll();
});

ui.metricForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const categoryId = ui.metricCategory.value;
  const name = ui.metricName.value.trim();
  if (!name) return;
  
  // Check for duplicate metric names
  const metrics = await listMetrics(true);
  const duplicate = metrics.some(metric => metric.name.toLowerCase() === name.toLowerCase());
  if (duplicate) {
    window.alert('A metric with this name already exists.');
    return;
  }
  
  const description = ui.metricDescription.value.trim();
  await createMetric({
    name: name,
    description: description || null,
    categoryId,
    unitName: ui.metricUnit.value.trim() || null,
    unitType: ui.metricType.value,
    metricKind: ui.metricKind.value,
    higherIsBetter: true,
    isArchived: false,
  });
  isAddingMetric = false;
  ui.metricForm.reset();
  ui.metricForm.style.display = 'none';
  
  // Clear active button states
  ui.addMetricBtn.classList.remove('active');
  
  incrementUnsavedCount();
  renderAll();
});

ui.changeForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const catId = ui.changeCategory.value || null;
  const dateVal = ui.changeDate.value;
  const timeVal = ui.changeTime.value;
  const recordedAt = new Date(`${dateVal}T${timeVal}`).toISOString();

  await createChangeEvent({
    title: document.querySelector('#changeTitle').value.trim(),
    notes: document.querySelector('#changeNotes').value.trim() || null,
    recordedAt,
    endAt: null,
    isArchived: false,
    categoryId: catId,
  });
  ui.changeForm.reset();
  resetChangeFormDateTime();
  incrementUnsavedCount();
  renderAll();
});

ui.changeList.addEventListener('click', async (event) => {
  const btn = event.target.closest('[data-action]');
  if (btn) {
    const action = btn.dataset.action;
    const eventId = btn.dataset.id;
    if (action === 'edit-event') {
      editingEventId = eventId;
      endingEventId = null;
      revivingEventId = null;
      renderLogs();
    } else if (action === 'end') {
      endingEventId = eventId;
      editingEventId = null;
      revivingEventId = null;
      renderLogs();
    } else if (action === 'revive') {
      revivingEventId = eventId;
      editingEventId = null;
      endingEventId = null;
      renderLogs();
    } else if (action === 'delete-event') {
      if (window.confirm('Delete this routine?')) {
        await deleteChangeEvent(eventId);
        incrementUnsavedCount();
        renderAll();
      }
    }
    return;
  }

  const cancelBtn = event.target.closest('.cancel-action');
  if (cancelBtn) {
    editingEventId = null;
    endingEventId = null;
    revivingEventId = null;
    renderLogs();
    return;
  }
});

// Mutually exclusive collapse for routine items in Existing Routines
// Handle click on summary elements to collapse others first
ui.changeList.addEventListener('click', (event) => {
  const summary = event.target.closest('details.routine-item summary');
  if (summary) {
    const details = summary.parentElement;
    const allRoutineItems = ui.changeList.querySelectorAll('details.routine-item');
    
    // Close all other routine items first
    allRoutineItems.forEach(item => {
      if (item !== details) {
        item.removeAttribute('open');
      }
    });
  }
});

ui.changeList.addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  if (form.hasAttribute('data-edit-form-id')) {
    const eventId = form.getAttribute('data-edit-form-id');
    const title = form.querySelector('.edit-title').value.trim();
    const notes = form.querySelector('.edit-notes').value.trim();
    const catId = form.querySelector('.edit-category').value || null;
    const dateVal = form.querySelector('.edit-date').value;
    const timeVal = form.querySelector('.edit-time').value;
    const recordedAt = new Date(`${dateVal}T${timeVal}`).toISOString();

    await updateChangeEvent(eventId, {
      title,
      notes: notes || null,
      categoryId: catId,
      recordedAt,
    });
    editingEventId = null;
    incrementUnsavedCount();
    renderAll();
  } else if (form.hasAttribute('data-end-form-id')) {
    const eventId = form.getAttribute('data-end-form-id');
    const dateVal = form.querySelector('.end-date').value;
    const timeVal = form.querySelector('.end-time').value;
    const endAt = new Date(`${dateVal}T${timeVal}`).toISOString();

    await updateChangeEvent(eventId, {
      endAt,
      isArchived: true,
    });
    endingEventId = null;
    incrementUnsavedCount();
    renderAll();
  } else if (form.hasAttribute('data-revive-form-id')) {
    const eventId = form.getAttribute('data-revive-form-id');
    const dateVal = form.querySelector('.revive-date').value;
    const timeVal = form.querySelector('.revive-time').value;
    const recordedAt = new Date(`${dateVal}T${timeVal}`).toISOString();

    await updateChangeEvent(eventId, {
      recordedAt,
      endAt: null,
      isArchived: false,
    });
    revivingEventId = null;
    incrementUnsavedCount();
    renderAll();
  }
});

if (ui.logShowArchived) {
  ui.logShowArchived.addEventListener('change', () => {
    activeFilters.log = 'Recent';
    renderLogs();
  });
}


ui.metricList.addEventListener('click', async (event) => {
  const actionButton = event.target.closest('[data-action]');
  if (actionButton) {
    const metricId = actionButton.dataset.id;
    if (actionButton.dataset.action === 'rename-metric') {
      isEditingMetric = true;
      selectedMetricForEdit = metricId;
      ui.metricEditForm.style.display = 'grid';
      ui.metricEditFields.style.display = 'block';
      ui.addMetricBtn.classList.remove('active');
      ui.editMetricBtn.classList.add('active');
      const metrics = await listMetrics(true);
      const selectedMetric = metrics.find((m) => m.id === metricId);
      if (selectedMetric) {
        ui.editMetricName.value = selectedMetric.name || '';
        ui.editMetricDescription.value = selectedMetric.description || '';
      }
      return;
    }
    if (actionButton.dataset.action === 'archive-metric') {
      const metrics = await listMetrics(true);
      const metric = metrics.find((m) => m.id === metricId);
      if (metric) {
        await updateMetric(metricId, { isArchived: !metric.isArchived });
      }
      metricSearchTerm = '';
      renderAll();
      return;
    }
  }

  const item = event.target.closest('.item[data-metric-id]');
  if (item) {
    isEditingMetric = true;
    selectedMetricForEdit = item.dataset.metricId;
    ui.metricEditForm.style.display = 'grid';
    ui.metricEditFields.style.display = 'block';
    ui.addMetricBtn.classList.remove('active');
    ui.editMetricBtn.classList.add('active');
    const metrics = await listMetrics(true);
    const selectedMetric = metrics.find((m) => m.id === selectedMetricForEdit);
    if (selectedMetric) {
      ui.editMetricName.value = selectedMetric.name || '';
      ui.editMetricDescription.value = selectedMetric.description || '';
    }
  }
});

// Reset states when collapsing sections
function setupCollapsibleReset(detailsElement, resetFunction) {
  if (detailsElement) {
    detailsElement.addEventListener('toggle', async function() {
      if (!this.open && !suppressDetailsReset) {
        await resetFunction();
      }
    });
  }
}

// For categories section - find the details element that contains categoryList
const allDetails = document.querySelectorAll('details');
allDetails.forEach(details => {
  if (details.querySelector('#categoryList')) {
    setupCollapsibleReset(details, () => {
      isAddingCategory = false;
      isEditingCategory = false;
      selectedCategoryForEdit = null;
      categorySearchTerm = '';
      ui.categoryName.value = '';
      ui.categorySearch.value = '';
      ui.categoryForm.style.display = 'none';
      ui.categoryEditForm.style.display = 'none';
      ui.categoryEditFields.style.display = 'none';
      ui.addCategoryBtn.classList.remove('active');
      ui.editCategoryBtn.classList.remove('active');
      renderAll();
    });
  }
  
  if (details.querySelector('#metricList')) {
    setupCollapsibleReset(details, () => {
      isAddingMetric = false;
      isEditingMetric = false;
      selectedMetricForEdit = null;
      metricSearchTerm = '';
      ui.metricName.value = '';
      ui.metricSearch.value = '';
      ui.metricForm.style.display = 'none';
      ui.metricEditForm.style.display = 'none';
      ui.metricEditFields.style.display = 'none';
      ui.addMetricBtn.classList.remove('active');
      ui.editMetricBtn.classList.remove('active');
      renderAll();
    });
  }
});

ui.categoryList.addEventListener('click', async (event) => {
  const actionButton = event.target.closest('[data-action]');
  if (actionButton) {
    const categoryId = actionButton.dataset.id;
    if (actionButton.dataset.action === 'rename-category') {
      isEditingCategory = true;
      selectedCategoryForEdit = categoryId;
      ui.categoryEditForm.style.display = 'grid';
      ui.categoryEditFields.style.display = 'block';
      const categories = await listCategories();
      const selectedCat = categories.find((c) => c.id === categoryId);
      if (selectedCat) {
        ui.editCategoryName.value = selectedCat.name || '';
        ui.editCategoryDescription.value = selectedCat.description || '';
      }
      ui.addCategoryBtn.classList.remove('active');
      ui.editCategoryBtn.classList.add('active');
      return;
    }
    if (actionButton.dataset.action === 'delete-category') {
      await confirmAndDeleteCategory(categoryId);
      return;
    }
  }

  const item = event.target.closest('.item[data-category-id]');
  if (item) {
    isEditingCategory = true;
    selectedCategoryForEdit = item.dataset.categoryId;
    ui.categoryEditForm.style.display = 'grid';
    ui.categoryEditFields.style.display = 'block';
    ui.addCategoryBtn.classList.remove('active');
    ui.editCategoryBtn.classList.add('active');
    const categories = await listCategories();
    const selectedCat = categories.find((c) => c.id === selectedCategoryForEdit);
    if (selectedCat) {
      ui.editCategoryName.value = selectedCat.name || '';
      ui.editCategoryDescription.value = selectedCat.description || '';
    }
  }
});

ui.deleteCategoryBtn.addEventListener('click', async () => {
  const categoryName = ui.categoryName.value.trim() || ui.categorySearch.value.trim();
  const categories = await listCategories();
  const exactMatch = categories.find((c) => c.name.toLowerCase() === categoryName.toLowerCase());
  if (exactMatch) {
    await confirmAndDeleteCategory(exactMatch.id);
  } else {
    window.alert('Type the exact category name to delete it.');
  }
});

async function updateDeleteCategoryButtonState(categories = null) {
  if (!ui.deleteCategoryBtn) return;
  const exactMatch = await findExactCategoryMatch(categories);
  ui.deleteCategoryBtn.disabled = !exactMatch;
}

async function findExactCategoryMatch(categories = null) {
  const allCategories = categories || await listCategories();
  const typedName = ui.categorySearch.value.trim();
  if (!typedName) return null;
  return allCategories.find((c) => c.name.toLowerCase() === typedName.toLowerCase()) || null;
}

function renderCategorySearchDatalist(categories) {
  if (!ui.categorySearchDatalist) return;
  ui.categorySearchDatalist.innerHTML = categories
    .map((category) => `<option value="${category.name}"></option>`) 
    .join('');
}

function renderMetricSearchDatalist(metrics) {
  if (!ui.metricSearchDatalist) return;
  ui.metricSearchDatalist.innerHTML = metrics
    .map((metric) => `<option value="${metric.name}"></option>`) 
    .join('');
}

function renderHomeSearchDatalist(categories, metrics) {
  if (!ui.homeSearchDatalist) return;
  const options = [
    ...new Set([
      ...categories.map((category) => category.name),
      ...metrics.map((metric) => metric.name),
    ]),
  ].sort((a, b) => a.localeCompare(b));

  ui.homeSearchDatalist.innerHTML = options
    .map((value) => `<option value="${value}"></option>`)
    .join('');
}

async function confirmAndDeleteCategory(categoryId) {
  const categories = await listCategories();
  const category = categories.find((cat) => cat.id === categoryId);
  if (!category) {
    window.alert('Category not found.');
    return;
  }

  const metrics = await listMetrics(true);
  const impactedMetrics = metrics.filter((metric) => metric.categoryId === categoryId);
  const impactedNames = impactedMetrics.map((metric) => metric.name).join(', ');
  const metricMessage = impactedMetrics.length
    ? `This will remove the category from ${impactedMetrics.length} metric(s): ${impactedNames}.`
    : 'No metrics currently use this category.';

  const confirmed = window.confirm(
    `Delete category "${category.name}"? ${metricMessage}\n\nThis action will remove the category from affected metrics.`
  );
  if (!confirmed) return;

  for (const metric of impactedMetrics) {
    await updateMetric(metric.id, { categoryId: null });
  }
  await deleteCategory(categoryId);
  ui.categoryName.value = '';
  ui.categorySearch.value = '';
  ui.categoryForm.style.display = 'none';
  ui.categoryEditForm.style.display = 'none';
  ui.categoryEditFields.style.display = 'none';
  isAddingCategory = false;
  isEditingCategory = false;
  selectedCategoryForEdit = null;
  categorySearchTerm = '';
  renderAll();
}

async function triggerCsvExport() {
  const csv = await exportDataAsCsv();
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'quantifi-pwa-export.csv';
  link.click();
  URL.revokeObjectURL(url);
  resetUnsavedCount();
}

ui.exportButton.addEventListener('click', async () => {
  await triggerCsvExport();
});

ui.importButton.addEventListener('click', () => {
  ui.importFile.click();
});

ui.importFile.addEventListener('change', async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  const text = await file.text();
  const summary = await importCsvText(text);
  resetUnsavedCount();
  await renderAll();
  alert(`Import complete. ${summary.entries} entries imported, ${summary.changes} changes, ${summary.metrics} new metrics created. Matching metrics were reused where possible.`);

  const statsTab = document.querySelector('.tab[data-view="stats"]');
  if (statsTab) {
    statsTab.click();
  }
});

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch((error) => console.warn(error));
  });
}

window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  deferredPrompt = event;
  ui.installButton.classList.remove('hidden');
});

ui.installButton.addEventListener('click', async () => {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  await deferredPrompt.userChoice;
  deferredPrompt = null;
  ui.installButton.classList.add('hidden');
});


// Date pills handler
if (ui.entryDatePills) {
  ui.entryDatePills.addEventListener('click', (event) => {
    const pill = event.target.closest('.pill');
    if (!pill) return;
    
    // Update active state
    ui.entryDatePills.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    
    // Show/hide dateTimeFields
    if (pill.dataset.date === 'Custom') {
      ui.dateTimeFields.classList.remove('hidden');
    } else {
      ui.dateTimeFields.classList.add('hidden');
      // Set default date/time based on selection
      const now = new Date();
      if (pill.dataset.date === 'Yesterday') {
        const yesterday = new Date(now);
        yesterday.setDate(yesterday.getDate() - 1);
        ui.entryDate.value = yesterday.toISOString().split('T')[0];
        ui.entryTime.value = '12:00';
      } else {
        ui.entryDate.value = now.toISOString().split('T')[0];
        ui.entryTime.value = now.toTimeString().slice(0, 5);
      }
    }
  });
}

// Target action pills handler
if (ui.targetActionPills) {
  ui.targetActionPills.addEventListener('click', (event) => {
    const pill = event.target.closest('.pill');
    if (!pill) return;
    
    // Update active state
    ui.targetActionPills.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    
    // Store selected target in dataset or hidden input
    // We'll read this value when form is submitted
  });
}


ui.metricGrid.addEventListener('click', async (event) => {
  const btn = event.target.closest('.card-pill');
  if (btn) {
    event.stopPropagation();
    const action = btn.dataset.action;
    const metricId = btn.dataset.id;
    if (action === 'add') {
      activeFilters.add = 'Recent';
      currentMetricId = metricId; // Store the current metric
      await renderMetricDropdown();
      ui.metricSelect.value = metricId;
      await syncAddFormMode();
      const addTab = document.querySelector('.tab[data-view="add"]');
      if (addTab) addTab.click();
    } else if (action === 'stats') {
      activeFilters.stats = 'Recent';
      currentMetricId = metricId; // Store the current metric
      ui.statsMetricSelect.value = metricId;
      activeVizSettings.metricId = metricId;
      const statsTab = document.querySelector('.tab[data-view="stats"]');
      if (statsTab) statsTab.click();
      renderStats();
    } else if (action === 'settings') {
      const settingsTab = document.querySelector('.tab[data-view="settings"]');
      const settingsView = document.querySelector('#view-settings');
      if (settingsTab && settingsView) {
        settingsMode = 'metrics';
        isAddingMetric = false;
        isEditingMetric = true;
        selectedMetricForEdit = metricId;
        metricSearchTerm = '';

        const metrics = await listMetrics(true);
        const metric = metrics.find((m) => m.id === metricId);
        ui.metricSearch.value = metric?.name || '';
        ui.metricForm.style.display = 'none';
        ui.metricEditForm.style.display = 'grid';
        ui.metricEditFields.style.display = 'block';
        ui.addMetricBtn.classList.remove('active');
        ui.editMetricBtn.classList.add('active');

        ui.tabs.forEach((item) => item.classList.remove('active'));
        ui.views.forEach((view) => view.classList.remove('active'));
        settingsTab.classList.add('active');
        settingsView.classList.add('active');

        activateSettingsMode('metrics');
        await renderSettings();
      }
    } else if (action === 'last-session') {
      await openStrengthSessionDetails(metricId);
    } else if (action === 'edit-entries') {
      await openEntriesModal(metricId);
    }
    return;
  }
});

ui.backupReminderBanner.addEventListener('click', async () => {
  await triggerCsvExport();
});

ui.statsMetricSelect.addEventListener('change', () => {
  activeVizSettings.metricId = ui.statsMetricSelect.value;
  renderStats();
});

ui.statsPeriodControl.addEventListener('click', (event) => {
  const btn = event.target.closest('.segment');
  if (btn) {
    activeVizSettings.period = btn.dataset.period;
    renderStats();
  }
});

ui.statsZerosToggle.addEventListener('change', () => {
  activeVizSettings.zeros = ui.statsZerosToggle.checked;
  renderStats();
});

ui.statsStrengthSelect.addEventListener('change', () => {
  activeVizSettings.strengthAgg = ui.statsStrengthSelect.value;
  renderStats();
});

ui.statsSummary.addEventListener('click', (event) => {
  const row = event.target.closest('[data-stats-metric-id]');
  if (row) {
    const metricId = row.dataset.statsMetricId;
    ui.statsMetricSelect.value = metricId;
    activeVizSettings.metricId = metricId;
    renderStats();
    ui.statsChartContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
});

async function openEntriesModal(metricId) {
  const metrics = await listMetrics(true);
  const metric = metrics.find(m => m.id === metricId);
  if (!metric) return;

  ui.entriesModalTitle.textContent = metric.name;
  await renderEntriesTable(metricId, metric);
  ui.entriesModal.classList.remove('hidden');
}

function closeEntriesModal() {
  ui.entriesModal.classList.add('hidden');
}

window.handleEditEntry = async function(entryId, metricId, trElement) {
  const entry = (await listEntries()).find(e => e.id === entryId);
  const metrics = await listMetrics(true);
  const metric = metrics.find(m => m.id === metricId);
  
  if (!entry || !metric) return;
  
  // Skip for strength sessions
  if (metric.metricKind === 'strength_session') {
    alert('Edit strength sessions via the Add form.');
    return;
  }
  
  // Replace value cell with input field
  const valueCell = trElement.querySelector('td:nth-child(2)');
  const originalValue = valueCell.textContent.trim();
  
  valueCell.innerHTML = `
    <input type="number" value="${entry.value}" class="edit-input" 
           data-entry-id="${entryId}" data-metric-id="${metricId}" 
           onblur="window.saveInlineEdit(this)" onkeydown="if(event.key==='Enter') window.saveInlineEdit(this); if(event.key==='Escape') window.cancelInlineEdit(this)">
  `;
  
  // Replace actions with Save/Cancel icons
  const actionsCell = trElement.querySelector('.action-buttons');
  actionsCell.innerHTML = `
    <button onclick="window.saveInlineEdit(this.closest('tr').querySelector('.edit-input'))" class="action-btn save-btn" title="Save">✓</button>
    <button onclick="window.cancelInlineEdit(this.closest('tr').querySelector('.edit-input'))" class="action-btn cancel-btn" title="Cancel">✕</button>
  `;
  
  // Focus the input
  const input = valueCell.querySelector('.edit-input');
  if (input) input.focus();
  
  // Reset global edit state
  editingEntryId = null;
}

window.saveInlineEdit = async function(input) {
  const entryId = input.dataset.entryId;
  const metricId = input.dataset.metricId;
  const newValue = Number(input.value);
  
  if (!Number.isFinite(newValue)) {
    window.alert('Please enter a valid numeric value.');
    input.focus();
    return;
  }

  await updateEntry(entryId, { value: newValue });
  editingEntryId = null;
  await renderEntriesTable(metricId); // Refresh table
  // Refresh active views
  const statsView = document.querySelector('#view-stats');
  const homeView = document.querySelector('#view-home');
  if (statsView && statsView.classList.contains('active')) {
    await renderStats();
  }
  if (homeView && homeView.classList.contains('active')) {
    await renderHome();
  }

  window.alert('Entry updated!');
}

window.cancelInlineEdit = async function(input) {
  editingEntryId = null;
  const tr = input.closest('tr');
  const metricId = tr.dataset.metricId;
  const metrics = await listMetrics(true);
  const metric = metrics.find(m => m.id === metricId);
  if (metric) {
    await renderEntriesTable(metricId, metric);
  }
}

window.handleDeleteEntry = async function(entryId, metricId, metricName) {
  if (confirm(`Delete this entry for ${metricName}?`)) {
    await deleteEntry(entryId);
    const metrics = await listMetrics(true);
    const metric = metrics.find(m => m.id === metricId);
    if (metricId && metric) {
      await renderEntriesTable(metricId, metric);
    }
    // Refresh active views
    const statsView = document.querySelector('#view-stats');
    const homeView = document.querySelector('#view-home');
    if (statsView && statsView.classList.contains('active')) {
      await renderStats();
    }
    if (homeView && homeView.classList.contains('active')) {
      await renderHome();
    }
  }
}

async function renderEntriesTable(metricId, metric) {
  const entries = await listEntries();
  const metricEntries = entries.filter(e => e.metricId === metricId);
  metricEntries.sort((a, b) => new Date(b.recordedAt) - new Date(a.recordedAt));

  ui.entriesTableBody.innerHTML = metricEntries.map(entry => {
    const d = new Date(entry.recordedAt);
    const shortDate = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    const shortTime = d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false });
    let displayValue = entry.value;
    if (metric && metric.metricKind === 'strength_session') {
      displayValue = computeStrengthValue(entry, 'Total Volume');
    }

    return `
      <tr data-entry-id="${entry.id}" data-metric-id="${metricId}">
        <td title="${d.toLocaleString()}" style="white-space: nowrap;">${shortDate}<br>${shortTime}</td>
        <td>${displayValue !== null && displayValue !== undefined ? displayValue : ''}</td>
        <td class="action-buttons">
          <button onclick="window.handleEditEntry('${entry.id}', '${metricId}', this.closest('tr'))" title="Edit">✏️</button>
          <button onclick="window.handleDeleteEntry('${entry.id}', '${metricId}', '${metric?.name || ''}')" title="Delete">🗑️</button>
        </td>
      </tr>
    `;
  }).join('');
}

ui.closeEntriesModal?.addEventListener('click', closeEntriesModal);
ui.modalOverlay?.addEventListener('click', closeEntriesModal);

initializeDatabase();
