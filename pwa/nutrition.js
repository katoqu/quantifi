export const NUTRIENTS = [
  { id: 'calories', key: 'calories', label: 'Calories', name: 'calories', unit: 'kcal', decimals: 0 },
  { id: 'protein', key: 'protein_g', label: 'Protein', name: 'protein', unit: 'g', decimals: 1 },
  { id: 'carbs', key: 'carbs_g', label: 'Carbs', name: 'carbs', unit: 'g', decimals: 1, aliases: ['carbohydrates'] },
  { id: 'fat', key: 'fat_g', label: 'Fat', name: 'fat', unit: 'g', decimals: 1 },
  { id: 'saturated_fat', key: 'saturated_fat_g', label: 'Saturated fat', name: 'saturated fat', unit: 'g', decimals: 1 },
  { id: 'fiber', key: 'fiber_g', label: 'Fiber', name: 'fiber', unit: 'g', decimals: 1 },
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

export const SAMPLE_NUTRITION_JSON = JSON.stringify([
  { date: '2026-11-02', calories: 2050, protein_g: 132, carbs_g: 218, fat_g: 71, saturated_fat_g: 20, fiber_g: 27 },
  { date: '2026-11-03', calories: 2240, protein_g: 148, carbs_g: 241, fat_g: 76, saturated_fat_g: 22, fiber_g: 31 },
  { date: '2026-11-04', calories: 1925, protein_g: 121, carbs_g: 205, fat_g: 68, saturated_fat_g: 18, fiber_g: 25 },
  { date: '2026-11-05', calories: 2160, protein_g: 139, carbs_g: 229, fat_g: 74, saturated_fat_g: 21, fiber_g: 29 },
  { date: '2026-11-06', calories: 2310, protein_g: 154, carbs_g: 248, fat_g: 79, saturated_fat_g: 23, fiber_g: 32 },
  { date: '2026-11-07', calories: 1870, protein_g: 126, carbs_g: 192, fat_g: 66, saturated_fat_g: 17, fiber_g: 24 },
  { date: '2026-11-08', calories: 2115, protein_g: 143, carbs_g: 222, fat_g: 73, saturated_fat_g: 20, fiber_g: 30 },
], null, 2);

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
