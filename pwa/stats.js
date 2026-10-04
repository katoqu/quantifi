import { computeStrengthValue } from './strength.js';

export function getStartDateForPeriod(period, maxDate) {
  const end = maxDate ? new Date(maxDate) : new Date();
  const start = new Date(end);
  if (period === 'Week') {
    start.setDate(end.getDate() - 7);
  } else if (period === 'Month') {
    start.setMonth(end.getMonth() - 1);
  } else if (period === '6M') {
    start.setMonth(end.getMonth() - 6);
  } else if (period === 'Year') {
    start.setFullYear(end.getFullYear() - 1);
  } else {
    return new Date(0);
  }
  return start;
}

export function resampleAndProcessData(entries, metric, period, zeros, strengthAgg) {
  const startDate = getStartDateForPeriod(period, new Date());
  const endDate = new Date();
  endDate.setHours(0, 0, 0, 0);
  const rows = entries
    .filter((entry) => entry.metricId === metric.id)
    .map((entry) => ({
      date: new Date(entry.recordedAt),
      entry,
    }))
    .filter((row) => !Number.isNaN(row.date.getTime()));

  const bucketMap = new Map();
  for (const { date, entry } of rows) {
    const day = new Date(date);
    day.setHours(0, 0, 0, 0);
    const key = day.toISOString();
    const value = metric.metricKind === 'strength_session'
      ? computeStrengthValue(entry, strengthAgg)
      : Number(entry.value);
    if (Number.isNaN(value)) continue;
    const existing = bucketMap.get(key);
    if (!existing || date > existing.recordedAt) {
      bucketMap.set(key, { date: new Date(day), recordedAt: date, value });
    }
  }

  const result = [];
  const cursor = new Date(startDate);
  cursor.setHours(0, 0, 0, 0);
  while (cursor <= endDate) {
    const key = cursor.toISOString();
    const bucket = bucketMap.get(key);
    if (bucket) {
      result.push({ date: bucket.date, value: bucket.value, dateStr: bucket.date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) });
    } else if (zeros) {
      result.push({ date: new Date(cursor), value: 0, dateStr: cursor.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) });
    }
    cursor.setDate(cursor.getDate() + 1);
  }
  return result;
}
