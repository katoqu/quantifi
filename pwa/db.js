import { validateWorkoutPlan } from './workout-model.js';

const DB_NAME = 'quantifi-pwa';
const DB_VERSION = 3;

export const STORE_NAMES = {
  categories: 'categories',
  metrics: 'metrics',
  entries: 'entries',
  changeEvents: 'changeEvents',
  workoutPlans: 'workoutPlans',
  workoutSessions: 'workoutSessions',
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
        if (event.oldVersion < 3 && current.objectStoreNames.contains(STORE_NAMES.entries)) {
          const entries = request.transaction.objectStore(STORE_NAMES.entries);
          const cursorRequest = entries.openCursor();
          cursorRequest.onsuccess = () => {
            const cursor = cursorRequest.result;
            if (!cursor) return;
            const entry = cursor.value;
            let changed = false;
            if (!Object.hasOwn(entry, 'loadValue') && Object.hasOwn(entry, 'loadKg')) {
              entry.loadValue = entry.loadKg;
              changed = true;
            }
            if (Object.hasOwn(entry, 'loadKg')) {
              delete entry.loadKg;
              changed = true;
            }
            if (Array.isArray(entry.sets)) {
              entry.sets = entry.sets.map((set) => {
                if (!Object.hasOwn(set, 'loadKg') && !Object.hasOwn(set, 'load_kg')) return set;
                const migratedSet = {
                  ...set,
                  ...(!Object.hasOwn(set, 'loadValue') ? { loadValue: set.loadKg ?? set.load_kg } : {}),
                };
                delete migratedSet.loadKg;
                delete migratedSet.load_kg;
                changed = true;
                return migratedSet;
              });
            }
            if (changed) cursor.update(entry);
            cursor.continue();
          };
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

export async function createCategory(name, description = null) {
  const record = {
    id: uid(),
    name: String(name || '').trim().toLowerCase(),
    createdAt: nowIso(),
  };
  if (description) {
    record.description = String(description).trim();
  }
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
  const metric = await getRecord(STORE_NAMES.metrics, metricId);
  if (!metric) {
    throw new Error('Metric not found.');
  }
  if (!metric.isArchived) {
    throw new Error('Only archived metrics can be deleted.');
  }

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
    loadValue: payload.loadValue ?? payload.loadKg ?? null,
    sets: Array.isArray(payload.sets) ? payload.sets : [],
    targetAction: payload.targetAction || null,
    recordedAt: payload.recordedAt || nowIso(),
    createdAt: nowIso(),
    ...(payload.workoutPlanId ? { workoutPlanId: payload.workoutPlanId } : {}),
    ...(payload.workoutSessionId ? { workoutSessionId: payload.workoutSessionId } : {}),
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

function parseWorkoutDataField(value, label) {
  try {
    const parsed = JSON.parse(String(value || ''));
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error();
    return parsed;
  } catch {
    throw new Error(`The CSV contains invalid ${label} data.`);
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
    const key = `${entry.metricId}_${entry.workoutSessionId || 'standalone'}_${naiveKeys[0]}`;
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
    workoutPlans: 0,
    workoutSessions: 0,
  };

  const existingEntries = await listEntries();
  const existingChanges = await listChangeEvents();
  const existingWorkoutPlans = await getAll(STORE_NAMES.workoutPlans);
  const existingWorkoutSessions = await getAll(STORE_NAMES.workoutSessions);
  const knownPlanIds = new Set(existingWorkoutPlans.map((plan) => plan.id));
  const knownSessionIds = new Set(existingWorkoutSessions.map((session) => session.id));
  const metricIdLookup = new Map();
  const entryIdLookup = new Map();

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
      const lookupKey = `${e.metricId}_${e.workoutSessionId || 'standalone'}_${key}`;
      entryLookup.add(lookupKey);
      entryIdLookup.set(lookupKey, e.id);
    }
    entryIdLookup.set(`source:${e.id}`, e.id);
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
    if (rowType === 'metric') {
      const categoryName = String(row.Category || '').trim().toLowerCase();
      const targetCategory = categoryName ? await getOrCreateCategory(categoryName) : null;
      let metric = await getMetricByName(String(row.Metric || '').trim().toLowerCase());
      if (!metric) {
        const unitType = String(row.Type || 'float').trim().toLowerCase();
        metric = await createMetric({
          name: row.Metric,
          description: String(row.Description || '').trim() || null,
          unitName: String(row.Unit || '').trim() || null,
          unitType,
          metricKind: String(row.Kind || '').trim().toLowerCase()
            || (unitType === 'integer_range' ? 'score' : unitType === 'integer' ? 'count' : 'quantitative'),
          rangeStart: coerceNumber(row.Min),
          rangeEnd: coerceNumber(row.Max),
          higherIsBetter: row.HigherIsBetter === '' ? true : toBoolean(row.HigherIsBetter),
          isArchived: toBoolean(row.Archived),
          categoryId: targetCategory?.id || null,
        });
        imported.metrics += 1;
      }
      if (row.RecordId) metricIdLookup.set(row.RecordId, metric.id);
      continue;
    }

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
      if (row.MetricId) metricIdLookup.set(row.MetricId, metric.id);

      const normalizedDate = normalizeDate(row.Date);
      const naiveKeys = getNaiveKeys(normalizedDate);
      const workoutSessionId = String(row.WorkoutSessionId || '').trim() || null;
      const entryLookupPrefix = `${metric.id}_${workoutSessionId || 'standalone'}_`;
      let isDuplicate = false;
      let duplicateId = null;
      for (const key of naiveKeys) {
        const lookupKey = `${entryLookupPrefix}${key}`;
        if (entryLookup.has(lookupKey)) {
          isDuplicate = true;
          duplicateId = entryIdLookup.get(lookupKey) || duplicateId;
          break;
        }
      }

      if (!isDuplicate) {
        const entry = await createEntry({
          metricId: metric.id,
          value: coerceNumber(row.Value),
          loadValue: coerceNumber(row.LoadValue) ?? coerceNumber(row.LoadKg),
          sets: parseSetsField(row.Sets).map((set) => ({
            ...set,
            ...(!Object.hasOwn(set, 'loadValue') && (Object.hasOwn(set, 'loadKg') || Object.hasOwn(set, 'load_kg'))
              ? { loadValue: set.loadKg ?? set.load_kg }
              : {}),
          })).map(({ loadKg, load_kg, ...set }) => set),
          targetAction: String(row.Target || '').trim() || null,
          recordedAt: normalizedDate,
          workoutSessionId,
          workoutPlanId: String(row.WorkoutPlanId || '').trim() || null,
        });
        for (const key of naiveKeys) {
          const lookupKey = `${entryLookupPrefix}${key}`;
          entryLookup.add(lookupKey);
          entryIdLookup.set(lookupKey, entry.id);
        }
        if (row.RecordId) entryIdLookup.set(`source:${row.RecordId}`, entry.id);
        imported.entries += 1;
      } else if (row.RecordId && duplicateId) {
        entryIdLookup.set(`source:${row.RecordId}`, duplicateId);
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

    if (rowType === 'workout_plan') {
      const source = parseWorkoutDataField(row.WorkoutData, 'workout plan');
      const sourceId = String(row.RecordId || source.id || '').trim();
      if (!sourceId) throw new Error('The CSV contains a workout plan without an ID.');
      if (knownPlanIds.has(sourceId)) continue;
      const currentMetrics = await listMetrics(true);
      const resolveMetricId = (sourceMetricId, name) => metricIdLookup.get(sourceMetricId)
        || currentMetrics.find((metric) => String(metric.name).toLowerCase() === String(name || '').toLowerCase())?.id
        || (currentMetrics.some((metric) => metric.id === sourceMetricId) ? sourceMetricId : '');
      const mapped = {
        ...source,
        id: sourceId,
        exercises: (source.exercises || []).map((exercise) => ({
          ...exercise,
          metricId: resolveMetricId(exercise.metricId, exercise.metricName),
        })),
        outcomeMetrics: (source.outcomeMetrics || []).map((outcome) => ({
          ...outcome,
          metricId: resolveMetricId(outcome.metricId, outcome.metricName),
        })),
      };
      const plan = validateWorkoutPlan(mapped);
      await putRecord(STORE_NAMES.workoutPlans, {
        ...plan,
        id: sourceId,
        isArchived: Boolean(source.isArchived),
        createdAt: source.createdAt || nowIso(),
        updatedAt: source.updatedAt || nowIso(),
      });
      knownPlanIds.add(sourceId);
      imported.workoutPlans += 1;
    }

    if (rowType === 'workout_session') {
      const source = parseWorkoutDataField(row.WorkoutData, 'workout session');
      const sourceId = String(row.RecordId || source.id || '').trim();
      if (!sourceId) throw new Error('The CSV contains a workout session without an ID.');
      if (knownSessionIds.has(sourceId)) continue;
      const exercises = (source.exercises || []).map((exercise) => ({
        ...exercise,
        entryId: entryIdLookup.get(`source:${exercise.entryId}`) || exercise.entryId,
        metricId: metricIdLookup.get(exercise.metricId) || exercise.metricId,
      }));
      const session = { ...source, id: sourceId, exercises };
      await putRecord(STORE_NAMES.workoutSessions, session);
      knownSessionIds.add(sourceId);
      imported.workoutSessions += 1;
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
  const [categories, metrics, entries, changeEvents, workoutPlans, workoutSessions] = await Promise.all([
    listCategories(),
    listMetrics(true),
    listEntries(),
    listChangeEvents(),
    getAll(STORE_NAMES.workoutPlans),
    getAll(STORE_NAMES.workoutSessions),
  ]);

  const categoryMap = Object.fromEntries(categories.map((category) => [category.id, category.name]));
  const metricMap = Object.fromEntries(metrics.map((metric) => [metric.id, metric]));
  const headers = [
    'RowType', 'Date', 'Category', 'Metric', 'Description', 'Archived', 'Value', 'Unit',
    'Type', 'Kind', 'Min', 'Max', 'HigherIsBetter', 'Target', 'LoadValue', 'Sets', 'Title',
    'Notes', 'EndDate', 'RecordId', 'MetricId', 'WorkoutSessionId', 'WorkoutPlanId', 'WorkoutData',
  ];
  const toRow = (values) => headers.map((header) => values[header] ?? '');
  const rows = [
    headers,
    ...metrics.map((metric) => toRow({
      RowType: 'metric',
      Category: categoryMap[metric.categoryId] || '',
      Metric: metric.name || '',
      Description: metric.description || '',
      Archived: Boolean(metric.isArchived),
      Unit: metric.unitName || '',
      Type: metric.unitType || '',
      Kind: metric.metricKind || '',
      Min: metric.rangeStart ?? '',
      Max: metric.rangeEnd ?? '',
      HigherIsBetter: metric.higherIsBetter ?? true,
      RecordId: metric.id,
    })),
    ...entries.map((entry) => {
      const metric = metricMap[entry.metricId] || {};
      return toRow({
        RowType: 'entry',
        Date: entry.recordedAt,
        Category: categoryMap[metric.categoryId] || '',
        Metric: metric.name || '',
        Description: metric.description || '',
        Archived: Boolean(metric.isArchived),
        Value: entry.value ?? '',
        Unit: metric.unitName || '',
        Type: metric.unitType || '',
        Kind: metric.metricKind || '',
        Min: metric.rangeStart ?? '',
        Max: metric.rangeEnd ?? '',
        HigherIsBetter: metric.higherIsBetter ?? true,
        Target: entry.targetAction ?? '',
        LoadValue: entry.loadValue ?? entry.loadKg ?? '',
        Sets: JSON.stringify(entry.sets || []),
        RecordId: entry.id,
        MetricId: entry.metricId,
        WorkoutSessionId: entry.workoutSessionId || '',
        WorkoutPlanId: entry.workoutPlanId || '',
      });
    }),
    ...changeEvents.map((event) => toRow({
      RowType: 'change',
      Date: event.recordedAt,
      Category: categoryMap[event.categoryId] || '',
      Archived: Boolean(event.isArchived),
      Title: event.title || '',
      Notes: event.notes || '',
      EndDate: event.endAt || '',
      RecordId: event.id,
    })),
    ...workoutPlans.map((plan) => toRow({
      RowType: 'workout_plan',
      RecordId: plan.id,
      WorkoutData: JSON.stringify({
        ...plan,
        exercises: plan.exercises.map((exercise) => ({
          ...exercise,
          metricName: metricMap[exercise.metricId]?.name || '',
        })),
        outcomeMetrics: (plan.outcomeMetrics || []).map((outcome) => ({
          ...outcome,
          metricName: metricMap[outcome.metricId]?.name || '',
        })),
      }),
    })),
    ...workoutSessions.map((session) => toRow({
      RowType: 'workout_session',
      RecordId: session.id,
      WorkoutData: JSON.stringify(session),
    })),
  ];

  return rows
    .map((row) => row.map((cell) => `"${String(cell ?? '').replaceAll('"', '""')}"`).join(','))
    .join('\n');
}
