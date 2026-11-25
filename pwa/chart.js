import { formatNutrientValue, NUTRIENTS } from './nutrition.js';

function escapeSvgText(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&apos;',
  })[character]);
}

function getNiceStep(value) {
  const exponent = Math.floor(Math.log10(value));
  const magnitude = 10 ** exponent;
  const fraction = value / magnitude;
  const niceFractions = [1, 2, 2.5, 5, 10];
  const closestFraction = niceFractions.reduce((closest, candidate) => (
    Math.abs(candidate - fraction) < Math.abs(closest - fraction) ? candidate : closest
  ));
  return closestFraction * magnitude;
}

function formatAxisTick(value, step) {
  const [coefficient, exponentText = '0'] = String(step).split('e');
  const exponent = Number(exponentText);
  const decimalPlaces = Math.min(
    20,
    Math.max(0, (coefficient.split('.')[1] || '').length - exponent)
  );
  if (decimalPlaces === 0) return String(Math.round(value));
  return value.toFixed(decimalPlaces).replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '');
}

function getNutritionAxisTicks(values) {
  const maxValue = Math.max(0, ...values);
  const step = getNiceStep((maxValue || 1) / 4);
  const max = Math.ceil((maxValue || 1) / step) * step;
  const count = Math.round(max / step);
  return {
    step,
    values: Array.from({ length: count + 1 }, (_, index) => index * step),
    max,
  };
}

const NUTRITION_SERIES_COLORS = {
  calories: '#3b82f6',
  protein: '#10b981',
  carbs: '#f59e0b',
  fat: '#ef4444',
  saturated_fat: '#a855f7',
  fiber: '#06b6d4',
  vegetables: '#84a92f',
};

export function generateNutritionSvgChart(days) {
  if (days.length === 0) {
    return '<div class="muted-text" style="text-align: center; padding: 40px;">No nutrition data in this period.</div>';
  }

  const width = 720;
  const height = 300;
  const padding = { top: 34, right: 68, bottom: 46, left: 68 };
  const xMin = padding.left;
  const xMax = width - padding.right;
  const yMin = padding.top;
  const yMax = height - padding.bottom;
  const orderedDays = days.slice().sort((a, b) => a.date.localeCompare(b.date));
  const dates = orderedDays.map((day) => new Date(`${day.date}T00:00:00`));
  const minTime = dates[0].getTime();
  const maxTime = dates.at(-1).getTime();
  const timeRange = maxTime - minTime;
  const getX = (date) => timeRange
    ? xMin + ((date.getTime() - minTime) / timeRange) * (xMax - xMin)
    : (xMin + xMax) / 2;

  const valuesByNutrient = new Map(NUTRIENTS.map((nutrient) => [
    nutrient.id,
    orderedDays
      .map((day, index) => ({
        date: dates[index],
        dateStr: dates[index].toLocaleDateString(undefined, { day: 'numeric', month: 'short' }),
        value: day.values[nutrient.id],
      }))
      .filter((point) => typeof point.value === 'number' && Number.isFinite(point.value)),
  ]));
  const caloriesTicks = getNutritionAxisTicks(valuesByNutrient.get('calories').map((point) => point.value));
  const gramsTicks = getNutritionAxisTicks(
    NUTRIENTS.filter((nutrient) => nutrient.id !== 'calories')
      .flatMap((nutrient) => valuesByNutrient.get(nutrient.id).map((point) => point.value))
  );
  const getY = (value, axis) => yMax - (value / axis.max) * (yMax - yMin);
  const yGridHtml = caloriesTicks.values.map((value) => {
    const y = getY(value, caloriesTicks);
    return `
      <line x1="${xMin}" y1="${y}" x2="${xMax}" y2="${y}" stroke="var(--border, #cbd5e1)" stroke-dasharray="2,4" opacity="0.4" />
      <text x="${xMin - 10}" y="${y + 4}" font-size="10" fill="var(--muted, #64748b)" text-anchor="end">${formatAxisTick(value, caloriesTicks.step)}</text>
    `;
  }).join('');
  const gramsAxisHtml = gramsTicks.values.map((value) => {
    const y = getY(value, gramsTicks);
    return `
      <text x="${xMax + 8}" y="${y + 4}" font-size="10" fill="var(--muted, #64748b)" text-anchor="start">${formatAxisTick(value, gramsTicks.step)}</text>
    `;
  }).join('');

  const xTickIndices = [0, Math.floor(orderedDays.length / 2), orderedDays.length - 1]
    .filter((value, index, list) => list.indexOf(value) === index);
  const xGridHtml = xTickIndices.map((index) => {
    const x = getX(dates[index]);
    return `
      <line x1="${x}" y1="${yMin}" x2="${x}" y2="${yMax}" stroke="var(--border, #cbd5e1)" stroke-dasharray="2,4" opacity="0.4" />
      <text x="${x}" y="${yMax + 18}" font-size="10" fill="var(--muted, #64748b)" text-anchor="middle">${dates[index].toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}</text>
    `;
  }).join('');

  const seriesHtml = NUTRIENTS.map((nutrient) => {
    const points = valuesByNutrient.get(nutrient.id);
    if (!points.length) return '';
    const axis = nutrient.id === 'calories' ? caloriesTicks : gramsTicks;
    const color = NUTRITION_SERIES_COLORS[nutrient.id];
    const path = points.map((point, index) => (
      `${index === 0 ? 'M' : 'L'} ${getX(point.date)} ${getY(point.value, axis)}`
    )).join(' ');
    const marks = points.map((point) => {
      const x = getX(point.date);
      const y = getY(point.value, axis);
      const label = `${point.dateStr}: ${nutrient.label} ${formatNutrientValue(point.value, nutrient)}`;
      const tooltipWidth = Math.min(width - 16, Math.max(96, label.length * 6 + 16));
      const tooltipX = Math.max(
        tooltipWidth / 2 + 8,
        Math.min(width - tooltipWidth / 2 - 8, x)
      );
      const tooltipY = y > 58 ? y - 4 : y + 34;
      return `<g class="chart-point nutrition-chart-point" tabindex="0" role="img" aria-label="${escapeSvgText(label)}">
        <circle class="chart-mark" cx="${x}" cy="${y}" r="4" fill="${color}" stroke="white" stroke-width="1">
          <title>${escapeSvgText(label)}</title>
        </circle>
        <circle class="chart-point-hit-area" cx="${x}" cy="${y}" r="12" />
        <g class="chart-tooltip" transform="translate(${tooltipX} ${tooltipY})" aria-hidden="true">
          <rect x="${-tooltipWidth / 2}" y="-26" width="${tooltipWidth}" height="22" rx="5" />
          <text x="0" y="-11" text-anchor="middle">${escapeSvgText(label)}</text>
        </g>
      </g>`;
    }).join('');

    return `<path d="${path}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />${marks}`;
  }).join('');
  const legendHtml = NUTRIENTS.map((nutrient) => `
    <span class="nutrition-chart-legend-item" role="listitem">
      <span class="nutrition-chart-legend-swatch" style="background: ${NUTRITION_SERIES_COLORS[nutrient.id]};"></span>
      ${escapeSvgText(nutrient.label)}
    </span>
  `).join('');

  return `
    <div class="nutrition-chart-summary muted-text">${orderedDays.length} days plotted</div>
    <div class="nutrition-chart-legend" role="list" aria-label="Nutrient series">${legendHtml}</div>
    <svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" style="display: block; overflow: visible;" aria-labelledby="nutrition-chart-title">
      <title id="nutrition-chart-title">Daily nutrition trends with calories on the left axis and grams on the right axis</title>
      ${yGridHtml}
      ${gramsAxisHtml}
      ${xGridHtml}
      <text x="18" y="${(yMin + yMax) / 2}" transform="rotate(-90 18 ${(yMin + yMax) / 2})" font-size="10" fill="var(--muted, #64748b)" text-anchor="middle">Calories (kcal)</text>
      <text x="${width - 10}" y="${(yMin + yMax) / 2}" transform="rotate(90 ${width - 10} ${(yMin + yMax) / 2})" font-size="10" fill="var(--muted, #64748b)" text-anchor="middle">Grams (g)</text>
      ${seriesHtml}
    </svg>
  `;
}

export function generateSvgChart(data, metric) {
  if (data.length === 0) {
    return `<div style="text-align: center; padding: 40px; color: var(--muted, #64748b);">No data in this period.</div>`;
  }

  const width = 600;
  const height = 240;
  const padding = { top: 30, right: 20, bottom: 40, left: 50 };

  const xMax = width - padding.right;
  const xMin = padding.left;
  const yMax = height - padding.bottom;
  const yMin = padding.top;
  const pointLabel = (d) => {
    const unit = metric.unitName ? ` ${metric.unitName}` : '';
    return `${d.dateStr}: ${d.value}${unit}`;
  };
  const renderTooltip = (d, x, y) => {
    const label = pointLabel(d);
    const tooltipWidth = Math.min(width - 16, Math.max(84, label.length * 7 + 16));
    const tooltipX = Math.max(
      tooltipWidth / 2 + 8,
      Math.min(width - tooltipWidth / 2 - 8, x)
    );
    const tooltipY = y > 58 ? y - 4 : y + 34;
    return `
      <g class="chart-tooltip" transform="translate(${tooltipX} ${tooltipY})" aria-hidden="true">
        <rect x="${-tooltipWidth / 2}" y="-26" width="${tooltipWidth}" height="22" rx="5" />
        <text x="0" y="-11" text-anchor="middle">${escapeSvgText(label)}</text>
      </g>
    `;
  };

  const values = data.map((d) => d.value);
  let minVal = Math.min(...values);
  let maxVal = Math.max(...values);

  const isScore = metric.metricKind === 'score' || metric.unitType === 'integer_range';
  if (isScore) {
    const start = metric.rangeStart ?? 1;
    const end = metric.rangeEnd ?? 5;
    minVal = Math.min(minVal, start);
    maxVal = Math.max(maxVal, end);
  } else {
    const range = maxVal - minVal;
    if (range === 0) {
      minVal = Math.max(0, minVal - 1);
      maxVal = maxVal + 1;
    } else {
      minVal = Math.max(0, minVal - range * 0.1);
      maxVal = maxVal + range * 0.1;
    }
  }

  let yTickValues;
  let yTickStep;
  if (isScore) {
    yTickStep = Math.max(1, Math.ceil((maxVal - minVal) / 4));
    yTickValues = [];
    for (let value = minVal; value <= maxVal; value += yTickStep) {
      yTickValues.push(value);
    }
    if (yTickValues.at(-1) !== maxVal) yTickValues.push(maxVal);
  } else {
    const originalRange = maxVal - minVal;
    yTickStep = getNiceStep(originalRange / 4);
    let tickMin = Math.floor(minVal / yTickStep) * yTickStep;
    let tickMax = Math.ceil(maxVal / yTickStep) * yTickStep;
    while ((tickMax - tickMin) / yTickStep > 5) {
      const magnitude = 10 ** Math.floor(Math.log10(yTickStep));
      const fraction = yTickStep / magnitude;
      const nextFraction = [1, 2, 2.5, 5, 10].find((candidate) => candidate > fraction);
      yTickStep = nextFraction
        ? nextFraction * magnitude
        : 10 * magnitude;
      tickMin = Math.floor(minVal / yTickStep) * yTickStep;
      tickMax = Math.ceil(maxVal / yTickStep) * yTickStep;
    }
    minVal = tickMin;
    maxVal = tickMax;
    const intervalCount = Math.round((tickMax - tickMin) / yTickStep);
    yTickValues = Array.from(
      { length: intervalCount + 1 },
      (_, index) => tickMin + index * yTickStep
    );
  }

  const times = data.map((d) => d.date.getTime());
  const minTime = Math.min(...times);
  const maxTime = Math.max(...times);
  const timeRange = maxTime - minTime || 1;

  const getX = (date) => {
    return xMin + ((date.getTime() - minTime) / timeRange) * (xMax - xMin);
  };

  const getY = (val) => {
    const valRange = maxVal - minVal || 1;
    return yMax - ((val - minVal) / valRange) * (yMax - yMin);
  };

  const avgVal = values.reduce((s, v) => s + v, 0) / values.length;
  const yBaseline = getY(avgVal);

  let yGridHtml = '';
  for (const val of yTickValues) {
    const y = getY(val);
    yGridHtml += `
      <line x1="${xMin}" y1="${y}" x2="${xMax}" y2="${y}" stroke="var(--border, #cbd5e1)" stroke-dasharray="2,4" opacity="0.4" />
      <text x="${xMin - 10}" y="${y + 4}" font-size="10" fill="var(--muted, #64748b)" text-anchor="end">${formatAxisTick(val, yTickStep)}</text>
    `;
  }


  const xTicksIndices = [0, Math.floor(data.length / 2), data.length - 1].filter((val, idx, self) => self.indexOf(val) === idx);
  let xGridHtml = '';
  xTicksIndices.forEach((idx) => {
    const d = data[idx];
    const x = getX(d.date);
    const dateStr = d.date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
    xGridHtml += `
      <line x1="${x}" y1="${yMin}" x2="${x}" y2="${yMax}" stroke="var(--border, #cbd5e1)" stroke-dasharray="2,4" opacity="0.4" />
      <text x="${x}" y="${yMax + 18}" font-size="10" fill="var(--muted, #64748b)" text-anchor="middle">${dateStr}</text>
    `;
  });

  let chartElements = '';
  if (isScore || metric.metricKind === 'count') {
    const xPositions = data.map((d) => getX(d.date));
    const nearestSpacing = xPositions.slice(1).reduce(
      (smallest, x, index) => Math.min(smallest, x - xPositions[index]),
      Infinity
    );
    const barWidth = Number.isFinite(nearestSpacing)
      ? Math.max(2, Math.min(24, Math.floor(nearestSpacing * 0.7)))
      : 12;
    chartElements = data.map((d, index) => {
      const x = xPositions[index] - barWidth / 2;
      const y = getY(d.value);
      const barHeight = yMax - y;
      const color = isScore ? 'var(--primary, #3b82f6)' : 'rgba(59, 130, 246, 0.8)';
      const label = pointLabel(d);
      return `<g class="chart-point" tabindex="0" role="img" aria-label="${escapeSvgText(label)}">
        <rect class="chart-mark" x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" fill="${color}" rx="2" opacity="0.85">
          <title>${escapeSvgText(label)}</title>
        </rect>
        <circle class="chart-point-hit-area" cx="${xPositions[index]}" cy="${y}" r="12" />
        ${renderTooltip(d, xPositions[index], y)}
      </g>`;
    }).join('');
  } else {
    let pathD = '';
    let hasSolidSegments = false;
    const gapPathDs = [];
    const calendarDay = (date) => Date.UTC(
      date.getFullYear(),
      date.getMonth(),
      date.getDate()
    );
    const dayIntervals = data.slice(1).map((d, index) => (
      (calendarDay(d.date) - calendarDay(data[index].date)) / 86_400_000
    ));
    const sortedIntervals = [...dayIntervals].sort((a, b) => a - b);
    const middle = Math.floor(sortedIntervals.length / 2);
    const typicalInterval = sortedIntervals.length
      ? sortedIntervals.length % 2
        ? sortedIntervals[middle]
        : (sortedIntervals[middle - 1] + sortedIntervals[middle]) / 2
      : Infinity;
    const gapThreshold = typicalInterval * 1.5;
    data.forEach((d, idx) => {
      const x = getX(d.date);
      const y = getY(d.value);
      if (idx === 0) {
        pathD += `M ${x} ${y}`;
      } else {
        const prev = data[idx - 1];
        const dayGap = (calendarDay(d.date) - calendarDay(prev.date)) / 86_400_000;
        const prevX = getX(prev.date);
        const prevY = getY(prev.value);
        const cpX1 = prevX + (x - prevX) / 3;
        const cpX2 = prevX + 2 * (x - prevX) / 3;
        const curve = `C ${cpX1} ${prevY}, ${cpX2} ${y}, ${x} ${y}`;
        if (dayGap > gapThreshold) {
          pathD += ` M ${x} ${y}`;
          gapPathDs.push(`M ${prevX} ${prevY} ${curve}`);
        } else {
          hasSolidSegments = true;
          pathD += ` ${curve}`;
        }
      }
    });

    chartElements = `
      ${hasSolidSegments ? `<path d="${pathD}" fill="none" stroke="var(--primary, #3b82f6)" stroke-width="3" />` : ''}
      ${gapPathDs.map((gapPath) => `<path d="${gapPath}" fill="none" stroke="var(--primary, #3b82f6)" stroke-width="3" stroke-dasharray="4,4" opacity="0.75" />`).join('')}
      ${data.map((d) => {
        const x = getX(d.date);
        const y = getY(d.value);
        const label = pointLabel(d);
        return `<g class="chart-point" tabindex="0" role="img" aria-label="${escapeSvgText(label)}">
          <circle class="chart-mark" cx="${x}" cy="${y}" r="4" fill="var(--primary, #3b82f6)" stroke="white" stroke-width="1">
            <title>${escapeSvgText(label)}</title>
          </circle>
          <circle class="chart-point-hit-area" cx="${x}" cy="${y}" r="12" />
          ${renderTooltip(d, x, y)}
        </g>`;
      }).join('')}
    `;
  }

  const unitStr = metric.unitName ? ` (${metric.unitName})` : '';

  return `
    <div style="font-size: 0.9rem; margin-bottom: 8px; display: flex; justify-content: space-between;">
      <span style="font-weight: 600; color: var(--text-color, #f8fafc);">Average: ${avgVal.toFixed(1)}${unitStr}</span>
      <span style="color: var(--muted, #64748b); font-size: 0.8rem;">${data.length} recorded days</span>
    </div>
    <svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" style="display: block; overflow: visible;">
      ${yGridHtml}
      ${xGridHtml}
      <line x1="${xMin}" y1="${yBaseline}" x2="${xMax}" y2="${yBaseline}" stroke="var(--muted, #64748b)" stroke-width="1.5" stroke-dasharray="4,4" opacity="0.6" />
      <text x="${xMax}" y="${yBaseline - 6}" font-size="9" fill="var(--muted, #64748b)" text-anchor="end" font-weight="600">Baseline (Avg): ${avgVal.toFixed(1)}</text>
      ${chartElements}
    </svg>
  `;
}


export function renderSparkline(values, color, { kind = 'quantitative', higherIsBetter = true, rangeStart = null, rangeEnd = null } = {}) {
  const clean = (values || []).map(Number).filter(v => !Number.isNaN(v));
  if (clean.length === 0) {
    return '<span style="font-size: 0.85rem; opacity: 0.6; padding: 4px 0; display: inline-block;">—</span>';
  }

  const width = 192;
  const height = 28;
  const pad = 4;
  const vmin = Math.min(...clean);
  const vmax = Math.max(...clean);

  const toY = (value) => {
    if (clean.length === 1 || vmax === vmin) return height / 2;
    return height - pad - ((value - vmin) / (vmax - vmin)) * (height - pad * 2);
  };

  let lastX = 0;
  let lastY = height / 2;

  if (kind === 'count') {
    const n = clean.length;
    const barGap = 1;
    const available = width - pad * 2;
    const barW = Math.max(2, (available - barGap * (n - 1)) / Math.max(1, n));
    const vmaxLocal = Math.max(1, vmax);
    const rects = [];
    let lastCx = null;
    let lastCy = null;

    for (let i = 0; i < n; i++) {
      const x = pad + i * (barW + barGap);
      const h = (clean[i] / vmaxLocal) * (height - pad * 2);
      const y = height - pad - h;
      if (i === n - 1) {
        lastCx = x + barW / 2;
        lastCy = y;
      }
      rects.push(
        `<rect x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="${barW.toFixed(2)}" height="${h.toFixed(2)}" rx="1.2" ry="1.2" fill="${color}" opacity="0.85" stroke="rgba(0,0,0,0.22)" stroke-width="${i === n - 1 ? 1 : 0}"/>`
      );
    }

    const lollipop = lastCx !== null && lastCy !== null
      ? `
        <line x1="${lastCx.toFixed(2)}" x2="${lastCx.toFixed(2)}" y1="${lastCy.toFixed(2)}" y2="${pad.toFixed(2)}" stroke="rgba(0,0,0,0.16)" stroke-width="1"/>
        <circle cx="${lastCx.toFixed(2)}" cy="${lastCy.toFixed(2)}" r="2.6" fill="${color}" stroke="white" stroke-width="1.2"/>
      `
      : '';

    return `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" preserveAspectRatio="none" aria-hidden="true">${rects.join('')}${lollipop}</svg>`;
  }

  if (kind === 'score') {
    let rs = rangeStart !== null && rangeStart !== undefined ? Number(rangeStart) : Math.round(vmin);
    let re = rangeEnd !== null && rangeEnd !== undefined ? Number(rangeEnd) : Math.round(vmax);
    if (Number.isNaN(rs)) rs = Math.round(vmin);
    if (Number.isNaN(re)) re = Math.round(vmax);
    const span = Math.max(1, re - rs);
    const n = clean.length;
    const gap = 1;
    const available = width - pad * 2;
    const blockW = Math.max(2, (available - gap * (n - 1)) / Math.max(1, n));
    const rects = [];
    let lastCx = null;
    let lastCy = null;
    let lastFill = null;

    for (let i = 0; i < n; i++) {
      const x = pad + i * (blockW + gap);
      const tHeight = Math.min(1, Math.max(0, (clean[i] - rs) / span));
      const tColor = higherIsBetter ? tHeight : 1 - tHeight;
      const r = Math.round(220 * (1 - tColor) + 40 * tColor);
      const g = Math.round(60 * (1 - tColor) + 180 * tColor);
      const b = Math.round(70 * (1 - tColor) + 80 * tColor);
      const fill = `rgb(${r},${g},${b})`;
      const h = Math.max(2, tHeight * (height - pad * 2));
      const y = height - pad - h;
      if (i === n - 1) {
        lastCx = x + blockW / 2;
        lastCy = y;
        lastFill = fill;
      }
      rects.push(
        `<rect x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="${blockW.toFixed(2)}" height="${h.toFixed(2)}" rx="2" ry="2" fill="${fill}" opacity="0.95" stroke="rgba(0,0,0,0.22)" stroke-width="${i === n - 1 ? 1 : 0}"/>`
      );
    }

    const lollipop = lastCx !== null && lastCy !== null
      ? `
        <line x1="${lastCx.toFixed(2)}" x2="${lastCx.toFixed(2)}" y1="${lastCy.toFixed(2)}" y2="${pad.toFixed(2)}" stroke="rgba(0,0,0,0.16)" stroke-width="1"/>
        <circle cx="${lastCx.toFixed(2)}" cy="${lastCy.toFixed(2)}" r="2.6" fill="${lastFill || color}" stroke="white" stroke-width="1.2"/>
      `
      : '';

    return `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" preserveAspectRatio="none" aria-hidden="true">${rects.join('')}${lollipop}</svg>`;
  }

  let points = '';
  if (clean.length === 1 || vmax === vmin) {
    points = `${pad},${height / 2} ${width - pad},${height / 2}`;
    lastX = width - pad;
    lastY = height / 2;
  } else {
    const step = (width - pad * 2) / (clean.length - 1);
    points = clean.map((value, index) => {
      const x = pad + index * step;
      const y = toY(value);
      lastX = x;
      lastY = y;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    }).join(' ');
  }

  return `
    <svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" preserveAspectRatio="none" aria-hidden="true">
      <line x1="${lastX.toFixed(2)}" x2="${lastX.toFixed(2)}" y1="${lastY.toFixed(2)}" y2="${pad.toFixed(2)}" stroke="rgba(0,0,0,0.16)" stroke-width="1"/>
      <polyline fill="none" stroke="${color}" stroke-width="2" points="${points}" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="${lastX.toFixed(2)}" cy="${lastY.toFixed(2)}" r="2.6" fill="${color}" stroke="white" stroke-width="1.2"/>
    </svg>
  `;
}
