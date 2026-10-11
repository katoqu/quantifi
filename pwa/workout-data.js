import { nowIso, openDb, uid } from './db.js';
import { validateWorkoutPlan } from './workout-model.js';
import { normalizeStrengthSet } from './strength-set-editor.js';

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

export async function saveWorkoutSession(plan, { recordedAt, exercises }) {
  if (!plan?.id) throw new Error('Choose a saved workout plan.');
  if (!recordedAt || Number.isNaN(new Date(recordedAt).getTime())) {
    throw new Error('Choose a valid workout date and time.');
  }
  if (!Array.isArray(exercises) || exercises.length !== plan.exercises.length) {
    throw new Error('Every exercise in the plan must be included in the workout.');
  }

  const sessionId = uid();
  const createdAt = nowIso();
  const exerciseEntries = exercises.map((exercise, index) => {
    const planned = plan.exercises[index];
    if (exercise.metricId !== planned.metricId || !Array.isArray(exercise.sets) || !exercise.sets.length) {
      throw new Error('Add at least one valid set for every exercise.');
    }
    const sets = exercise.sets.map((set) => normalizeStrengthSet(set.loadKg ?? set.load_kg, set.reps));
    const entryId = uid();
    return {
      entry: {
        id: entryId,
        metricId: planned.metricId,
        value: sets[0].loadKg,
        loadKg: sets[0].loadKg,
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
        targetSets: planned.targetSets,
        targetReps: planned.targetReps,
      },
    };
  });

  const session = {
    id: sessionId,
    planId: plan.id,
    planName: plan.name,
    recordedAt,
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
