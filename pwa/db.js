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

function parseCsvText(text) {
  const rows = [];
  let currentRow = [];
  let currentCell = '';
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const nextChar = text[i + 1];

    if (char === '"') {
      if (inQuotes && nextChar === '"') {
        currentCell += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      currentRow.push(currentCell);
      currentCell = '';
    } else if ((char === '\r' || char === '\n') && !inQuotes) {
      if (char === '\r' && nextChar === '\n') {
        i += 1;
      }
      currentRow.push(currentCell);
      if (currentRow.length > 1 || (currentRow.length === 1 && currentRow[0].trim() !== '')) {
        rows.push(currentRow);
      }
      currentRow = [];
      currentCell = '';
    } else {
      currentCell += char;
    }
  }

  if (currentCell !== '' || currentRow.length > 0) {
    currentRow.push(currentCell);
    if (currentRow.length > 1 || (currentRow.length === 1 && currentRow[0].trim() !== '')) {
      rows.push(currentRow);
    }
  }

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

export async function cleanupDuplicates() {
  const [entries, changeEvents] = await Promise.all([
    listEntries(),
    listChangeEvents(),
  ]);

  const getNaiveKeys = (dStr) => {
    if (!dStr) return [];
    const d = new Date(dStr);
    if (Number.isNaN(d.getTime())) return [String(dStr).trim().toLowerCase()];
    const pad = (num) => String(num).padStart(2, '0');
    const localStr = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    const utcStr = `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
    return [localStr, utcStr];
  };

  // 1. Deduplicate Entries
  const entryGroups = {};
  for (const entry of entries) {
    const naiveKeys = getNaiveKeys(entry.recordedAt);
    const key = `${entry.metricId}_${naiveKeys[0]}`;
    if (!entryGroups[key]) {
      entryGroups[key] = [];
    }
    entryGroups[key].push(entry);
  }

  for (const group of Object.values(entryGroups)) {
    if (group.length > 1) {
      group.sort((a, b) => {
        const aSets = Array.isArray(a.sets) ? a.sets.length : 0;
        const bSets = Array.isArray(b.sets) ? b.sets.length : 0;
        if (aSets !== bSets) return bSets - aSets;
        const aVal = a.value !== null && a.value !== undefined ? 1 : 0;
        const bVal = b.value !== null && b.value !== undefined ? 1 : 0;
        if (aVal !== bVal) return bVal - aVal;
        return new Date(b.createdAt || 0) - new Date(a.createdAt || 0);
      });

      for (let i = 1; i < group.length; i++) {
        await deleteEntry(group[i].id);
      }
    }
  }

  // 2. Deduplicate Change Events
  const changeGroups = {};
  for (const change of changeEvents) {
    const title = String(change.title || '').trim().toLowerCase();
    const naiveKeys = getNaiveKeys(change.recordedAt);
    const key = `${title}_${naiveKeys[0]}`;
    if (!changeGroups[key]) {
      changeGroups[key] = [];
    }
    changeGroups[key].push(change);
  }

  for (const group of Object.values(changeGroups)) {
    if (group.length > 1) {
      group.sort((a, b) => {
        const aNotesLen = String(a.notes || '').trim().length;
        const bNotesLen = String(b.notes || '').trim().length;
        if (aNotesLen !== bNotesLen) return bNotesLen - aNotesLen;
        return new Date(b.createdAt || 0) - new Date(a.createdAt || 0);
      });

      for (let i = 1; i < group.length; i++) {
        await deleteChangeEvent(group[i].id);
      }
    }
  }
}

export async function importCsvText(csvText) {
  // First, heal any existing duplicates in the database
  await cleanupDuplicates();

  const rows = parseCsvText(csvText);
  const imported = {
    categories: 0,
    metrics: 0,
    entries: 0,
    changes: 0,
  };

  const existingEntries = await listEntries();
  const existingChanges = await listChangeEvents();

  const normalizeDate = (dStr) => {
    if (!dStr) return '';
    try {
      return new Date(dStr).toISOString();
    } catch {
      return dStr;
    }
  };

  const getNaiveKeys = (dStr) => {
    if (!dStr) return [];
    const d = new Date(dStr);
    if (Number.isNaN(d.getTime())) return [String(dStr).trim().toLowerCase()];
    const pad = (num) => String(num).padStart(2, '0');
    const localStr = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    const utcStr = `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
    return [localStr, utcStr];
  };

  const entryLookup = new Set();
  for (const e of existingEntries) {
    const keys = getNaiveKeys(e.recordedAt);
    for (const key of keys) {
      entryLookup.add(`${e.metricId}_${key}`);
    }
  }

  const changeLookup = new Set();
  for (const c of existingChanges) {
    const keys = getNaiveKeys(c.recordedAt);
    const title = String(c.title || '').trim().toLowerCase();
    for (const key of keys) {
      changeLookup.add(`${title}_${key}`);
    }
  }

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

      const normalizedDate = normalizeDate(row.Date);
      const naiveKeys = getNaiveKeys(normalizedDate);
      let isDuplicate = false;
      for (const key of naiveKeys) {
        if (entryLookup.has(`${metric.id}_${key}`)) {
          isDuplicate = true;
          break;
        }
      }

      if (!isDuplicate) {
        await createEntry({
          metricId: metric.id,
          value: coerceNumber(row.Value),
          loadKg: coerceNumber(row.LoadKg),
          sets: parseSetsField(row.Sets),
          targetAction: String(row.Target || '').trim() || null,
          recordedAt: normalizedDate,
        });
        for (const key of naiveKeys) {
          entryLookup.add(`${metric.id}_${key}`);
        }
        imported.entries += 1;
      }
    }

    if (rowType === 'change') {
      const categoryName = String(row.Category || '').trim().toLowerCase();
      const category = categoryName ? await getOrCreateCategory(categoryName) : null;
      const normalizedDate = normalizeDate(row.Date);
      const changeTitle = String(row.Title || '').trim();
      const naiveKeys = getNaiveKeys(normalizedDate);
      let isDuplicate = false;
      for (const key of naiveKeys) {
        if (changeLookup.has(`${changeTitle.toLowerCase()}_${key}`)) {
          isDuplicate = true;
          break;
        }
      }

      if (!isDuplicate) {
        await createChangeEvent({
          title: changeTitle,
          notes: String(row.Notes || '').trim(),
          recordedAt: normalizedDate,
          endAt: row.EndDate ? normalizeDate(row.EndDate) : null,
          isArchived: toBoolean(row.Archived),
          categoryId: category?.id || null,
        });
        for (const key of naiveKeys) {
          changeLookup.add(`${changeTitle.toLowerCase()}_${key}`);
        }
        imported.changes += 1;
      }
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
