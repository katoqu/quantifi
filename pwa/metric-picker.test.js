import assert from 'node:assert/strict';
import test from 'node:test';

import { setMetricPickerOpen } from './metric-picker.js';

function classList() {
  const classes = new Set();
  return {
    contains: (name) => classes.has(name),
    toggle: (name, enabled) => enabled ? classes.add(name) : classes.delete(name),
  };
}

test('opens and closes the metric search picker', () => {
  const pickerContainer = { classList: classList() };
  const suggestionsContainer = { classList: classList() };
  const chip = { setAttribute: (name, value) => { chip[name] = value; } };
  const selectedContainer = { querySelector: () => chip };
  const searchInput = { setAttribute: (name, value) => { searchInput[name] = value; } };

  setMetricPickerOpen(false, suggestionsContainer, searchInput, null, pickerContainer, selectedContainer);
  assert.equal(pickerContainer.classList.contains('is-open'), false);
  assert.equal(suggestionsContainer.classList.contains('hidden'), true);

  setMetricPickerOpen(true, suggestionsContainer, searchInput, null, pickerContainer, selectedContainer);
  assert.equal(pickerContainer.classList.contains('is-open'), true);
  assert.equal(suggestionsContainer.classList.contains('hidden'), false);
  assert.equal(searchInput['aria-expanded'], 'true');
  assert.equal(chip['aria-expanded'], 'true');

  setMetricPickerOpen(false, suggestionsContainer, searchInput, null, pickerContainer, selectedContainer);
  assert.equal(pickerContainer.classList.contains('is-open'), false);
  assert.equal(suggestionsContainer.classList.contains('hidden'), true);
  assert.equal(searchInput['aria-expanded'], 'false');
  assert.equal(chip['aria-expanded'], 'false');
});
