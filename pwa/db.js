const DB_NAME = 'quantifi-pwa';
const DB_VERSION = 1;

export const STORE_NAMES = {
  categories: 'categories',
  metrics: 'metrics',
  entries: 'entries',
  changeEvents: 'changeEvents',
};

let dbPromise;

export function uid() {
  return (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID()
    : `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function nowIso() {
  return new Date().toISOString();
}

export function openDb() {
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = (event) => {
        const current = event.target.result;
        for (const storeName of Object.values(STORE_NAMES)) {
          if (!current.objectStoreNames.contains(storeName)) {
            current.createObjectStore(storeName, { keyPath: 'id' });
          }
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
  return dbPromise;
}

export async function getStore(storeName, mode = 'readonly') {
  const database = await openDb();
  return database.transaction(storeName, mode).objectStore(storeName);
}

export async function getAll(storeName) {
  const store = await getStore(storeName);
  return new Promise((resolve, reject) => {
    const request = store.getAll();
    request.onsuccess = () => resolve(request.result || []);
    request.onerror = () => reject(request.error);
  });
}

export async function putRecord(storeName, record) {
  const store = await getStore(storeName, 'readwrite');
  return new Promise((resolve, reject) => {
    const request = store.put(record);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function updateRecord(storeName, id, changes) {
  const current = await getRecord(storeName, id);
  if (!current) return null;
  const record = { ...current, ...changes };
  await putRecord(storeName, record);
  return record;
}

export async function getRecord(storeName, id) {
  const store = await getStore(storeName);
  return new Promise((resolve, reject) => {
    const request = store.get(id);
    request.onsuccess = () => resolve(request.result || null);
    request.onerror = () => reject(request.error);
  });
}

export async function deleteRecord(storeName, id) {
  const store = await getStore(storeName, 'readwrite');
  return new Promise((resolve, reject) => {
    const request = store.delete(id);
    request.onsuccess = () => resolve(true);
    request.onerror = () => reject(request.error);
  });
}

export async function seedBaseData() {
  const categories = await getAll(STORE_NAMES.categories);
  if (categories.length > 0) {
    return false;
  }

  const generalCategory = {
    id: uid(),
    name: 'General',
    createdAt: nowIso(),
  };
  const strengthCategory = {
    id: uid(),
    name: 'Strength',
    createdAt: nowIso(),
  };

  const moodMetric = {
    id: uid(),
    name: 'mood',
    description: 'Daily mood score',
    unitName: 'score',
    unitType: 'integer_range',
    metricKind: 'score',
    rangeStart: 1,
    rangeEnd: 5,
    higherIsBetter: true,
    isArchived: false,
    categoryId: generalCategory.id,
    createdAt: nowIso(),
  };

  const waterMetric = {
    id: uid(),
    name: 'water',
    description: 'Hydration goal',
    unitName: 'glasses',
    unitType: 'integer',
    metricKind: 'count',
    rangeStart: null,
    rangeEnd: null,
    higherIsBetter: true,
    isArchived: false,
    categoryId: generalCategory.id,
    createdAt: nowIso(),
  };

  const firstEntry = {
    id: uid(),
    metricId: moodMetric.id,
    value: 4,
    recordedAt: nowIso(),
    createdAt: nowIso(),
  };

  await putRecord(STORE_NAMES.categories, generalCategory);
  await putRecord(STORE_NAMES.categories, strengthCategory);
  await putRecord(STORE_NAMES.metrics, moodMetric);
  await putRecord(STORE_NAMES.metrics, waterMetric);
  await putRecord(STORE_NAMES.entries, firstEntry);
  return true;
}

export async function listCategories() {
  return getAll(STORE_NAMES.categories);
}

export async function listMetrics(includeArchived = true) {
  const metrics = await getAll(STORE_NAMES.metrics);
  if (includeArchived) {
    return metrics;
  }
  return metrics.filter((metric) => !metric.isArchived);
}

export async function listEntries() {
  return getAll(STORE_NAMES.entries);
}

export async function listEntriesForMetric(metricId) {
  const entries = await listEntries();
  return entries.filter((entry) => entry.metricId === metricId);
}

export async function listChangeEvents() {
  return getAll(STORE_NAMES.changeEvents);
}

export async function createCategory(name) {
  const record = {
    id: uid(),
    name: String(name || '').trim().toLowerCase(),
    createdAt: nowIso(),
  };
  await putRecord(STORE_NAMES.categories, record);
  return record;
}

export async function updateCategory(categoryId, changes) {
  return updateRecord(STORE_NAMES.categories, categoryId, changes);
}

export async function deleteCategory(categoryId) {
  await deleteRecord(STORE_NAMES.categories, categoryId);
}

export async function createMetric(payload) {
  const record = {
    id: uid(),
    name: String(payload.name || '').trim().toLowerCase(),
    description: payload.description || null,
    unitName: payload.unitName || null,
    unitType: payload.unitType || 'float',
    metricKind: payload.metricKind || 'quantitative',
    rangeStart: payload.rangeStart ?? null,
    rangeEnd: payload.rangeEnd ?? null,
    higherIsBetter: payload.higherIsBetter ?? true,
    isArchived: Boolean(payload.isArchived),
    categoryId: payload.categoryId || null,
    createdAt: nowIso(),
  };
  await putRecord(STORE_NAMES.metrics, record);
  return record;
}

export async function updateMetric(metricId, changes) {
  return updateRecord(STORE_NAMES.metrics, metricId, changes);
}

export async function archiveMetric(metricId) {
  return updateRecord(STORE_NAMES.metrics, metricId, { isArchived: true });
}

export async function deleteMetric(metricId) {
  await deleteRecord(STORE_NAMES.metrics, metricId);
  const entries = await listEntriesForMetric(metricId);
  for (const entry of entries) {
    await deleteRecord(STORE_NAMES.entries, entry.id);
  }
}

export async function createEntry(payload) {
  const record = {
    id: uid(),
    metricId: payload.metricId,
    value: payload.value ?? null,
    loadKg: payload.loadKg ?? null,
    sets: Array.isArray(payload.sets) ? payload.sets : [],
    targetAction: payload.targetAction || null,
    recordedAt: payload.recordedAt || nowIso(),
    createdAt: nowIso(),
  };
  await putRecord(STORE_NAMES.entries, record);
  return record;
}

export async function updateEntry(entryId, changes) {
  return updateRecord(STORE_NAMES.entries, entryId, changes);
}

export async function deleteEntry(entryId) {
  await deleteRecord(STORE_NAMES.entries, entryId);
}

export async function createChangeEvent(payload) {
  const record = {
    id: uid(),
    title: String(payload.title || '').trim(),
    notes: payload.notes || '',
    recordedAt: payload.recordedAt || nowIso(),
    endAt: payload.endAt || null,
    isArchived: Boolean(payload.isArchived),
    categoryId: payload.categoryId || null,
    createdAt: nowIso(),
  };
  await putRecord(STORE_NAMES.changeEvents, record);
  return record;
}

export async function updateChangeEvent(eventId, changes) {
  return updateRecord(STORE_NAMES.changeEvents, eventId, changes);
}

export async function deleteChangeEvent(eventId) {
  await deleteRecord(STORE_NAMES.changeEvents, eventId);
}

export async function getMetricByName(name) {
  const metrics = await listMetrics(true);
  const normalized = String(name || '').trim().toLowerCase();
  return metrics.find((metric) => String(metric.name || '').trim().toLowerCase() === normalized) || null;
}

function parseCsvLine(line) {
  const cells = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    const next = line[i + 1];

    if (char === '"') {
      if (inQuotes && next === '"') {
        current += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (char === ',' && !inQuotes) {
      cells.push(current);
      current = '';
      continue;
    }

    current += char;
  }

  cells.push(current);
  return cells;
}

function parseCsvText(text) {
  const rows = text
    .split(/\r?\n/)
    .filter((line) => line.trim().length > 0)
    .map((line) => parseCsvLine(line));

  if (!rows.length) {
    return [];
  }

  const headers = rows[0].map((header) => String(header || '').trim());
  return rows.slice(1).map((row) => {
    const record = {};
    headers.forEach((header, index) => {
      record[header] = row[index] ?? '';
    });
    return record;
  });
}

function parseSetsField(value) {
  const text = String(value ?? '').trim();
  if (!text) return [];
  try {
    const parsed = JSON.parse(text);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function toBoolean(value) {
  return String(value).trim().toLowerCase() === 'true';
}

function coerceNumber(value) {
  if (value === null || value === undefined) return null;
  const clean = String(value).trim();
  if (!clean) return null;
  const parsed = Number(clean);
  return Number.isFinite(parsed) ? parsed : null;
}

export async function importCsvText(csvText) {
  const rows = parseCsvText(csvText);
  const imported = {
    categories: 0,
    metrics: 0,
    entries: 0,
    changes: 0,
  };

  for (const row of rows) {
    const rowType = String(row.RowType || '').trim().toLowerCase();
    if (rowType === 'entry') {
      const categoryName = String(row.Category || '').trim().toLowerCase();
      const metricName = String(row.Metric || '').trim().toLowerCase();
      const unitName = String(row.Unit || '').trim().toLowerCase();
      const unitType = String(row.Type || 'float').trim().toLowerCase();
      const metricKind = String(row.Kind || '').trim().toLowerCase();
      const targetCategory = categoryName ? await getOrCreateCategory(categoryName) : null;
      let metric = await getMetricByName(metricName);

      if (!metric) {
        metric = await createMetric({
          name: metricName,
          description: String(row.Description || '').trim() || null,
          unitName: unitName || null,
          unitType,
          metricKind: metricKind || (unitType === 'integer_range' ? 'score' : unitType === 'integer' ? 'count' : 'quantitative'),
          rangeStart: coerceNumber(row.Min),
          rangeEnd: coerceNumber(row.Max),
          higherIsBetter: row.HigherIsBetter === '' ? true : toBoolean(row.HigherIsBetter),
          isArchived: toBoolean(row.Archived),
          categoryId: targetCategory?.id || null,
        });
        imported.metrics += 1;
      }

      await createEntry({
        metricId: metric.id,
        value: coerceNumber(row.Value),
        loadKg: coerceNumber(row.LoadKg),
        sets: parseSetsField(row.Sets),
        targetAction: String(row.Target || '').trim() || null,
        recordedAt: row.Date,
      });
      imported.entries += 1;
    }

    if (rowType === 'change') {
      const categoryName = String(row.Category || '').trim().toLowerCase();
      const category = categoryName ? await getOrCreateCategory(categoryName) : null;
      await createChangeEvent({
        title: String(row.Title || '').trim(),
        notes: String(row.Notes || '').trim(),
        recordedAt: row.Date,
        endAt: row.EndDate || null,
        isArchived: toBoolean(row.Archived),
        categoryId: category?.id || null,
      });
      imported.changes += 1;
    }
  }

  return imported;
}

export async function getOrCreateCategory(name) {
  const normalized = String(name || '').trim().toLowerCase();
  if (!normalized) return null;
  const categories = await listCategories();
  const match = categories.find((category) => String(category.name || '').trim().toLowerCase() === normalized);
  if (match) return match;
  const category = await createCategory(normalized);
  return category;
}

export async function exportDataAsCsv() {
  const [categories, metrics, entries, changeEvents] = await Promise.all([
    listCategories(),
    listMetrics(true),
    listEntries(),
    listChangeEvents(),
  ]);

  const categoryMap = Object.fromEntries(categories.map((category) => [category.id, category.name]));
  const metricMap = Object.fromEntries(metrics.map((metric) => [metric.id, metric]));

  const rows = [
    ['RowType', 'Date', 'Category', 'Metric', 'Description', 'Archived', 'Value', 'Unit', 'Type', 'Kind', 'Min', 'Max', 'HigherIsBetter', 'Target', 'LoadKg', 'Sets', 'Title', 'Notes', 'EndDate'],
    ...entries.map((entry) => {
      const metric = metricMap[entry.metricId] || {};
      return [
        'entry',
        entry.recordedAt,
        categoryMap[metric.categoryId] || '',
        metric.name || '',
        metric.description || '',
        Boolean(metric.isArchived),
        entry.value ?? '',
        metric.unitName || '',
        metric.unitType || '',
        metric.metricKind || '',
        metric.rangeStart ?? '',
        metric.rangeEnd ?? '',
        metric.higherIsBetter ?? true,
        entry.targetAction ?? '',
        entry.loadKg ?? '',
        JSON.stringify(entry.sets || []),
        '',
        '',
        '',
      ];
    }),
    ...changeEvents.map((event) => [
      'change',
      event.recordedAt,
      categoryMap[event.categoryId] || '',
      '',
      '',
      Boolean(event.isArchived),
      '',
      '',
      '',
      '',
      '',
      '',
      '',
      '',
      event.title || '',
      event.notes || '',
      event.endAt || '',
    ]),
  ];

  return rows
    .map((row) => row.map((cell) => `"${String(cell ?? '').replaceAll('"', '""')}"`).join(','))
    .join('\n');
}
