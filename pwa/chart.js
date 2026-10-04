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

  const yTicks = 4;
  let yGridHtml = '';
  for (let i = 0; i <= yTicks; i++) {
    const ratio = i / yTicks;
    const val = minVal + ratio * (maxVal - minVal);
    const y = getY(val);
    yGridHtml += `
      <line x1="${xMin}" y1="${y}" x2="${xMax}" y2="${y}" stroke="var(--border, #cbd5e1)" stroke-dasharray="2,4" opacity="0.4" />
      <text x="${xMin - 10}" y="${y + 4}" font-size="10" fill="var(--muted, #64748b)" text-anchor="end">${val.toFixed(isScore ? 0 : 1)}</text>
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
      return `<rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" fill="${color}" rx="2" opacity="0.85">
        <title>${d.dateStr}: ${d.value.toFixed(1)}</title>
      </rect>`;
    }).join('');
  } else {
    let pathD = '';
    data.forEach((d, idx) => {
      const x = getX(d.date);
      const y = getY(d.value);
      if (idx === 0) {
        pathD += `M ${x} ${y}`;
      } else {
        const prev = data[idx - 1];
        const prevX = getX(prev.date);
        const prevY = getY(prev.value);
        const cpX1 = prevX + (x - prevX) / 3;
        const cpY1 = prevY;
        const cpX2 = prevX + 2 * (x - prevX) / 3;
        const cpY2 = y;
        pathD += ` C ${cpX1} ${cpY1}, ${cpX2} ${cpY2}, ${x} ${y}`;
      }
    });

    chartElements = `
      <path d="${pathD}" fill="none" stroke="var(--primary, #3b82f6)" stroke-width="3" />
      ${data.map((d) => `<circle cx="${getX(d.date)}" cy="${getY(d.value)}" r="4" fill="var(--primary, #3b82f6)" stroke="white" stroke-width="1">
        <title>${d.dateStr}: ${d.value.toFixed(1)}</title>
      </circle>`).join('')}
    `;
  }

  const unitStr = metric.unitName ? ` (${metric.unitName})` : '';

  return `
    <div style="font-size: 0.9rem; margin-bottom: 8px; display: flex; justify-content: space-between;">
      <span style="font-weight: 600; color: var(--text-color, #f8fafc);">Average: ${avgVal.toFixed(1)}${unitStr}</span>
      <span style="color: var(--muted, #64748b); font-size: 0.8rem;">${data.length} days plotted</span>
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
