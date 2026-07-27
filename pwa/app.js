import {
  archiveMetric,
  createCategory,
  createChangeEvent,
  createEntry,
  createMetric,
  deleteCategory,
  deleteMetric,
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
  metricCategory: document.querySelector('#metricCategory'),
  metricList: document.querySelector('#metricList'),
  categoryList: document.querySelector('#categoryList'),
  changeList: document.querySelector('#changeList'),
  statsSummary: document.querySelector('#statsSummary'),
  entryForm: document.querySelector('#entryForm'),
  changeForm: document.querySelector('#changeForm'),
  categoryForm: document.querySelector('#categoryForm'),
  metricForm: document.querySelector('#metricForm'),
  exportButton: document.querySelector('#exportButton'),
  importButton: document.querySelector('#importButton'),
  importFile: document.querySelector('#importFile'),
  installButton: document.querySelector('#installButton'),
  numericValueField: document.querySelector('#numericValueField'),
  strengthWorkoutFields: document.querySelector('#strengthWorkoutFields'),
  strengthLoadInput: document.querySelector('#strengthLoadInput'),
  strengthRepsInput: document.querySelector('#strengthRepsInput'),
  strengthAddSetButton: document.querySelector('#strengthAddSetButton'),
  strengthSetList: document.querySelector('#strengthSetList'),
  strengthBaseline: document.querySelector('#strengthBaseline'),
  entryTargetAction: document.querySelector('#entryTargetAction'),
  targetActionField: document.querySelector('#targetActionField'),
  entryDatePills: document.querySelector('#entryDatePills'),
  dateTimeFields: document.querySelector('#dateTimeFields'),
  targetActionPills: document.querySelector('#targetActionPills'),
  homeCategoryPills: document.querySelector('#homeCategoryPills'),
  addCategoryPills: document.querySelector('#addCategoryPills'),
  statsCategoryPills: document.querySelector('#statsCategoryPills'),
  backupReminderBanner: document.querySelector('#backupReminderBanner'),
  unsavedCount: document.querySelector('#unsavedCount'),
  logCategoryPills: document.querySelector('#logCategoryPills'),
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
};

let deferredPrompt = null;
let strengthSets = [];
let editingSetIndex = null;

let editingEventId = null;
let endingEventId = null;
let revivingEventId = null;

let activeFilters = { home: 'Recent', add: 'Recent', stats: 'Recent', log: 'Recent' };

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

function renderCategoryPills(viewName, categories, container) {
  if (!container) return;
  const options = ['Recent', ...categories.map((c) => c.name.charAt(0).toUpperCase() + c.name.slice(1))];
  const currentFilter = activeFilters[viewName];
  container.innerHTML = options
    .map((opt) => {
      const isActive = opt.toLowerCase() === currentFilter.toLowerCase();
      return `<button class="pill ${isActive ? 'active' : ''}" data-filter="${opt}">${opt}</button>`;
    })
    .join('');
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
  const dateInput = document.querySelector('#entryDate');
  const timeInput = document.querySelector('#entryTime');
  if (dateInput) dateInput.value = dateStr;
  if (timeInput) timeInput.value = timeStr;
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

  renderCategoryPills('add', categories, ui.addCategoryPills);

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
  const [metrics, entries, categories] = await Promise.all([
    listMetrics(true),
    listEntries(),
    listCategories(),
  ]);

  const activeMetrics = metrics.filter((m) => !m.isArchived);

  renderCategoryPills('home', categories, ui.homeCategoryPills);

  const filteredMetrics = await filterMetricsForView('home', activeMetrics, entries, categories);

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
          <button class="card-pill" data-action="stats" data-id="${metric.id}" title="View Stats">📊</button>
          <button class="card-pill" data-action="settings" data-id="${metric.id}" title="Edit Metric">⚙️</button>
        </div>
      </div>
    `;
  }).join('') || '<p>No metrics match this filter.</p>';
}

function renderLogCategoryPills(categories, events, catMap) {
  if (!ui.logCategoryPills) return;
  const showArchived = ui.logShowArchived?.checked || false;
  const visibleEvents = showArchived
    ? events
    : events.filter(e => !e.isArchived);
  
  const presentCatIds = new Set(visibleEvents.map(e => e.categoryId).filter(Boolean));
  const presentCategories = categories
    .filter(c => presentCatIds.has(c.id))
    .map(c => c.name.charAt(0).toUpperCase() + c.name.slice(1))
    .sort((a, b) => a.localeCompare(b));

  const options = ['Recent', ...presentCategories];
  const currentFilter = activeFilters.log || 'Recent';
  ui.logCategoryPills.innerHTML = options
    .map((opt) => {
      const isActive = opt.toLowerCase() === currentFilter.toLowerCase();
      return `<button class="pill ${isActive ? 'active' : ''}" data-filter="${opt}">${opt}</button>`;
    })
    .join('');
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
  renderLogCategoryPills(categories, events, catMap);

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
      <div class="item" style="padding: 12px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 8px; background: var(--surface);">
        <strong style="font-size: 1.1rem; display: block; margin-bottom: 4px;">${displayedTitle}</strong>
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

function resampleAndProcessData(entries, metric, period, zeros, strengthAgg) {
  const metricEntries = entries.filter((e) => e.metricId === metric.id);
  if (metricEntries.length === 0) return [];

  const parsed = metricEntries.map((e) => {
    let val = Number(e.value);
    if (metric.metricKind === 'strength_session') {
      val = computeStrengthValue(e, strengthAgg);
    }
    return {
      date: new Date(e.recordedAt),
      value: val,
    };
  }).sort((a, b) => a.date - b.date);

  const maxDate = parsed[parsed.length - 1].date;
  const startDate = getStartDateForPeriod(period, maxDate);

  let filtered = parsed.filter((e) => e.date >= startDate);
  if (filtered.length === 0) return [];

  const dailyMap = new Map();
  filtered.forEach((e) => {
    const key = e.date.toISOString().split('T')[0];
    if (!dailyMap.has(key)) {
      dailyMap.set(key, []);
    }
    dailyMap.get(key).push(e.value);
  });

  const dailyEntries = [];
  dailyMap.forEach((vals, key) => {
    let collapsedVal = 0;
    if (metric.metricKind === 'count') {
      collapsedVal = vals.reduce((s, v) => s + v, 0);
    } else if (metric.metricKind === 'score' || metric.unitType === 'integer_range') {
      const sorted = [...vals].sort((a, b) => a - b);
      const mid = Math.floor(sorted.length / 2);
      collapsedVal = sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    } else {
      collapsedVal = vals.reduce((s, v) => s + v, 0) / vals.length;
    }
    dailyEntries.push({ dateStr: key, date: new Date(key), value: collapsedVal });
  });

  dailyEntries.sort((a, b) => a.date - b.date);

  if (!zeros) {
    return dailyEntries;
  }

  const firstDate = dailyEntries[0].date;
  const lastDate = dailyEntries[dailyEntries.length - 1].date;
  const filled = [];
  const dailyLookup = new Map(dailyEntries.map((e) => [e.dateStr, e.value]));

  const current = new Date(firstDate);
  while (current <= lastDate) {
    const key = current.toISOString().split('T')[0];
    const val = dailyLookup.has(key) ? dailyLookup.get(key) : 0;
    filled.push({
      dateStr: key,
      date: new Date(current),
      value: val,
    });
    current.setDate(current.getDate() + 1);
  }
  return filled;
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

  renderCategoryPills('stats', categories, ui.statsCategoryPills);

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

let settingsShowMetrics = false;
let settingsShowCategories = false;

async function renderSettings() {
  const [categories, metrics] = await Promise.all([
    listCategories(),
    listMetrics(true),
  ]);

  if (settingsShowCategories) {
    ui.categoryList.innerHTML = categories.map((category) => `
      <div class="item">
        <strong>${category.name}</strong>
        <div>
          <button data-action="rename-category" data-id="${category.id}" class="secondary">Rename</button>
          <button data-action="delete-category" data-id="${category.id}" class="secondary">Delete</button>
        </div>
      </div>
    `).join('');
  } else {
    ui.categoryList.innerHTML = '<p class="muted-text" style="padding: 1rem; text-align: center; opacity: 0.6;">Select or create a category to manage.</p>';
  }

  if (settingsShowMetrics) {
    ui.metricList.innerHTML = metrics.map((metric) => `
      <div class="item">
        <strong>${metric.name}</strong>
        <div>${metric.unitName || 'unit'} · ${metric.metricKind || metric.unitType || 'metric'}</div>
        <div>
          <button data-action="rename-metric" data-id="${metric.id}" class="secondary">Rename</button>
          <button data-action="archive-metric" data-id="${metric.id}" class="secondary">Archive</button>
          <button data-action="delete-metric" data-id="${metric.id}" class="secondary">Delete</button>
        </div>
      </div>`).join('');
  } else {
    ui.metricList.innerHTML = '<p class="muted-text" style="padding: 1rem; text-align: center; opacity: 0.6;">Select or create a metric to manage.</p>';
  }
  
  ui.metricCategory.innerHTML = categories.map((category) => `<option value="${category.id}">${category.name}</option>`).join('');
}

ui.tabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    ui.tabs.forEach((item) => item.classList.remove('active'));
    ui.views.forEach((view) => view.classList.remove('active'));
    tab.classList.add('active');
    document.querySelector(`#view-${tab.dataset.view}`).classList.add('active');
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
  syncAddFormMode();
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
  const metricId = ui.metricSelect.value;
  if (!metricId) return;

  const metrics = await listMetrics(false);
  const metric = metrics.find((item) => item.id === metricId) || null;
  const recordedAt = new Date(`${document.querySelector('#entryDate').value}T${document.querySelector('#entryTime').value}`).toISOString();

  // Get target action from active pill
  const activeTargetPill = ui.targetActionPills?.querySelector('.pill.active');
  const targetAction = activeTargetPill ? (activeTargetPill.dataset.target === 'None' ? null : activeTargetPill.dataset.target) : null;

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
      value: Number(document.querySelector('#entryValue').value),
      targetAction,
      recordedAt,
    });
  }

  strengthSets = [];
  editingSetIndex = null;
  ui.entryForm.reset();
  resetEntryFormDateTime();
  incrementUnsavedCount();
  renderAll();
});

ui.categoryForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const name = document.querySelector('#categoryName').value.trim();
  if (!name) return;
  await createCategory(name);
  settingsShowCategories = true;
  ui.categoryForm.reset();
  incrementUnsavedCount();
  renderAll();
});

ui.metricForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const categoryId = ui.metricCategory.value;
  await createMetric({
    name: document.querySelector('#metricName').value.trim(),
    categoryId,
    unitName: document.querySelector('#metricUnit').value.trim() || null,
    unitType: document.querySelector('#metricType').value,
    metricKind: document.querySelector('#metricKind').value,
    higherIsBetter: true,
    isArchived: false,
  });
  settingsShowMetrics = true;
  ui.metricForm.reset();
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

if (ui.logCategoryPills) {
  ui.logCategoryPills.addEventListener('click', (event) => {
    handlePillClick('log', event, renderLogs);
  });
}

ui.metricList.addEventListener('click', async (event) => {
  const actionButton = event.target.closest('[data-action]');
  if (!actionButton) return;
  const metricId = actionButton.dataset.id;
  if (actionButton.dataset.action === 'rename-metric') {
    const nextName = window.prompt('Rename metric', '');
    if (!nextName) return;
    await updateMetric(metricId, { name: nextName.trim().toLowerCase() });
    renderAll();
  }
  if (actionButton.dataset.action === 'archive-metric') {
    await archiveMetric(metricId);
    renderAll();
  }
  if (actionButton.dataset.action === 'delete-metric') {
    if (window.confirm('Are you sure you want to delete this metric?')) {
      await deleteMetric(metricId);
      renderAll();
    }
  }
});

ui.categoryList.addEventListener('click', async (event) => {
  const actionButton = event.target.closest('[data-action]');
  if (!actionButton) return;
  const categoryId = actionButton.dataset.id;
  if (actionButton.dataset.action === 'rename-category') {
    const nextName = window.prompt('Rename category', '');
    if (!nextName) return;
    await updateCategory(categoryId, { name: nextName.trim().toLowerCase() });
    renderAll();
  }
  if (actionButton.dataset.action === 'delete-category') {
    if (window.confirm('Are you sure you want to delete this category? All its metrics will become uncategorized.')) {
      await deleteCategory(categoryId);
      renderAll();
    }
  }
});

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

function handlePillClick(viewName, event, reRenderFunc) {
  const pill = event.target.closest('.pill');
  if (!pill) return;
  activeFilters[viewName] = pill.dataset.filter;
  reRenderFunc();
}

ui.homeCategoryPills.addEventListener('click', (event) => {
  handlePillClick('home', event, renderHome);
});

ui.addCategoryPills.addEventListener('click', (event) => {
  handlePillClick('add', event, renderMetricDropdown);
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

ui.statsCategoryPills.addEventListener('click', (event) => {
  handlePillClick('stats', event, renderStats);
});

ui.metricGrid.addEventListener('click', async (event) => {
  const btn = event.target.closest('.card-pill');
  if (btn) {
    event.stopPropagation();
    const action = btn.dataset.action;
    const metricId = btn.dataset.id;
    if (action === 'add') {
      activeFilters.add = 'Recent';
      await renderMetricDropdown();
      ui.metricSelect.value = metricId;
      await syncAddFormMode();
      const addTab = document.querySelector('.tab[data-view="add"]');
      if (addTab) addTab.click();
    } else if (action === 'stats') {
      activeFilters.stats = 'Recent';
      ui.statsMetricSelect.value = metricId;
      activeVizSettings.metricId = metricId;
      const statsTab = document.querySelector('.tab[data-view="stats"]');
      if (statsTab) statsTab.click();
      renderStats();
    } else if (action === 'settings') {
      settingsShowMetrics = true;
      const settingsTab = document.querySelector('.tab[data-view="settings"]');
      if (settingsTab) settingsTab.click();
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

initializeDatabase();
