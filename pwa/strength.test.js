import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildStrengthProgressRecommendation,
  computeStrengthValue,
  formatStrengthSession,
  getLastStrengthSet,
} from './strength.js';

test('computes strength aggregates from sets', () => {
  const entry = {
    sets: [
      { loadKg: 60, reps: 8 },
      { loadKg: 70, reps: 5 },
    ],
  };

  assert.equal(computeStrengthValue(entry, 'Total Volume'), 830);
  assert.equal(computeStrengthValue(entry, 'Max Load'), 70);
  assert.equal(computeStrengthValue(entry, 'Average Load'), 65);
  assert.equal(computeStrengthValue(entry, 'Max e1RM'), 70 * (1 + 5 / 30));
});

test('accepts legacy set load field and defaults missing repetitions', () => {
  assert.equal(
    computeStrengthValue({ sets: [{ load_kg: '50' }] }, 'Total Volume'),
    500
  );
});

test('formats strength sessions with sets', () => {
  assert.equal(
    formatStrengthSession({
      loadKg: 70,
      sets: [{ loadKg: 60, reps: 8 }, { loadKg: 70, reps: 5 }],
    }),
    '70.0 kg × 8/5 reps × 2 sets'
  );
});

test('formats legacy strength entries and missing entries', () => {
  assert.equal(formatStrengthSession({ value: 42 }), '42.0 kg');
  assert.equal(formatStrengthSession({ value: null }), '—');
  assert.equal(formatStrengthSession(null), '—');
});

test('uses the legacy entry value when an entry has no sets', () => {
  const entry = { value: '40' };

  assert.equal(computeStrengthValue(entry, 'Total Volume'), 1200);
  assert.equal(computeStrengthValue(entry, 'Max Load'), 40);
  assert.equal(computeStrengthValue(entry, 'Max e1RM'), 80);
});

test('gets the final set, with legacy entry fields as fallback', () => {
  assert.deepEqual(
    getLastStrengthSet({
      sets: [{ loadKg: 40, reps: 8 }, { load_kg: '45', reps: '6' }],
    }),
    { loadKg: 45, reps: 6 }
  );
  assert.deepEqual(getLastStrengthSet({ value: '35', reps: '10' }), {
    loadKg: 35,
    reps: 10,
  });
});

test('recommends a rounded load increase after a 12-rep final set', () => {
  assert.equal(
    buildStrengthProgressRecommendation([{
      sets: [{ loadKg: 50, reps: 12 }],
    }]),
    'Try increasing your last set by +2.50 kg (about 5%).'
  );
});

test('recommends extra repetitions after four unchanged sessions', () => {
  const entries = Array.from({ length: 4 }, () => ({
    sets: [{ loadKg: 60, reps: 8 }],
  }));

  assert.equal(
    buildStrengthProgressRecommendation(entries),
    'Your last set load and reps have been the same for 4 sessions. Try adding 2 more reps to the last set.'
  );
  assert.equal(buildStrengthProgressRecommendation(entries.slice(0, 3)), null);
});

test('does not recommend progression for an empty session list', () => {
  assert.equal(buildStrengthProgressRecommendation([]), null);
  assert.equal(buildStrengthProgressRecommendation(null), null);
});
