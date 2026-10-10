export function getRecentMetricIds(entries, limit = 5) {
  if (!entries || entries.length === 0 || limit <= 0) return [];
  const sorted = [...entries].sort((a, b) => new Date(b.recordedAt) - new Date(a.recordedAt));
  const seen = new Set();
  const recentIds = [];
  for (const entry of sorted) {
    if (!seen.has(entry.metricId)) {
      seen.add(entry.metricId);
      recentIds.push(entry.metricId);
      if (recentIds.length >= limit) break;
    }
  }
  return recentIds;
}

export function sortMetricsByRecentEntry(metrics, entries) {
  const latestEntryByMetric = new Map();
  for (const entry of entries) {
    const timestamp = new Date(entry.recordedAt).getTime();
    if (!Number.isFinite(timestamp)) continue;
    latestEntryByMetric.set(
      entry.metricId,
      Math.max(latestEntryByMetric.get(entry.metricId) ?? -Infinity, timestamp)
    );
  }
  return [...metrics].sort((a, b) => {
    const aLatest = latestEntryByMetric.get(a.id) ?? -Infinity;
    const bLatest = latestEntryByMetric.get(b.id) ?? -Infinity;
    if (aLatest !== bLatest) return bLatest - aLatest;
    return a.name.localeCompare(b.name);
  });
}

export function filterMetricsByView(filter, metrics, entries, categories) {
  if (!filter || filter === 'Recent') {
    const recentIds = getRecentMetricIds(entries, 5);
    if (!recentIds.length) {
      return [...metrics].sort((a, b) => a.name.localeCompare(b.name));
    }
    const recentMap = new Map(recentIds.map((id, index) => [id, index]));
    return [...metrics].sort((a, b) => {
      const aIndex = recentMap.has(a.id) ? recentMap.get(a.id) : Infinity;
      const bIndex = recentMap.has(b.id) ? recentMap.get(b.id) : Infinity;
      if (aIndex !== bIndex) return aIndex - bIndex;
      return a.name.localeCompare(b.name);
    });
  }
  const category = categories.find((item) => item.name.toLowerCase() === filter.toLowerCase());
  if (!category) return [];
  return metrics.filter((metric) => metric.categoryId === category.id);
}

export function filterMetricsBySearch(metrics, categories, searchTerm) {
  if (!searchTerm) return metrics;
  const term = searchTerm.trim().toLowerCase();
  const archivedOnly = term.startsWith('#');
  const query = archivedOnly ? term.slice(1).trim() : term;
  const categoryMap = new Map(categories.map((category) => [category.id, category.name.toLowerCase()]));
  return metrics.filter((metric) => {
    if (archivedOnly && !metric.isArchived) return false;
    if (!query) return true;
    const nameMatch = metric.name.toLowerCase().includes(query);
    const categoryName = categoryMap.get(metric.categoryId) || '';
    const categoryMatch = categoryName.includes(query);
    return nameMatch || categoryMatch;
  });
}
