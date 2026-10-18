import { computeStrengthValue } from './strength.js';

export function validateWorkoutPlan(plan) {
  const name = String(plan.name || '').trim();
  if (!name) throw new Error('Enter a workout plan name.');

  const exercises = Array.isArray(plan.exercises) ? plan.exercises : [];
  if (exercises.length === 0) throw new Error('Add at least one exercise.');

  const exerciseMetricIds = new Set();
  const normalizedExercises = exercises.map((exercise) => {
    const metricId = String(exercise.metricId || '').trim();
    const targetSets = Number(exercise.targetSets);
    const strengthMeasure = exercise.strengthMeasure === 'duration' ? 'duration' : 'reps';
    const targetValue = Number(strengthMeasure === 'duration'
      ? exercise.targetDurationSeconds
      : exercise.targetReps);
    if (!metricId) throw new Error('Choose a strength metric for every exercise.');
    if (exerciseMetricIds.has(metricId)) throw new Error('Add each strength metric only once to a plan.');
    if (!Number.isInteger(targetSets) || targetSets < 1) {
      throw new Error('Target sets must be a whole number greater than zero.');
    }
    if (!Number.isFinite(targetValue) || targetValue <= 0
      || (strengthMeasure === 'reps' && !Number.isInteger(targetValue))) {
      throw new Error(strengthMeasure === 'duration'
        ? 'Target duration must be greater than zero seconds.'
        : 'Target reps must be a whole number greater than zero.');
    }
    exerciseMetricIds.add(metricId);
    return strengthMeasure === 'duration'
      ? { metricId, targetSets, strengthMeasure, targetDurationSeconds: targetValue }
      : { metricId, targetSets, strengthMeasure, targetReps: targetValue };
  });

  const outcomeMetrics = Array.isArray(plan.outcomeMetrics) ? plan.outcomeMetrics : [];
  if (outcomeMetrics.length > 2) throw new Error('Link no more than two outcome metrics.');
  const outcomeMetricIds = new Set();
  const normalizedOutcomes = outcomeMetrics.map((outcome) => {
    const metricId = String(outcome.metricId || '').trim();
    const direction = outcome.direction;
    if (!metricId) throw new Error('Choose a metric for every workout outcome.');
    if (outcomeMetricIds.has(metricId)) throw new Error('Choose each outcome metric only once.');
    if (!['increase', 'decrease'].includes(direction)) {
      throw new Error('Choose whether each outcome metric should increase or decrease.');
    }
    outcomeMetricIds.add(metricId);
    return { metricId, direction };
  });

  return { name, exercises: normalizedExercises, outcomeMetrics: normalizedOutcomes };
}

function getEntryBestEstimatedOneRepMax(entry) {
  if (!Array.isArray(entry?.sets) || entry.sets.length === 0) return null;
  return computeStrengthValue(entry, 'Max e1RM');
}

function getEntryBestDuration(entry) {
  const durations = (entry?.sets || []).map((set) => Number(set.durationSeconds)).filter(Number.isFinite);
  return durations.length ? Math.max(...durations) : null;
}

function compareOutcomeValues(first, last, direction) {
  if (first === last) return 'unchanged';
  const increased = last > first;
  return increased === (direction === 'increase') ? 'toward-goal' : 'away-from-goal';
}

function getEntryNumericValue(entry) {
  if (entry.value === null || entry.value === undefined || entry.value === '') return null;
  const value = Number(entry.value);
  return Number.isFinite(value) ? value : null;
}

export function summarizeWorkoutBlock({ plan, sessions, entries, metrics, startAt, endAt }) {
  const start = new Date(startAt).getTime();
  const end = new Date(endAt).getTime();
  if (!Number.isFinite(start) || !Number.isFinite(end) || start > end) {
    throw new Error('Choose a valid workout block date range.');
  }

  const planExercises = Array.isArray(plan.exercises) ? plan.exercises : [];
  const planMetricIds = new Set(planExercises.map((exercise) => exercise.metricId));
  const includedSessions = sessions
    .filter((session) => session.planId === plan.id)
    .filter((session) => {
      const recordedAt = new Date(session.recordedAt).getTime();
      return Number.isFinite(recordedAt) && recordedAt >= start && recordedAt <= end;
    })
    .sort((a, b) => new Date(a.recordedAt) - new Date(b.recordedAt));
  const sessionEntryMap = new Map();
  for (const entry of entries) {
    if (!entry.workoutSessionId) continue;
    const group = sessionEntryMap.get(entry.workoutSessionId) || [];
    group.push(entry);
    sessionEntryMap.set(entry.workoutSessionId, group);
  }

  const exerciseProgress = planExercises.map((exercise) => {
    const readings = [];
    for (const session of includedSessions) {
      const matchingEntry = (sessionEntryMap.get(session.id) || [])
        .find((entry) => entry.metricId === exercise.metricId);
      const strengthMeasure = exercise.strengthMeasure || 'reps';
      const best = strengthMeasure === 'duration'
        ? getEntryBestDuration(matchingEntry)
        : getEntryBestEstimatedOneRepMax(matchingEntry);
      if (best !== null && Number.isFinite(best)) readings.push(best);
    }
    const first = readings[0] ?? null;
    const latest = readings.at(-1) ?? null;
    return {
      metricId: exercise.metricId,
      strengthMeasure: exercise.strengthMeasure || 'reps',
      sessions: readings.length,
      firstValue: first,
      latestValue: latest,
      change: readings.length < 2 ? null : latest - first,
    };
  });

  const metricMap = new Map(metrics.map((metric) => [metric.id, metric]));
  const outcomeProgress = (plan.outcomeMetrics || []).map((outcome) => {
    const readings = entries
      .filter((entry) => entry.metricId === outcome.metricId)
      .filter((entry) => {
        const recordedAt = new Date(entry.recordedAt).getTime();
        return Number.isFinite(recordedAt) && recordedAt >= start && recordedAt <= end;
      })
      .map((entry) => ({ recordedAt: new Date(entry.recordedAt).getTime(), value: getEntryNumericValue(entry) }))
      .filter((entry) => entry.value !== null)
      .sort((a, b) => a.recordedAt - b.recordedAt);
    const first = readings[0]?.value ?? null;
    const latest = readings.at(-1)?.value ?? null;
    return {
      metricId: outcome.metricId,
      metricName: metricMap.get(outcome.metricId)?.name || 'Unknown metric',
      direction: outcome.direction,
      firstValue: first,
      latestValue: latest,
      progress: readings.length < 2
        ? 'not-enough-data'
        : compareOutcomeValues(first, latest, outcome.direction),
    };
  });

  return {
    sessionsCompleted: includedSessions.length,
    exerciseProgress,
    outcomeProgress,
  };
}
