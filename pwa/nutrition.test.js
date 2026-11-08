import assert from 'node:assert/strict';
import test from 'node:test';
import {
  getNutritionPreviewRecords,
  normalizeNutritionDay,
  NUTRITION_PREVIEW_LIMIT,
  parseNutritionImportJson,
} from './nutrition.js';

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

test('rejects invalid dates, negative values, duplicate days, and empty records', () => {
  assert.throws(() => normalizeNutritionDay({ date: '2026-02-30', calories: 1 }), /Invalid nutrition date/);
  assert.throws(() => normalizeNutritionDay({ date: '2026-11-08', calories: -1 }), /non-negative number/);
  assert.throws(() => normalizeNutritionDay({ date: '2026-11-08' }), /at least one numeric/);
  assert.throws(() => parseNutritionImportJson(JSON.stringify([
    { date: '2026-11-08', calories: 1 },
    { date: '2026-11-08', calories: 2 },
  ])), /more than one record/);
});
