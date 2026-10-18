import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildStrengthProgressRecommendation,
  computeDurationValue,
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
      loadValue: 70,
      sets: [{ loadValue: 60, reps: 8 }, { loadValue: 70, reps: 5 }],
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
    { loadValue: 45, reps: 6 }
  );
  assert.deepEqual(getLastStrengthSet({ value: '35', reps: '10' }), {
    loadValue: 35,
    reps: 10,
  });
});

test('recommends a rounded load increase after a 12-rep final set', () => {
  assert.equal(
    buildStrengthProgressRecommendation([{
      sets: [{ loadKg: 50, reps: 12 }],
    }], 'lb'),
    'Try increasing your last set by +2.50 lb (about 5%).'
  );
  assert.equal(
    buildStrengthProgressRecommendation([{
      sets: [{ loadKg: 50, reps: 12 }],
    }]),
    'Try increasing your last set by +2.50 kg (about 5%).'
  );
});

test('formats strength load using the metric unit', () => {
  assert.equal(
    formatStrengthSession({ sets: [{ loadValue: 70, reps: 8 }] }, 'lb'),
    '70.0 lb × 8 reps × 1 sets'
  );
});

test('computes and formats timed strength sessions without applying load aggregates', () => {
  const entry = { value: 30, sets: [{ durationSeconds: 25 }, { durationSeconds: 30, loadValue: 5 }] };
  assert.equal(computeDurationValue(entry, 'Max Duration'), 30);
  assert.equal(computeDurationValue(entry, 'Total Duration'), 55);
  assert.equal(formatStrengthSession(entry), '25 sec hold · 30 sec hold + 5 kg');
  assert.equal(formatStrengthSession({ value: 30 }, 'lb', 'duration'), '30 sec');
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
