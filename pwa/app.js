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
};

let deferredPrompt = null;
let strengthSets = [];

async function initializeDatabase() {
  await seedBaseData();
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
    ? strengthSets.map((set, index) => `
        <div class="item">
          <strong>Set ${index + 1}</strong>
          <div>${Number(set.loadKg).toFixed(1)} kg × ${set.reps} reps</div>
          <div>
            <button type="button" data-remove-set="${index}" class="secondary">Remove</button>
          </div>
        </div>
      `).join('')
    : '<p>No sets yet.</p>';
}

async function syncAddFormMode() {
  const metrics = await listMetrics(false);
  const metric = metrics.find((item) => item.id === ui.metricSelect.value) || metrics[0] || null;

  const isStrength = metric?.metricKind === 'strength_session';
  ui.numericValueField.classList.toggle('hidden', isStrength);
  ui.strengthWorkoutFields.classList.toggle('hidden', !isStrength);

  if (isStrength) {
    const [entries] = await Promise.all([listEntries()]);
    const metricEntries = entries.filter((entry) => entry.metricId === metric.id);
    const lastEntry = metricEntries.sort((a, b) => new Date(b.recordedAt) - new Date(a.recordedAt))[0];
    ui.strengthLoadInput.value = lastEntry?.loadKg ?? lastEntry?.value ?? 0;
    renderStrengthSetList();
  }
}

async function renderMetricDropdown() {
  const metrics = await listMetrics(false);
  ui.metricSelect.innerHTML = metrics
    .map((metric) => `<option value="${metric.id}">${metric.name}</option>`)
    .join('');
  ui.metricSelect.value = metrics[0]?.id ?? '';
  await syncAddFormMode();
}

async function renderHome() {
  const [metrics, entries, categories] = await Promise.all([
    listMetrics(true),
    listEntries(),
    listCategories(),
  ]);

  const categoryMap = Object.fromEntries(categories.map((category) => [category.id, category.name]));

  ui.metricGrid.innerHTML = metrics.map((metric) => {
    const metricEntries = entries.filter((entry) => entry.metricId === metric.id);
    const latest = metricEntries.sort((a, b) => new Date(b.recordedAt) - new Date(a.recordedAt))[0];
    const categoryName = categoryMap[metric.categoryId] || 'General';
    const valueLabel = latest ? latest.value ?? '—' : 'No data yet';
    return `
      <article class="card">
        <div class="card-topline">${categoryName}</div>
        <strong>${metric.name}</strong>
        <small>${metric.unitName || 'unit'} · ${metric.metricKind || metric.unitType || 'metric'}</small>
        <div class="card-value">${valueLabel}</div>
      </article>
    `;
  }).join('') || '<p>No metrics yet.</p>';
}

async function renderLogs() {
  const [events, categories] = await Promise.all([
    listChangeEvents(),
    listCategories(),
  ]);
  const catMap = Object.fromEntries(categories.map((item) => [item.id, item.name]));
  ui.changeList.innerHTML = events
    .map((event) => `<div class="item"><strong>${event.title}</strong><div>${event.notes || 'No notes'}</div><small>${new Date(event.recordedAt).toLocaleString()} · ${catMap[event.categoryId] || 'General'}</small></div>`)
    .join('') || '<p>No changes yet.</p>';
}

async function renderStats() {
  const [metrics, entries] = await Promise.all([
    listMetrics(true),
    listEntries(),
  ]);
  const summary = metrics.map((metric) => {
    const metricEntries = entries.filter((entry) => entry.metricId === metric.id);
    const values = metricEntries.map((entry) => Number(entry.value)).filter((n) => !Number.isNaN(n));
    const total = values.reduce((sum, value) => sum + value, 0);
    const latest = values.at(-1);
    return `<div class="item"><strong>${metric.name}</strong><div>${values.length} entries · total ${total.toFixed(1)} · latest ${latest ?? '—'}</div></div>`;
  });
  ui.statsSummary.innerHTML = summary.join('') || '<p>No stats yet.</p>';
}

async function renderSettings() {
  const [categories, metrics] = await Promise.all([
    listCategories(),
    listMetrics(true),
  ]);
  ui.categoryList.innerHTML = categories.map((category) => `
    <div class="item">
      <strong>${category.name}</strong>
      <div>
        <button data-action="rename-category" data-id="${category.id}" class="secondary">Rename</button>
        <button data-action="delete-category" data-id="${category.id}" class="secondary">Delete</button>
      </div>
    </div>
  `).join('');
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
  if (!removeButton) return;
  const index = Number(removeButton.dataset.removeSet);
  strengthSets.splice(index, 1);
  renderStrengthSetList();
});

ui.entryForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const metricId = ui.metricSelect.value;
  if (!metricId) return;

  const metrics = await listMetrics(false);
  const metric = metrics.find((item) => item.id === metricId) || null;
  const recordedAt = new Date(`${document.querySelector('#entryDate').value}T${document.querySelector('#entryTime').value}`).toISOString();

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
      recordedAt,
    });
  } else {
    await createEntry({
      metricId,
      value: Number(document.querySelector('#entryValue').value),
      recordedAt,
    });
  }

  strengthSets = [];
  ui.entryForm.reset();
  renderAll();
});

ui.categoryForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const name = document.querySelector('#categoryName').value.trim();
  if (!name) return;
  await createCategory(name);
  ui.categoryForm.reset();
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
  ui.metricForm.reset();
  renderAll();
});

ui.changeForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  await createChangeEvent({
    title: document.querySelector('#changeTitle').value.trim(),
    notes: document.querySelector('#changeNotes').value.trim(),
    recordedAt: new Date().toISOString(),
    endAt: null,
    isArchived: false,
    categoryId: null,
  });
  ui.changeForm.reset();
  renderAll();
});

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
    await deleteMetric(metricId);
    renderAll();
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
    await deleteCategory(categoryId);
    renderAll();
  }
});

ui.exportButton.addEventListener('click', async () => {
  const csv = await exportDataAsCsv();
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'quantifi-pwa-export.csv';
  link.click();
  URL.revokeObjectURL(url);
});

ui.importButton.addEventListener('click', () => {
  ui.importFile.click();
});

ui.importFile.addEventListener('change', async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  const text = await file.text();
  const summary = await importCsvText(text);
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

initializeDatabase();
