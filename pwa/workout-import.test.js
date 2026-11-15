import assert from 'node:assert/strict';
import test from 'node:test';

import { findWorkoutMetricMatches, parseWorkoutImportJson } from './workout-import.js';

const workoutFile = {
  format: 'quantifi-workout',
  version: 1,
  plan: {
    name: 'Upper A',
    exercises: [{
      key: 'bench',
      metric: {
        name: 'Barbell bench press',
        strengthMeasure: 'reps',
        unitName: 'kg',
        aliases: ['bench press'],
      },
      targetSets: 3,
      targetReps: 8,
    }, {
      key: 'plank',
      metric: { name: 'Plank', strengthMeasure: 'duration' },
      targetSets: 2,
      targetDurationSeconds: 30,
    }],
    outcomeMetrics: [{
      key: 'weight',
      metric: { name: 'Body weight', unitName: 'kg' },
      direction: 'decrease',
    }],
  },
};

test('parses versioned workout JSON into plan references and metric definitions', () => {
  const parsed = parseWorkoutImportJson(JSON.stringify(workoutFile));
  assert.deepEqual(parsed.plan, {
    name: 'Upper A',
    exercises: [
      {
        metricKey: 'bench',
        targetSets: 3,
        strengthMeasure: 'reps',
        targetReps: 8,
      },
      {
        metricKey: 'plank',
        targetSets: 2,
        strengthMeasure: 'duration',
        targetDurationSeconds: 30,
      },
    ],
    outcomeMetrics: [{ metricKey: 'weight', direction: 'decrease' }],
  });
  assert.deepEqual(parsed.metrics.map(({ key, name, metricKind, strengthMeasure }) => ({
    key,
    name,
    metricKind,
    strengthMeasure,
  })), [
    { key: 'bench', name: 'Barbell bench press', metricKind: 'strength_session', strengthMeasure: 'reps' },
    { key: 'plank', name: 'Plank', metricKind: 'strength_session', strengthMeasure: 'duration' },
    { key: 'weight', name: 'Body weight', metricKind: 'quantitative', strengthMeasure: undefined },
  ]);
});

test('rejects unsupported versions, duplicate keys, and invalid exercise targets', () => {
  assert.throws(
    () => parseWorkoutImportJson(JSON.stringify({ ...workoutFile, version: 2 })),
    /version 1/
  );
  const duplicateKey = structuredClone(workoutFile);
  duplicateKey.plan.exercises[1].key = 'bench';
  assert.throws(() => parseWorkoutImportJson(JSON.stringify(duplicateKey)), /duplicate key/);
  const invalidDuration = structuredClone(workoutFile);
  invalidDuration.plan.exercises[1].targetDurationSeconds = 0;
  assert.throws(() => parseWorkoutImportJson(JSON.stringify(invalidDuration)), /positive number/);
  const mismatchedTarget = structuredClone(workoutFile);
  mismatchedTarget.plan.exercises[1].targetReps = 8;
  assert.throws(() => parseWorkoutImportJson(JSON.stringify(mismatchedTarget)), /must not include targetReps/);
});

test('suggests normalized exact aliases and similar names while identifying incompatible measures', () => {
  const [parsedDefinition] = parseWorkoutImportJson(JSON.stringify(workoutFile)).metrics;
  const matches = findWorkoutMetricMatches(parsedDefinition, [
    { id: 'exact', name: 'Bench Press', metricKind: 'strength_session', strengthMeasure: 'reps', unitName: 'kg' },
    { id: 'similar', name: 'Barbell Press', metricKind: 'strength_session', strengthMeasure: 'reps', unitName: 'kg' },
    { id: 'timed', name: 'Barbell Bench Press', metricKind: 'strength_session', strengthMeasure: 'duration' },
    { id: 'unrelated', name: 'Squat', metricKind: 'strength_session', strengthMeasure: 'reps' },
  ]);
  assert.deepEqual(matches.map(({ metric, exact }) => [metric.id, exact]), [
    ['exact', true],
    ['timed', true],
    ['similar', false],
  ]);
  assert.equal(matches[1].measureMismatch, true);
  assert.equal(matches[1].compatible, false);
  assert.equal(matches[0].unitMismatch, false);
});
