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
      request.result = {
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
      request.onsuccess?.();
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
  const { deleteMetric, STORE_NAMES } = await import('./db.js');
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
      sets: [{ loadKg: 50, reps: 8 }, { loadKg: 52.5, reps: 7 }],
    }],
  });

  const entries = await listEntries();
  const exerciseEntry = entries.find((entry) => entry.workoutSessionId === session.id);
  assert.ok(exerciseEntry);
  assert.equal(exerciseEntry.metricId, bench.id);
  assert.equal(exerciseEntry.sets.length, 2);

  const csv = await exportDataAsCsv();
  assert.match(csv, /workout_plan/);
  assert.match(csv, /workout_session/);
  assert.match(csv, /WorkoutSessionId/);
  const imported = await importCsvText(csv);
  assert.equal(imported.workoutPlans, 0);
  assert.equal(imported.workoutSessions, 0);

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
});
