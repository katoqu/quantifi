import { getStartDateForPeriod } from './stats.js';

export const NUTRIENTS = [
  { id: 'calories', key: 'calories', label: 'Calories', name: 'calories', unit: 'kcal', decimals: 0 },
  { id: 'protein', key: 'protein_g', label: 'Protein', name: 'protein', unit: 'g', decimals: 1 },
  { id: 'carbs', key: 'carbs_g', label: 'Carbs', name: 'carbs', unit: 'g', decimals: 1, aliases: ['carbohydrates'] },
  { id: 'fat', key: 'fat_g', label: 'Fat', name: 'fat', unit: 'g', decimals: 1 },
  { id: 'saturated_fat', key: 'saturated_fat_g', label: 'Saturated fat', name: 'saturated fat', unit: 'g', decimals: 1 },
  { id: 'fiber', key: 'fiber_g', label: 'Fiber', name: 'fiber', unit: 'g', decimals: 1 },
  { id: 'vegetables', key: 'vegetables_g', label: 'Vegetables', name: 'vegetables', unit: 'g', decimals: 1 },
];

export const RESERVED_NUTRITION_METRIC_NAMES = new Set(
  NUTRIENTS.flatMap((nutrient) => [
    nutrient.id,
    nutrient.key,
    nutrient.label,
    nutrient.name,
    ...(nutrient.aliases || []),
  ].map((name) => String(name).trim().toLowerCase()))
);

export const NUTRITION_PREVIEW_LIMIT = 30;

export const NUTRITION_TARGET_TYPES = [
  { id: 'minimum', label: 'At least' },
  { id: 'maximum', label: 'At most' },
  { id: 'range', label: 'Between' },
];

export function normalizeNutritionTarget(target) {
  if (!target || typeof target !== 'object' || Array.isArray(target)) {
    throw new Error('A nutrition target must be an object.');
  }
  const nutrient = NUTRIENTS.find((item) => item.id === target.nutrientId);
  if (!nutrient) throw new Error('Choose a supported nutrition value for the target.');
  const effectiveFrom = String(target.effectiveFrom || '');
  if (!isValidDate(effectiveFrom)) {
    throw new Error(`Invalid target start date: "${effectiveFrom}". Use YYYY-MM-DD.`);
  }
  const type = String(target.type || '');
  if (!NUTRITION_TARGET_TYPES.some((item) => item.id === type)) {
    throw new Error('Choose whether the target is a minimum, maximum, or range.');
  }

  const value = target.value === '' || target.value === undefined ? null : target.value;
  const minValue = target.minValue === '' || target.minValue === undefined ? null : target.minValue;
  const maxValue = target.maxValue === '' || target.maxValue === undefined ? null : target.maxValue;
  const isValidValue = (number) => typeof number === 'number' && Number.isFinite(number) && number >= 0;
  if (type === 'minimum' && !isValidValue(value)) throw new Error('Enter a non-negative minimum target.');
  if (type === 'maximum' && !isValidValue(value)) throw new Error('Enter a non-negative maximum target.');
  if (type === 'range' && (!isValidValue(minValue) || !isValidValue(maxValue) || minValue > maxValue)) {
    throw new Error('Enter a valid range with the minimum no greater than the maximum.');
  }
  return {
    id: `${nutrient.id}-${effectiveFrom}`,
    nutrientId: nutrient.id,
    type,
    value: type === 'range' ? null : value,
    minValue: type === 'range' ? minValue : null,
    maxValue: type === 'range' ? maxValue : null,
    effectiveFrom,
    note: String(target.note || '').trim(),
  };
}

function isValidDate(date) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
  const parsed = new Date(`${date}T00:00:00.000Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === date;
}

export function normalizeNutritionDay(record) {
  if (!record || typeof record !== 'object' || Array.isArray(record)) {
    throw new Error('Each nutrition day must be an object.');
  }
  const date = String(record.date || '');
  if (!isValidDate(date)) throw new Error(`Invalid nutrition date: "${date}". Use YYYY-MM-DD.`);
  const sourceValues = record.values && typeof record.values === 'object' && !Array.isArray(record.values)
    ? record.values
    : record;
  const values = {};
  const unknownFields = [];

  for (const [key, value] of Object.entries(sourceValues)) {
    if (key === 'date' || key === 'values') continue;
    const nutrient = NUTRIENTS.find((item) => item.key === key || item.id === key);
    if (!nutrient) {
      unknownFields.push(key);
      continue;
    }
    if (value !== null && (typeof value !== 'number' || !Number.isFinite(value) || value < 0)) {
      throw new Error(`${key} for ${date} must be a non-negative number or null.`);
    }
    values[nutrient.id] = value;
  }

  for (const nutrient of NUTRIENTS) {
    if (!Object.hasOwn(values, nutrient.id)) values[nutrient.id] = null;
  }
  if (!NUTRIENTS.some((nutrient) => values[nutrient.id] !== null)) {
    throw new Error(`Nutrition day ${date} must include at least one numeric nutrient value.`);
  }
  return { date, values, unknownFields };
}

export function parseNutritionImportJson(text) {
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error('The nutrition file is not valid JSON.');
  }
  const days = Array.isArray(parsed) ? parsed : parsed?.days;
  if (!Array.isArray(days) || !days.length) {
    throw new Error('Use a JSON array of daily nutrition objects, or an object with a "days" array.');
  }

  const seenDates = new Set();
  const records = days.map((day) => {
    const normalized = normalizeNutritionDay(day);
    if (seenDates.has(normalized.date)) throw new Error(`The file contains more than one record for ${normalized.date}.`);
    seenDates.add(normalized.date);
    return normalized;
  });
  return {
    records,
    unknownFields: [...new Set(records.flatMap((record) => record.unknownFields))],
  };
}

export function getNutritionPreviewRecords(records, limit = NUTRITION_PREVIEW_LIMIT) {
  const previewRecords = records.slice(0, limit);
  return {
    records: previewRecords,
    omittedCount: records.length - previewRecords.length,
    totalCount: records.length,
  };
}

export function formatNutrientValue(value, nutrient) {
  if (value === null || value === undefined) return '—';
  return `${Number(value).toFixed(nutrient.decimals)} ${nutrient.unit}`;
}

export function formatNutritionTarget(target, nutrient) {
  if (!target) return 'No target set';
  if (target.type === 'minimum') return `At least ${formatNutrientValue(target.value, nutrient)}`;
  if (target.type === 'maximum') return `At most ${formatNutrientValue(target.value, nutrient)}`;
  return `${formatNutrientValue(target.minValue, nutrient)} – ${formatNutrientValue(target.maxValue, nutrient)}`;
}

export function filterNutritionDaysForPeriod(days, period, maxDate = new Date()) {
  const startDate = getStartDateForPeriod(period, maxDate);
  startDate.setHours(0, 0, 0, 0);
  const endDate = new Date(maxDate);
  endDate.setHours(23, 59, 59, 999);

  return days
    .filter((day) => {
      const date = new Date(`${day.date}T00:00:00`);
      return !Number.isNaN(date.getTime()) && date >= startDate && date <= endDate;
    })
    .sort((a, b) => a.date.localeCompare(b.date));
}
