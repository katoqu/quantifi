import assert from 'node:assert/strict';
import test from 'node:test';
import {
  getNutritionPreviewRecords,
  filterNutritionDaysForPeriod,
  normalizeNutritionDay,
  NUTRITION_PREVIEW_LIMIT,
  normalizeNutritionTarget,
  parseNutritionImportJson,
} from './nutrition.js';

test('filters nutrition days by the selected period and returns them chronologically', () => {
  const days = [
    { date: '2026-11-15', values: {} },
    { date: '2026-11-07', values: {} },
    { date: '2026-11-08', values: {} },
    { date: '2026-11-16', values: {} },
  ];
  const endDate = new Date(2026, 10, 15, 12);

  assert.deepEqual(
    filterNutritionDaysForPeriod(days, 'Week', endDate).map((day) => day.date),
    ['2026-11-08', '2026-11-15']
  );
  assert.deepEqual(
    filterNutritionDaysForPeriod(days, 'All', endDate).map((day) => day.date),
    ['2026-11-07', '2026-11-08', '2026-11-15']
  );
});

test('parses a JSON array and fills unspecified nutrients with null', () => {
  const parsed = parseNutritionImportJson(JSON.stringify([
    { date: '2026-11-08', calories: 2140, protein_g: 142, carbs_g: 230, fat_g: 72 },
  ]));
  assert.equal(parsed.records.length, 1);
  assert.deepEqual(parsed.records[0].values, {
    calories: 2140,
    protein: 142,
    carbs: 230,
    fat: 72,
    saturated_fat: null,
    fiber: null,
    vegetables: null,
  });
  assert.deepEqual(parsed.unknownFields, []);
});

test('accepts a days wrapper and reports unknown fields without importing them', () => {
  const parsed = parseNutritionImportJson(JSON.stringify({
    days: [{ date: '2026-11-08', calories: 2000, salt_g: 5 }],
  }));
  assert.deepEqual(parsed.unknownFields, ['salt_g']);
  assert.equal(parsed.records[0].values.calories, 2000);
});

test('normalizes daily vegetable intake in grams', () => {
  const parsed = parseNutritionImportJson(JSON.stringify([
    { date: '2026-11-08', vegetables_g: 400 },
  ]));
  assert.equal(parsed.records[0].values.vegetables, 400);
  assert.deepEqual(parsed.unknownFields, []);
});

test('limits preview to 30 days while retaining the full import count', () => {
  const records = Array.from({ length: 42 }, (_, index) => ({ date: `2026-01-${String(index + 1).padStart(2, '0')}` }));
  const preview = getNutritionPreviewRecords(records);
  assert.equal(NUTRITION_PREVIEW_LIMIT, 30);
  assert.equal(preview.records.length, 30);
  assert.equal(preview.omittedCount, 12);
  assert.equal(preview.totalCount, 42);
  assert.equal(preview.records[0], records[0]);
  assert.equal(preview.records.at(-1), records[29]);
});

test('normalizes nutrition targets and rejects invalid range values', () => {
  const target = normalizeNutritionTarget({
    nutrientId: 'calories',
    type: 'range',
    minValue: 1800,
    maxValue: 2200,
    effectiveFrom: '2026-11-08',
    note: '  Training day  ',
  });
  assert.equal(target.id, 'calories-2026-11-08');
  assert.equal(target.note, 'Training day');
  assert.throws(() => normalizeNutritionTarget({
    nutrientId: 'protein',
    type: 'range',
    minValue: 150,
    maxValue: 100,
    effectiveFrom: '2026-11-08',
  }), /minimum no greater than the maximum/);
  assert.throws(() => normalizeNutritionTarget({
    nutrientId: 'unknown',
    type: 'minimum',
    value: 1,
    effectiveFrom: '2026-11-08',
  }), /supported nutrition value/);
});

test('rejects invalid dates, negative values, duplicate days, and empty records', () => {
  assert.throws(() => normalizeNutritionDay({ date: '2026-02-30', calories: 1 }), /Invalid nutrition date/);
  assert.throws(() => normalizeNutritionDay({ date: '2026-11-08', calories: -1 }), /non-negative number/);
  assert.throws(() => normalizeNutritionDay({ date: '2026-11-08' }), /at least one numeric/);
  assert.throws(() => parseNutritionImportJson(JSON.stringify([
    { date: '2026-11-08', calories: 1 },
    { date: '2026-11-08', calories: 2 },
  ])), /more than one record/);
});
