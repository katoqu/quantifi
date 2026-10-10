import assert from 'node:assert/strict';
import test from 'node:test';

import { generateSvgChart, renderSparkline } from './chart.js';

const sampleData = [
  { date: new Date(2026, 0, 1), dateStr: 'Jan 1', value: 2 },
  { date: new Date(2026, 0, 2), dateStr: 'Jan 2', value: 4 },
];

test('renders a no-data message for an empty period', () => {
  assert.match(generateSvgChart([], { metricKind: 'quantitative' }), /No data in this period\./);
  assert.doesNotMatch(generateSvgChart([], { metricKind: 'quantitative' }), /<svg/);
});

test('renders quantitative values as a line chart with average and unit', () => {
  const chart = generateSvgChart(sampleData, {
    metricKind: 'quantitative',
    unitName: 'reps',
  });

  assert.match(chart, /<svg[^>]+viewBox="0 0 600 240"/);
  assert.match(chart, /<path d="M [\d.]+ [\d.]+ C /);
  assert.equal((chart.match(/<circle class="chart-mark"/g) || []).length, 2);
  assert.match(chart, /Average: 3\.0 \(reps\)/);
  assert.match(chart, /2 days plotted/);
  assert.match(chart, /aria-label="Jan 1: 2 reps"/);
  assert.match(chart, /<title>Jan 1: 2 reps<\/title>/);
  assert.match(chart, /class="chart-tooltip"/);
});

test('uses rounded, evenly spaced guide values for quantitative y-axis labels', () => {
  const data = [
    { date: new Date(2026, 0, 1), dateStr: 'Jan 1', value: 12 },
    { date: new Date(2026, 0, 2), dateStr: 'Jan 2', value: 19 },
  ];
  const chart = generateSvgChart(data, { metricKind: 'quantitative' });
  const yAxisLabels = [...chart.matchAll(/<text x="40" y="[\d.]+"[^>]*>([^<]+)<\/text>/g)]
    .map(([, label]) => label);

  assert.deepEqual(yAxisLabels, ['10', '12', '14', '16', '18', '20']);
});

test('uses clean decimal guide values when the data range is small', () => {
  const data = [
    { date: new Date(2026, 0, 1), dateStr: 'Jan 1', value: 0.1 },
    { date: new Date(2026, 0, 2), dateStr: 'Jan 2', value: 0.2 },
  ];
  const chart = generateSvgChart(data, { metricKind: 'quantitative' });
  const yAxisLabels = [...chart.matchAll(/<text x="40" y="[\d.]+"[^>]*>([^<]+)<\/text>/g)]
    .map(([, label]) => label);

  assert.deepEqual(yAxisLabels, ['0.05', '0.1', '0.15', '0.2', '0.25']);
});

test('preserves exact values in accessible chart point labels and tooltips', () => {
  const chart = generateSvgChart([
    { date: new Date(2026, 0, 1), dateStr: 'Jan 1', value: 2.345678 },
  ], {
    metricKind: 'quantitative',
    unitName: 'kg',
  });

  assert.match(chart, /aria-label="Jan 1: 2\.345678 kg"/);
  assert.match(chart, /<title>Jan 1: 2\.345678 kg<\/title>/);
  assert.match(chart, />Jan 1: 2\.345678 kg<\/text>/);
});

test('renders count metrics as bars', () => {
  const chart = generateSvgChart(sampleData, { metricKind: 'count' });

  assert.equal((chart.match(/<rect class="chart-mark"/g) || []).length, 2);
  assert.doesNotMatch(chart, /<path /);
});

test('keeps count bars from overlapping when dates are clustered', () => {
  const data = Array.from({ length: 10 }, (_, index) => {
    const date = new Date(2026, 0, index < 9 ? index + 1 : 31);
    return { date, dateStr: date.toDateString(), value: index + 1 };
  });
  const chart = generateSvgChart(data, { metricKind: 'count' });
  const bars = [...chart.matchAll(/<rect class="chart-mark" x="([\d.]+)"[^>]*width="([\d.]+)"/g)]
    .map(([, x, width]) => ({ x: Number(x), width: Number(width) }));

  assert.equal(bars.length, data.length);
  assert.ok(bars.every((bar, index) => index === 0 || bars[index - 1].x + bars[index - 1].width <= bar.x));
});

test('renders score metrics as bars and respects the score range', () => {
  const chart = generateSvgChart(sampleData, {
    metricKind: 'score',
    rangeStart: 1,
    rangeEnd: 5,
  });

  assert.equal((chart.match(/<rect class="chart-mark"/g) || []).length, 2);
  assert.match(chart, /<text[^>]*>1<\/text>/);
  assert.match(chart, /<text[^>]*>5<\/text>/);
});

test('renders a placeholder for empty sparkline data', () => {
  assert.match(renderSparkline([], 'red'), /<span[^>]*>—<\/span>/);
  assert.match(renderSparkline([undefined, 'invalid'], 'red'), /<span[^>]*>—<\/span>/);
});

test('renders quantitative sparklines and keeps a single value centered', () => {
  const sparkline = renderSparkline([1, 3, 2], 'purple');
  assert.match(sparkline, /<polyline[^>]*stroke="purple"/);
  assert.match(sparkline, /points="4\.00,[\d.]+ 96\.00,[\d.]+ 188\.00,[\d.]+"/);

  const singleValue = renderSparkline([5], 'purple');
  assert.match(singleValue, /points="4,14 188,14"/);
});

test('renders count sparklines as bars with a marker for the latest value', () => {
  const sparkline = renderSparkline([2, 4, 3], 'orange', { kind: 'count' });
  assert.equal((sparkline.match(/<rect /g) || []).length, 3);
  assert.match(sparkline, /fill="orange"/);
  assert.equal((sparkline.match(/<circle /g) || []).length, 1);
});

test('colors score sparklines according to range and direction', () => {
  const higherIsBetter = renderSparkline([1, 5], 'blue', {
    kind: 'score',
    rangeStart: 1,
    rangeEnd: 5,
  });
  const lowerIsBetter = renderSparkline([1, 5], 'blue', {
    kind: 'score',
    rangeStart: 1,
    rangeEnd: 5,
    higherIsBetter: false,
  });

  assert.match(higherIsBetter, /fill="rgb\(40,180,80\)"/);
  assert.match(lowerIsBetter, /fill="rgb\(220,60,70\)"/);
});
