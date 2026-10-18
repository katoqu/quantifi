import assert from 'node:assert/strict';
import test from 'node:test';

const stores = new Map();
for (const storeName of ['categories', 'metrics', 'entries', 'changeEvents']) {
  stores.set(storeName, new Map());
}

globalThis.indexedDB = {
  open() {
    const request = {};
    queueMicrotask(() => {
      const database = {
        objectStoreNames: { contains: () => true },
        transaction(storeName) {
          const transaction = {
            objectStore(name) {
              if (!stores.has(name)) stores.set(name, new Map());
              const records = stores.get(name);
              return {
                get(id) {
                  return createRequest(() => records.get(id) || null);
                },
                getAll() {
                  return createRequest(() => [...records.values()]);
                },
                delete(id) {
                  return createRequest(() => records.delete(id));
                },
                put(record) {
                  return createRequest(() => {
                    records.set(record.id, record);
                    return record.id;
                  });
                },
              };
            },
          };
          setTimeout(() => transaction.oncomplete?.(), 0);
          return transaction;
        },
      };
      request.result = database;
      const upgradeTransaction = {
        objectStore(name) {
          if (!stores.has(name)) stores.set(name, new Map());
          const records = stores.get(name);
          return {
            openCursor() {
              const cursorRequest = {};
              const rows = [...records.entries()];
              let index = 0;
              const continueCursor = () => queueMicrotask(() => {
                if (index >= rows.length) {
                  cursorRequest.result = null;
                  cursorRequest.onsuccess?.();
                  request.onsuccess?.();
                  return;
                }
                const [id, value] = rows[index];
                cursorRequest.result = {
                  value,
                  update(record) {
                    records.set(id, record);
                  },
                  continue() {
                    index += 1;
                    continueCursor();
                  },
                };
                cursorRequest.onsuccess?.();
              });
              continueCursor();
              return cursorRequest;
            },
          };
        },
      };
      request.transaction = upgradeTransaction;
      request.onupgradeneeded?.({ target: { result: database }, oldVersion: 2 });
    });
    return request;
  },
};

function createRequest(operation) {
  const request = {};
  queueMicrotask(() => {
    request.result = operation();
    request.onsuccess?.();
  });
  return request;
}

test('deletes archived metrics and their entries but refuses active metrics', async () => {
  stores.get('entries').set('legacy-load', {
    id: 'legacy-load',
    metricId: 'legacy-metric',
    loadKg: 72.5,
    sets: [{ loadKg: 72.5, reps: 8 }],
  });
  const { deleteMetric, STORE_NAMES } = await import('./db.js');
  const { listEntries } = await import('./db.js');
  const [migratedEntry] = await listEntries();
  assert.equal(migratedEntry.loadValue, 72.5);
  assert.equal(Object.hasOwn(migratedEntry, 'loadKg'), false);
  assert.deepEqual(migratedEntry.sets, [{ loadValue: 72.5, reps: 8 }]);
  const metricStore = stores.get(STORE_NAMES.metrics);
  const entryStore = stores.get(STORE_NAMES.entries);

  metricStore.set('active', { id: 'active', isArchived: false });
  entryStore.set('active-entry', { id: 'active-entry', metricId: 'active' });

  await assert.rejects(deleteMetric('active'), /Only archived metrics can be deleted/);
  assert.equal(metricStore.has('active'), true);
  assert.equal(entryStore.has('active-entry'), true);

  metricStore.set('archived', { id: 'archived', isArchived: true });
  entryStore.set('archived-entry', { id: 'archived-entry', metricId: 'archived' });
  entryStore.set('unrelated-entry', { id: 'unrelated-entry', metricId: 'other' });

  await deleteMetric('archived');
  assert.equal(metricStore.has('archived'), false);
  assert.equal(entryStore.has('archived-entry'), false);
  assert.equal(entryStore.has('unrelated-entry'), true);
});

test('saves grouped workout entries and includes plans and sessions in CSV backups', async () => {
  for (const records of stores.values()) records.clear();
  const [
    { createMetric, exportDataAsCsv, importCsvText, listEntries },
    { listWorkoutPlans, listWorkoutSessions, saveWorkoutPlan, saveWorkoutSession },
  ] = await Promise.all([
    import('./db.js'),
    import('./workout-data.js'),
  ]);
  const bench = await createMetric({ name: 'workout-test-bench', metricKind: 'strength_session' });
  const row = await createMetric({ name: 'workout-test-weight', metricKind: 'quantitative' });
  const plan = await saveWorkoutPlan({
    name: 'Workout test plan',
    exercises: [{ metricId: bench.id, targetSets: 3, targetReps: 8 }],
    outcomeMetrics: [{ metricId: row.id, direction: 'decrease' }],
  });

  const session = await saveWorkoutSession(plan, {
    recordedAt: '2026-10-11T10:00:00.000Z',
    exercises: [{
      metricId: bench.id,
      metricName: bench.name,
      sets: [{ loadValue: 50, reps: 8 }, { loadValue: 52.5, reps: 7 }],
    }],
  });

  const entries = await listEntries();
  const exerciseEntry = entries.find((entry) => entry.workoutSessionId === session.id);
  assert.ok(exerciseEntry);
  assert.equal(exerciseEntry.metricId, bench.id);
  assert.equal(exerciseEntry.sets.length, 2);
  assert.deepEqual(exerciseEntry.sets, [{ loadValue: 50, reps: 8 }, { loadValue: 52.5, reps: 7 }]);

  const csv = await exportDataAsCsv();
  assert.match(csv, /workout_plan/);
  assert.match(csv, /workout_session/);
  assert.match(csv, /WorkoutSessionId/);
  assert.match(csv, /LoadValue/);
  assert.doesNotMatch(csv.split('\n')[0], /LoadKg/);
  const imported = await importCsvText(csv);
  assert.equal(imported.workoutPlans, 0);
  assert.equal(imported.workoutSessions, 0);

  const legacyCsv = [
    'RowType,Date,Metric,Kind,Unit,Value,LoadKg,Sets,RecordId,MetricId',
    'metric,,legacy-csv-strength,strength_session,lb,,,,legacy-csv-metric,',
    'entry,2026-10-12T10:00:00.000Z,legacy-csv-strength,strength_session,lb,50,50,"[{""loadKg"":50,""reps"":8}]",legacy-csv-entry,legacy-csv-metric',
  ].join('\n');
  const legacyImport = await importCsvText(legacyCsv);
  assert.equal(legacyImport.entries, 1);
  const legacyEntry = (await listEntries()).find((entry) => entry.id !== exerciseEntry.id);
  assert.deepEqual(legacyEntry.sets, [{ loadValue: 50, reps: 8 }]);
  assert.equal(legacyEntry.loadValue, 50);

  for (const records of stores.values()) records.clear();
  const restored = await importCsvText(csv);
  assert.equal(restored.metrics, 2);
  assert.equal(restored.entries, 1);
  assert.equal(restored.workoutPlans, 1);
  assert.equal(restored.workoutSessions, 1);
  const [restoredPlan] = await listWorkoutPlans();
  const [restoredSession] = await listWorkoutSessions();
  const [restoredEntry] = await listEntries();
  assert.equal(restoredPlan.exercises[0].metricId, restoredEntry.metricId);
  assert.equal(restoredSession.exercises[0].entryId, restoredEntry.id);
  assert.equal(restoredEntry.workoutSessionId, restoredSession.id);
  assert.deepEqual(restoredEntry.sets, [{ loadValue: 50, reps: 8 }, { loadValue: 52.5, reps: 7 }]);
});

test('saves duration sets with optional added load and exports their metric measure', async () => {
  for (const records of stores.values()) records.clear();
  const [
    { createMetric, exportDataAsCsv, listEntries },
    { saveWorkoutPlan, saveWorkoutSession },
  ] = await Promise.all([
    import('./db.js'),
    import('./workout-data.js'),
  ]);
  const plank = await createMetric({
    name: 'workout-test-plank',
    metricKind: 'strength_session',
    strengthMeasure: 'duration',
    unitName: 'lb',
  });
  const plan = await saveWorkoutPlan({
    name: 'Timed core',
    exercises: [{
      metricId: plank.id,
      targetSets: 3,
      strengthMeasure: 'duration',
      targetDurationSeconds: 30,
    }],
  });
  await saveWorkoutSession(plan, {
    recordedAt: '2026-10-12T10:00:00.000Z',
    exercises: [{
      metricId: plank.id,
      metricName: plank.name,
      sets: [{ durationSeconds: 30 }, { durationSeconds: 25, loadValue: 5 }],
    }],
  });
  const [entry] = await listEntries();
  assert.deepEqual(entry.sets, [{ durationSeconds: 30 }, { loadValue: 5, durationSeconds: 25 }]);
  assert.equal(entry.value, 30);
  const csv = await exportDataAsCsv();
  assert.match(csv, /StrengthMeasure/);
  assert.match(csv, /duration/);
});
