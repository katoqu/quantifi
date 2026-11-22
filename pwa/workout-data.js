import { nowIso, openDb, uid } from './db.js';
import { validateWorkoutPlan } from './workout-model.js';
import { normalizeStrengthSet } from './strength-set-editor.js';
import { RESERVED_NUTRITION_METRIC_NAMES } from './nutrition.js';

function getMetricKind(metric) {
  if (metric.metricKind) return metric.metricKind;
  if (metric.unitType === 'integer_range') return 'score';
  if (metric.unitType === 'integer') return 'count';
  return 'quantitative';
}

export async function listWorkoutPlans({ includeArchived = false } = {}) {
  const database = await openDb();
  const request = database.transaction('workoutPlans').objectStore('workoutPlans').getAll();
  return new Promise((resolve, reject) => {
    request.onsuccess = () => {
      const plans = request.result || [];
      resolve(includeArchived ? plans : plans.filter((plan) => !plan.isArchived));
    };
    request.onerror = () => reject(request.error);
  });
}

export async function saveWorkoutPlan(payload) {
  const plan = validateWorkoutPlan(payload);
  const database = await openDb();
  const transaction = database.transaction('workoutPlans', 'readwrite');
  const store = transaction.objectStore('workoutPlans');
  const record = {
    ...plan,
    id: payload.id || uid(),
    isArchived: Boolean(payload.isArchived),
    createdAt: payload.createdAt || nowIso(),
    updatedAt: nowIso(),
  };
  return new Promise((resolve, reject) => {
    store.put(record);
    transaction.oncomplete = () => resolve(record);
    transaction.onerror = () => reject(transaction.error);
    transaction.onabort = () => reject(transaction.error || new Error('Could not save workout plan.'));
  });
}

export async function saveWorkoutPlanImport({ plan, metricDecisions }) {
  if (!Array.isArray(metricDecisions) || !metricDecisions.length) {
    throw new Error('Resolve the workout metrics before importing.');
  }
  const database = await openDb();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(['metrics', 'workoutPlans'], 'readwrite');
    const metricsStore = transaction.objectStore('metrics');
    const plansStore = transaction.objectStore('workoutPlans');
    let result;
    let failure;

    const request = metricsStore.getAll();
    request.onsuccess = () => {
      try {
        const existingMetrics = new Map((request.result || []).map((metric) => [metric.id, metric]));
        const metricIds = new Map();
        const metricsToCreate = [];
        const createdNames = new Set();
        for (const decision of metricDecisions) {
          if (!decision?.key || metricIds.has(decision.key)) {
            throw new Error('The workout file contains unresolved or duplicate metric keys.');
          }
          if (decision.metricId) {
            const existing = existingMetrics.get(decision.metricId);
            if (!existing || existing.isArchived) {
              throw new Error('A selected metric is no longer available. Review the metric matches and try again.');
            }
            const definition = decision.definition;
            if (getMetricKind(existing) !== definition.metricKind
              || (definition.role === 'exercise'
                && (existing.strengthMeasure || 'reps') !== definition.strengthMeasure)) {
              throw new Error(`"${existing.name}" is not compatible with the imported metric "${definition.name}".`);
            }
            metricIds.set(decision.key, existing.id);
            continue;
          }

          const definition = decision.definition;
          const name = String(definition?.name || '').trim().toLowerCase();
          if (!name) throw new Error('Imported metric names cannot be empty.');
          if (RESERVED_NUTRITION_METRIC_NAMES.has(name)) {
            throw new Error(`"${name}" is reserved for a nutrition metric and cannot be imported as a workout metric.`);
          }
          if (createdNames.has(name)) {
            throw new Error(`The import would create more than one metric named "${name}". Choose an existing metric for one of them.`);
          }
          createdNames.add(name);
          const id = uid();
          const record = {
            id,
            name,
            description: null,
            unitName: definition.unitName || null,
            unitType: definition.unitType || 'float',
            metricKind: definition.metricKind,
            ...(definition.role === 'exercise'
              ? { strengthMeasure: definition.strengthMeasure === 'duration' ? 'duration' : 'reps' }
              : {}),
            rangeStart: null,
            rangeEnd: null,
            higherIsBetter: true,
            isArchived: false,
            categoryId: null,
            aliases: definition.aliases || [],
            createdAt: nowIso(),
          };
          metricIds.set(decision.key, id);
          metricsToCreate.push(record);
        }

        const exercises = plan.exercises.map(({ metricKey, ...exercise }) => {
          const metricId = metricIds.get(metricKey);
          if (!metricId) throw new Error(`Resolve the imported exercise metric "${metricKey}".`);
          return { ...exercise, metricId };
        });
        const outcomeMetrics = plan.outcomeMetrics.map(({ metricKey, ...outcome }) => {
          const metricId = metricIds.get(metricKey);
          if (!metricId) throw new Error(`Resolve the imported outcome metric "${metricKey}".`);
          return { ...outcome, metricId };
        });
        const validated = validateWorkoutPlan({ ...plan, exercises, outcomeMetrics });
        const timestamp = nowIso();
        const savedPlan = {
          ...validated,
          id: uid(),
          isArchived: false,
          createdAt: timestamp,
          updatedAt: timestamp,
        };
        for (const metric of metricsToCreate) metricsStore.put(metric);
        plansStore.put(savedPlan);
        result = { plan: savedPlan, createdMetrics: metricsToCreate };
      } catch (error) {
        failure = error;
        try {
          transaction.abort();
        } catch {
          reject(error);
        }
      }
    };
    request.onerror = () => {
      failure = request.error || new Error('Could not read workout metrics.');
      try {
        transaction.abort();
      } catch {
        reject(failure);
      }
    };
    transaction.oncomplete = () => resolve(result);
    transaction.onerror = () => {
      failure ||= transaction.error || new Error('Could not import workout plan.');
    };
    transaction.onabort = () => reject(failure || transaction.error || new Error('Could not import workout plan.'));
  });
}

export async function archiveWorkoutPlan(planId) {
  const plans = await listWorkoutPlans({ includeArchived: true });
  const plan = plans.find((item) => item.id === planId);
  if (!plan) throw new Error('Workout plan not found.');
  return saveWorkoutPlan({ ...plan, isArchived: true });
}

export async function listWorkoutSessions() {
  const database = await openDb();
  const request = database.transaction('workoutSessions').objectStore('workoutSessions').getAll();
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result || []);
    request.onerror = () => reject(request.error);
  });
}

export async function saveWorkoutSession(plan, {
  recordedAt,
  startedAt,
  completedAt,
  durationSeconds: confirmedDurationSeconds,
  exercises,
}) {
  if (!plan?.id) throw new Error('Choose a saved workout plan.');
  if (!recordedAt || Number.isNaN(new Date(recordedAt).getTime())) {
    throw new Error('Workout date and time must be valid.');
  }
  if (!Array.isArray(exercises) || exercises.length !== plan.exercises.length) {
    throw new Error('Every exercise in the plan must be included in the workout.');
  }

  let measuredDurationSeconds;
  if (startedAt !== undefined || completedAt !== undefined) {
    const startTime = new Date(startedAt).getTime();
    const endTime = new Date(completedAt).getTime();
    if (!Number.isFinite(startTime) || !Number.isFinite(endTime) || endTime < startTime) {
      throw new Error('Workout start and finish times must be valid and in order.');
    }
    measuredDurationSeconds = Math.round((endTime - startTime) / 1000);
  }
  if (confirmedDurationSeconds !== undefined
    && (!Number.isFinite(confirmedDurationSeconds) || confirmedDurationSeconds < 0)) {
    throw new Error('Workout duration must be a non-negative number of seconds.');
  }
  const durationSeconds = confirmedDurationSeconds ?? measuredDurationSeconds;

  const sessionId = uid();
  const createdAt = nowIso();
  const exerciseEntries = exercises.map((exercise, index) => {
    const planned = plan.exercises[index];
    if (exercise.metricId !== planned.metricId || !Array.isArray(exercise.sets) || !exercise.sets.length) {
      throw new Error('Add at least one valid set for every exercise.');
    }
    const strengthMeasure = planned.strengthMeasure || 'reps';
    const sets = exercise.sets.map((set) => normalizeStrengthSet(
      set.loadValue ?? set.loadKg ?? set.load_kg,
      strengthMeasure === 'duration' ? set.durationSeconds : set.reps,
      strengthMeasure
    ));
    const skippedSets = Math.max(0, Number(planned.targetSets) - sets.length);
    if (exercise.skippedSets !== undefined && exercise.skippedSets !== skippedSets) {
      throw new Error('Skipped sets must match the remaining planned sets.');
    }
    const entryId = uid();
    const firstSetValue = strengthMeasure === 'duration'
      ? sets[0].durationSeconds
      : sets[0].loadValue;
    return {
      entry: {
        id: entryId,
        metricId: planned.metricId,
        value: firstSetValue,
        ...(sets[0].loadValue === undefined ? {} : { loadValue: sets[0].loadValue }),
        sets,
        targetAction: null,
        recordedAt,
        createdAt,
        workoutPlanId: plan.id,
        workoutSessionId: sessionId,
      },
      sessionExercise: {
        metricId: planned.metricId,
        metricName: String(exercise.metricName || ''),
        entryId,
        strengthMeasure,
        targetSets: planned.targetSets,
        skippedSets,
        ...(strengthMeasure === 'duration'
          ? { targetDurationSeconds: planned.targetDurationSeconds }
          : { targetReps: planned.targetReps }),
      },
    };
  });

  const session = {
    id: sessionId,
    planId: plan.id,
    planName: plan.name,
    recordedAt,
    ...(durationSeconds === undefined
      ? {}
      : {
        ...(startedAt === undefined ? {} : { startedAt, completedAt }),
        durationSeconds,
      }),
    exercises: exerciseEntries.map(({ sessionExercise }) => sessionExercise),
    createdAt,
  };

  const database = await openDb();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(['entries', 'workoutSessions'], 'readwrite');
    const entriesStore = transaction.objectStore('entries');
    const sessionsStore = transaction.objectStore('workoutSessions');
    for (const { entry } of exerciseEntries) entriesStore.put(entry);
    sessionsStore.put(session);
    transaction.oncomplete = () => resolve(session);
    transaction.onerror = () => reject(transaction.error);
    transaction.onabort = () => reject(transaction.error || new Error('Could not save workout session.'));
  });
}
