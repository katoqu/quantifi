import assert from 'node:assert/strict';
import test from 'node:test';

import { summarizeWorkoutBlock, validateWorkoutPlan } from './workout-model.js';

test('validates plan exercises and optional outcome directions', () => {
  assert.deepEqual(validateWorkoutPlan({
    name: ' Upper A ',
    exercises: [{ metricId: 'bench', targetSets: '3', targetReps: '8' }],
    outcomeMetrics: [{ metricId: 'weight', direction: 'decrease' }],
  }), {
    name: 'Upper A',
    exercises: [{ metricId: 'bench', targetSets: 3, targetReps: 8 }],
    outcomeMetrics: [{ metricId: 'weight', direction: 'decrease' }],
  });
  assert.throws(() => validateWorkoutPlan({ name: '', exercises: [] }), /plan name/);
  assert.throws(() => validateWorkoutPlan({
    name: 'A',
    exercises: [
      { metricId: 'bench', targetSets: 3, targetReps: 8 },
      { metricId: 'bench', targetSets: 2, targetReps: 5 },
    ],
  }), /only once/);
  assert.throws(() => validateWorkoutPlan({
    name: 'A',
    exercises: [{ metricId: 'bench', targetSets: 3, targetReps: 8 }],
    outcomeMetrics: [
      { metricId: 'weight', direction: 'decrease' },
      { metricId: 'waist', direction: 'decrease' },
      { metricId: 'mood', direction: 'increase' },
    ],
  }), /no more than two/);
});

test('summarizes exercise progress and outcome trends within the selected block', () => {
  const summary = summarizeWorkoutBlock({
    plan: {
      id: 'upper-a',
      exercises: [{ metricId: 'bench' }],
      outcomeMetrics: [{ metricId: 'weight', direction: 'decrease' }],
    },
    sessions: [
      { id: 'outside', planId: 'upper-a', recordedAt: '2025-12-31T12:00:00Z' },
      { id: 'session-1', planId: 'upper-a', recordedAt: '2026-01-02T12:00:00Z' },
      { id: 'session-2', planId: 'upper-a', recordedAt: '2026-01-20T12:00:00Z' },
      { id: 'other-plan', planId: 'lower-b', recordedAt: '2026-01-25T12:00:00Z' },
    ],
    entries: [
      {
        workoutSessionId: 'session-1',
        metricId: 'bench',
        sets: [{ loadKg: 50, reps: 8 }],
      },
      {
        workoutSessionId: 'session-2',
        metricId: 'bench',
        sets: [{ loadKg: 55, reps: 8 }],
      },
      { metricId: 'weight', value: 80, recordedAt: '2026-01-03T08:00:00Z' },
      { metricId: 'weight', value: 78, recordedAt: '2026-01-29T08:00:00Z' },
      { metricId: 'weight', value: 79, recordedAt: '2026-02-01T08:00:00Z' },
    ],
    metrics: [{ id: 'weight', name: 'body weight' }],
    startAt: '2026-01-01T00:00:00Z',
    endAt: '2026-01-31T23:59:59Z',
  });

  assert.equal(summary.sessionsCompleted, 2);
  assert.equal(summary.exerciseProgress[0].sessions, 2);
  assert.equal(summary.exerciseProgress[0].change, (55 * (1 + 8 / 30)) - (50 * (1 + 8 / 30)));
  assert.deepEqual(summary.outcomeProgress[0], {
    metricId: 'weight',
    metricName: 'body weight',
    direction: 'decrease',
    firstValue: 80,
    latestValue: 78,
    progress: 'toward-goal',
  });
});

test('requires a valid block and reports insufficient outcome readings', () => {
  const input = {
    plan: {
      id: 'plan',
      exercises: [],
      outcomeMetrics: [{ metricId: 'mood', direction: 'increase' }],
    },
    sessions: [],
    entries: [{ metricId: 'mood', value: 3, recordedAt: '2026-01-10T12:00:00Z' }],
    metrics: [],
    startAt: '2026-01-01T00:00:00Z',
    endAt: '2026-01-31T23:59:59Z',
  };
  assert.equal(summarizeWorkoutBlock(input).outcomeProgress[0].progress, 'not-enough-data');
  assert.throws(
    () => summarizeWorkoutBlock({ ...input, startAt: 'bad-date' }),
    /valid workout block/
  );
});
