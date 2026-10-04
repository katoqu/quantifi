import assert from 'node:assert/strict';
import test from 'node:test';

import {
  filterMetricsBySearch,
  filterMetricsByView,
  getRecentMetricIds,
} from './metric-filters.js';

const metrics = [
  { id: 'water', name: 'water', categoryId: 'general', isArchived: false },
  { id: 'mood', name: 'mood', categoryId: 'health', isArchived: false },
  { id: 'sleep', name: 'sleep', categoryId: 'health', isArchived: true },
];

const categories = [
  { id: 'general', name: 'general' },
  { id: 'health', name: 'health' },
];

test('orders recent metrics by latest entry, then alphabetically', () => {
  const entries = [
    { metricId: 'mood', recordedAt: '2026-05-01T10:00:00Z' },
    { metricId: 'water', recordedAt: '2026-05-03T10:00:00Z' },
    { metricId: 'mood', recordedAt: '2026-05-04T10:00:00Z' },
  ];

  assert.deepEqual(getRecentMetricIds(entries, 2), ['mood', 'water']);
  assert.deepEqual(
    filterMetricsByView('Recent', metrics, entries, categories).map((metric) => metric.id),
    ['mood', 'water', 'sleep']
  );
});

test('sorts alphabetically when there are no recent entries', () => {
  assert.deepEqual(
    filterMetricsByView('Recent', metrics, [], categories).map((metric) => metric.id),
    ['mood', 'sleep', 'water']
  );
});

test('filters metrics by category name without changing their order', () => {
  assert.deepEqual(
    filterMetricsByView('HEALTH', metrics, [], categories).map((metric) => metric.id),
    ['mood', 'sleep']
  );
  assert.deepEqual(filterMetricsByView('missing', metrics, [], categories), []);
});

test('searches metric names and category names case-insensitively', () => {
  assert.deepEqual(
    filterMetricsBySearch(metrics, categories, 'WAT').map((metric) => metric.id),
    ['water']
  );
  assert.deepEqual(
    filterMetricsBySearch(metrics, categories, 'health').map((metric) => metric.id),
    ['mood', 'sleep']
  );
});

test('a leading hash limits search to archived metrics', () => {
  assert.deepEqual(
    filterMetricsBySearch(metrics, categories, '#').map((metric) => metric.id),
    ['sleep']
  );
  assert.deepEqual(
    filterMetricsBySearch(metrics, categories, '# SLE').map((metric) => metric.id),
    ['sleep']
  );
});
