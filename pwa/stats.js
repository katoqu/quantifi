import { computeDurationValue, computeStrengthValue } from './strength.js';

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

export function resampleAndProcessData(entries, metric, period, strengthAgg) {
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
    const rawValue = entry.value;
    const value = metric.metricKind === 'strength_session'
      ? (metric.strengthMeasure === 'duration'
        ? computeDurationValue(entry, strengthAgg)
        : computeStrengthValue(entry, strengthAgg))
      : rawValue === null || rawValue === undefined || (typeof rawValue === 'string' && !rawValue.trim())
        ? Number.NaN
        : Number(rawValue);
    if (!Number.isFinite(value)) continue;
    const existing = bucketMap.get(key);
    if (!existing || date > existing.recordedAt) {
      bucketMap.set(key, { date: new Date(day), recordedAt: date, value });
    }
  }

  if (!bucketMap.size) return [];

  const firstRecordedDate = [...bucketMap.values()]
    .reduce((earliest, bucket) => bucket.date < earliest ? bucket.date : earliest, endDate);
  const startDate = period === 'All'
    ? new Date(firstRecordedDate)
    : getStartDateForPeriod(period, new Date());
  startDate.setHours(0, 0, 0, 0);

  return [...bucketMap.values()]
    .filter((bucket) => bucket.date >= startDate && bucket.date <= endDate)
    .sort((first, second) => first.date - second.date)
    .map((bucket) => ({
      date: bucket.date,
      value: bucket.value,
      dateStr: bucket.date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }),
    }));
}
