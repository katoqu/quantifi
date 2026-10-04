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
