import assert from 'node:assert/strict';
import test from 'node:test';

import { getStartDateForPeriod, resampleAndProcessData } from './stats.js';

test('calculates period start dates with calendar arithmetic', () => {
  const anchor = new Date(2024, 5, 15, 12);

  assert.deepEqual(getStartDateForPeriod('Week', anchor), new Date(2024, 5, 8, 12));
  assert.deepEqual(getStartDateForPeriod('Month', anchor), new Date(2024, 4, 15, 12));
  assert.deepEqual(getStartDateForPeriod('6M', anchor), new Date(2023, 11, 15, 12));
  assert.deepEqual(getStartDateForPeriod('Year', anchor), new Date(2023, 5, 15, 12));
  assert.deepEqual(getStartDateForPeriod('All', anchor), new Date(0));
});

test('uses the latest valid entry for each day and filters by metric', () => {
  const today = new Date();
  const latestTime = new Date(today);
  latestTime.setHours(18, 0, 0, 0);
  const earlierTime = new Date(today);
  earlierTime.setHours(9, 0, 0, 0);
  const previousDay = new Date(today);
  previousDay.setDate(previousDay.getDate() - 1);
  previousDay.setHours(12, 0, 0, 0);

  const result = resampleAndProcessData([
    { metricId: 'metric-a', recordedAt: latestTime.toISOString(), value: 8 },
    { metricId: 'metric-a', recordedAt: earlierTime.toISOString(), value: 3 },
    { metricId: 'metric-a', recordedAt: previousDay.toISOString(), value: 2 },
    { metricId: 'metric-b', recordedAt: latestTime.toISOString(), value: 99 },
    { metricId: 'metric-a', recordedAt: 'not-a-date', value: 100 },
  ], { id: 'metric-a', metricKind: 'quantitative' }, 'Week', false, 'Max Load');

  assert.deepEqual(result.map(({ value }) => value), [2, 8]);
});

test('fills missing dates with zero when enabled', () => {
  const today = new Date();
  today.setHours(12, 0, 0, 0);

  const result = resampleAndProcessData([
    { metricId: 'metric-a', recordedAt: today.toISOString(), value: 4 },
  ], { id: 'metric-a', metricKind: 'quantitative' }, 'Week', true, 'Max Load');

  assert.equal(result.length, 8);
  assert.equal(result.filter(({ value }) => value === 0).length, 7);
  assert.equal(result.at(-1).value, 4);
});

test('resamples strength entries using the selected aggregate', () => {
  const today = new Date();
  today.setHours(12, 0, 0, 0);

  const result = resampleAndProcessData([
    {
      metricId: 'strength',
      recordedAt: today.toISOString(),
      sets: [{ loadKg: 60, reps: 8 }, { loadKg: 70, reps: 5 }],
    },
  ], { id: 'strength', metricKind: 'strength_session' }, 'Week', false, 'Total Volume');

  assert.equal(result.length, 1);
  assert.equal(result[0].value, 830);
});
