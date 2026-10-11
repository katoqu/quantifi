import assert from 'node:assert/strict';
import test from 'node:test';

import { normalizeStrengthSet } from './strength-set-editor.js';

test('normalizes valid strength sets and rejects invalid load or reps', () => {
  assert.deepEqual(normalizeStrengthSet('62.5', '8'), { loadKg: 62.5, reps: 8 });
  assert.throws(() => normalizeStrengthSet('', '8'), /valid load/);
  assert.throws(() => normalizeStrengthSet('50', '0'), /whole-number rep count/);
  assert.throws(() => normalizeStrengthSet('50', '8.5'), /whole-number rep count/);
});
