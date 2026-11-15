const FORMAT_NAME = 'quantifi-workout';
const FORMAT_VERSION = 1;
const MAX_ALIASES = 20;

function normalizeName(value) {
  return String(value || '')
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function readName(value, label) {
  if (typeof value !== 'string') throw new Error(`The workout file is missing ${label}.`);
  const name = value.trim();
  if (!name) throw new Error(`The workout file is missing ${label}.`);
  if (name.length > 120) throw new Error(`${label} must be 120 characters or fewer.`);
  return name;
}

function readKey(value, label, keys) {
  if (typeof value !== 'string') throw new Error(`The workout file is missing a key for ${label}.`);
  const key = value.trim();
  if (!key) throw new Error(`The workout file is missing a key for ${label}.`);
  if (key.length > 80) throw new Error(`The key for ${label} must be 80 characters or fewer.`);
  if (keys.has(key)) throw new Error(`The workout file contains a duplicate key: "${key}".`);
  keys.add(key);
  return key;
}

function readAliases(value, label) {
  if (value === undefined) return [];
  if (!Array.isArray(value)) throw new Error(`Aliases for ${label} must be a list of names.`);
  if (value.length > MAX_ALIASES) throw new Error(`Use no more than ${MAX_ALIASES} aliases for ${label}.`);
  return [...new Set(value.map((alias) => readName(alias, `an alias for ${label}`)))];
}

function readUnitName(value, label) {
  if (value === undefined || value === null || value === '') return null;
  if (typeof value !== 'string') throw new Error(`The unit for ${label} must be a name.`);
  const unitName = value.trim();
  if (!unitName) return null;
  if (unitName.length > 40) throw new Error(`The unit for ${label} must be 40 characters or fewer.`);
  return unitName;
}

function readPositiveNumber(value, label, integer = false) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0
    || (integer && !Number.isInteger(value))) {
    throw new Error(`${label} must be a ${integer ? 'positive whole number' : 'positive number'}.`);
  }
  return value;
}

function normalizeExercise(exercise, index, keys, metricKeys) {
  const label = `exercise ${index + 1}`;
  if (!exercise || typeof exercise !== 'object' || Array.isArray(exercise)) {
    throw new Error(`The workout file contains an invalid ${label}.`);
  }
  const key = readKey(exercise.key, label, keys);
  const metric = exercise.metric;
  if (!metric || typeof metric !== 'object' || Array.isArray(metric)) {
    throw new Error(`The workout file is missing a metric definition for ${label}.`);
  }
  const name = readName(metric.name, `a metric name for ${label}`);
  const strengthMeasure = metric.strengthMeasure;
  if (!['reps', 'duration'].includes(strengthMeasure)) {
    throw new Error(`Choose "reps" or "duration" for the strength measure of ${name}.`);
  }
  const targetSets = readPositiveNumber(exercise.targetSets, `Target sets for ${name}`, true);
  const metricKey = readKey(key, `metric for ${label}`, metricKeys);
  const target = strengthMeasure === 'duration'
    ? { targetDurationSeconds: readPositiveNumber(exercise.targetDurationSeconds, `Target duration for ${name}`) }
    : { targetReps: readPositiveNumber(exercise.targetReps, `Target reps for ${name}`, true) };
  const forbiddenTarget = strengthMeasure === 'duration' ? 'targetReps' : 'targetDurationSeconds';
  if (Object.hasOwn(exercise, forbiddenTarget)) {
    throw new Error(`${name} must not include ${forbiddenTarget} for a ${strengthMeasure} target.`);
  }
  const definition = {
    key: metricKey,
    role: 'exercise',
    name,
    metricKind: 'strength_session',
    strengthMeasure,
    unitName: readUnitName(metric.unitName, name),
    aliases: readAliases(metric.aliases, name),
  };
  return {
    metricKey,
    targetSets,
    strengthMeasure,
    ...target,
    definition,
  };
}

function normalizeOutcome(outcome, index, keys, metricKeys) {
  const label = `outcome metric ${index + 1}`;
  if (!outcome || typeof outcome !== 'object' || Array.isArray(outcome)) {
    throw new Error(`The workout file contains an invalid ${label}.`);
  }
  const key = readKey(outcome.key, label, keys);
  const metric = outcome.metric;
  if (!metric || typeof metric !== 'object' || Array.isArray(metric)) {
    throw new Error(`The workout file is missing a metric definition for ${label}.`);
  }
  const name = readName(metric.name, `a metric name for ${label}`);
  const metricKey = readKey(key, `metric for ${label}`, metricKeys);
  const unitType = metric.unitType || 'float';
  if (!['float', 'integer', 'integer_range'].includes(unitType)) {
    throw new Error(`The unit type for ${name} must be float, integer, or integer_range.`);
  }
  const inferredMetricKind = unitType === 'integer_range'
    ? 'score'
    : unitType === 'integer' ? 'count' : 'quantitative';
  const metricKind = metric.metricKind || inferredMetricKind;
  if (!['quantitative', 'count', 'score'].includes(metricKind)) {
    throw new Error(`The metric kind for ${name} is not supported for workout outcomes.`);
  }
  if (outcome.direction !== 'increase' && outcome.direction !== 'decrease') {
    throw new Error(`Choose "increase" or "decrease" for the direction of ${name}.`);
  }
  const definition = {
    key: metricKey,
    role: 'outcome',
    name,
    metricKind,
    unitType,
    unitName: readUnitName(metric.unitName, name),
    aliases: readAliases(metric.aliases, name),
  };
  return { metricKey, direction: outcome.direction, definition };
}

export function parseWorkoutImportJson(text) {
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error('The workout file is not valid JSON.');
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('Use a Quantifi workout JSON object.');
  }
  if (parsed.format !== FORMAT_NAME || parsed.version !== FORMAT_VERSION) {
    throw new Error(`Use a "${FORMAT_NAME}" file with version ${FORMAT_VERSION}.`);
  }
  if (!parsed.plan || typeof parsed.plan !== 'object' || Array.isArray(parsed.plan)) {
    throw new Error('The workout file must contain a plan object.');
  }
  if (!Array.isArray(parsed.plan.exercises) || parsed.plan.exercises.length === 0) {
    throw new Error('The workout plan must include at least one exercise.');
  }
  const outcomeInputs = parsed.plan.outcomeMetrics ?? [];
  if (!Array.isArray(outcomeInputs)) throw new Error('Workout outcome metrics must be a list.');
  if (outcomeInputs.length > 2) throw new Error('A workout plan can include no more than two outcome metrics.');

  const keys = new Set();
  const metricKeys = new Set();
  const exercises = parsed.plan.exercises.map((exercise, index) => (
    normalizeExercise(exercise, index, keys, metricKeys)
  ));
  const outcomeMetrics = outcomeInputs.map((outcome, index) => (
    normalizeOutcome(outcome, index, keys, metricKeys)
  ));
  return {
    plan: {
      name: readName(parsed.plan.name, 'a plan name'),
      exercises: exercises.map(({ definition: _definition, ...exercise }) => exercise),
      outcomeMetrics: outcomeMetrics.map(({ definition: _definition, ...outcome }) => outcome),
    },
    metrics: [
      ...exercises.map((exercise) => exercise.definition),
      ...outcomeMetrics.map((outcome) => outcome.definition),
    ],
  };
}

function getMetricKind(metric) {
  if (metric.metricKind) return metric.metricKind;
  if (metric.unitType === 'integer_range') return 'score';
  if (metric.unitType === 'integer') return 'count';
  return 'quantitative';
}

function getNameSimilarity(first, second) {
  if (!first || !second) return 0;
  if (first === second) return 1;
  const firstTokens = new Set(first.split(' '));
  const secondTokens = new Set(second.split(' '));
  const shared = [...firstTokens].filter((token) => secondTokens.has(token)).length;
  if (!shared) return 0;
  const union = new Set([...firstTokens, ...secondTokens]).size;
  const smallest = Math.min(firstTokens.size, secondTokens.size);
  return (0.7 * shared / union) + (0.3 * shared / smallest);
}

export function findWorkoutMetricMatches(definition, metrics) {
  const importedNames = [definition.name, ...(definition.aliases || [])]
    .map(normalizeName)
    .filter(Boolean);
  return metrics.map((metric) => {
    const existingNames = [metric.name, ...(metric.aliases || [])]
      .map(normalizeName)
      .filter(Boolean);
    const exact = importedNames.some((name) => existingNames.includes(name));
    const similarity = importedNames.reduce((best, importedName) => Math.max(
      best,
      ...existingNames.map((existingName) => getNameSimilarity(importedName, existingName)),
    ), 0);
    const metricKindMismatch = getMetricKind(metric) !== definition.metricKind;
    const measureMismatch = definition.role === 'exercise'
      && (metric.strengthMeasure || 'reps') !== definition.strengthMeasure;
    const importedUnit = normalizeName(definition.unitName);
    const existingUnit = normalizeName(metric.unitName);
    const unitMismatch = Boolean(importedUnit && existingUnit && importedUnit !== existingUnit);
    return {
      metric,
      exact,
      similarity,
      compatible: !metricKindMismatch && !measureMismatch,
      unitMismatch,
      metricKindMismatch,
      measureMismatch,
    };
  })
    .filter((match) => match.exact || match.similarity >= 0.35)
    .sort((first, second) => Number(second.exact) - Number(first.exact)
      || Number(second.compatible) - Number(first.compatible)
      || second.similarity - first.similarity
      || first.metric.name.localeCompare(second.metric.name))
    .slice(0, 8);
}
