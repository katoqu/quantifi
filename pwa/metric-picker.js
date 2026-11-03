import { filterMetricsBySearch } from './metric-filters.js';

export function renderMetricPicker({
  selectedContainer,
  pickerContainer,
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
    const selected = document.createElement(expandButton ? 'span' : 'button');
    if (!expandButton) {
      selected.type = 'button';
      selected.setAttribute('aria-controls', suggestionsContainer.id);
      selected.setAttribute('aria-expanded', String(isOpen));
    }
    selected.className = 'selected-metric-chip';
    selected.setAttribute('aria-label', `Selected metric: ${selectedMetric.name}`);
    selected.textContent = selectedMetric.name;
    selectedContainer.append(selected);
  } else {
    const choose = document.createElement(expandButton ? 'span' : 'button');
    if (!expandButton) {
      choose.type = 'button';
      choose.setAttribute('aria-controls', suggestionsContainer.id);
      choose.setAttribute('aria-expanded', String(isOpen));
    }
    choose.className = 'selected-metric-chip selected-metric-placeholder';
    choose.setAttribute('aria-label', 'Choose a metric');
    choose.textContent = 'Choose a metric';
    selectedContainer.append(choose);
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
  setMetricPickerOpen(isOpen, suggestionsContainer, searchInput, expandButton, pickerContainer, selectedContainer);
}

export function setMetricPickerOpen(
  isOpen,
  suggestionsContainer,
  searchInput,
  expandButton,
  pickerContainer,
  selectedContainer,
) {
  pickerContainer?.classList.toggle('is-open', isOpen);
  suggestionsContainer.classList.toggle('hidden', !isOpen);
  selectedContainer?.querySelector('.selected-metric-chip')?.setAttribute('aria-expanded', String(isOpen));
  expandButton?.setAttribute('aria-expanded', String(isOpen));
  searchInput.setAttribute('aria-expanded', String(isOpen));
  if (expandButton) {
    expandButton.setAttribute('aria-label', isOpen ? 'Hide matching metrics' : 'Show matching metrics');
  }
}
