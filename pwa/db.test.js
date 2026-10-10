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
          if (!stores.has(storeName)) stores.set(storeName, new Map());
          const records = stores.get(storeName);
          return {
            objectStore() {
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
