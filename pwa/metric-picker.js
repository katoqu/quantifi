import { filterMetricsBySearch } from './metric-filters.js';

export function renderMetricPicker({
  selectedContainer,
  suggestionsContainer,
  searchInput,
  clearButton,
  expandButton,
  metrics,
  categories,
  selectedMetric,
  isOpen,
}) {
  selectedContainer.replaceChildren();
  suggestionsContainer.replaceChildren();
  if (selectedMetric) {
    const selected = document.createElement('span');
    selected.className = 'selected-metric-chip';
    selected.setAttribute('aria-label', `Selected metric: ${selectedMetric.name}`);
    selected.textContent = selectedMetric.name;
    selectedContainer.append(selected);
  }

  const matchingMetrics = filterMetricsBySearch(metrics, categories, searchInput.value);
  matchingMetrics.forEach((metric) => {
    const option = document.createElement('button');
    option.type = 'button';
    option.className = 'search-dropdown-suggestion';
    option.dataset.metricId = metric.id;
    option.setAttribute('role', 'option');
    option.setAttribute('aria-selected', String(metric.id === selectedMetric?.id));
    option.textContent = `${metric.isArchived ? '# ' : ''}${metric.name}`;
    suggestionsContainer.append(option);
  });

  if (!matchingMetrics.length) {
    const emptyMessage = document.createElement('p');
    emptyMessage.className = 'search-dropdown-empty';
    emptyMessage.textContent = 'No metrics match this search.';
    suggestionsContainer.append(emptyMessage);
  }

  clearButton.classList.toggle('hidden', !searchInput.value);
  setMetricPickerOpen(isOpen, suggestionsContainer, searchInput, expandButton);
}

export function setMetricPickerOpen(isOpen, suggestionsContainer, searchInput, expandButton) {
  suggestionsContainer.classList.toggle('hidden', !isOpen);
  expandButton.setAttribute('aria-expanded', String(isOpen));
  searchInput.setAttribute('aria-expanded', String(isOpen));
  expandButton.setAttribute('aria-label', isOpen ? 'Hide matching metrics' : 'Show matching metrics');
}
