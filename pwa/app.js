import {
  createCategory,
  createChangeEvent,
  createEntry,
  createMetric,
  deleteCategory,
  deleteEntry,
  deleteMetric,
  exportDataAsCsv,
  getMetricByName,
  importCsvText,
  listCategories,
  listChangeEvents,
  listEntries,
  listMetrics,
  listNutritionMetrics,
  listNutritionDays,
  listNutritionTargets,
  migrateLegacyNutritionDays,
  seedBaseData,
  saveNutritionDay,
  saveNutritionTarget,
  updateCategory,
  updateEntry,
  updateMetric,
  updateChangeEvent,
  deleteChangeEvent,
  STORE_NAMES,
} from './db.js';
import {
  buildStrengthProgressRecommendation,
  computeDurationValue,
  computeStrengthValue,
  formatStrengthSession,
  getLastStrengthSet,
} from './strength.js';
import { resampleAndProcessData } from './stats.js';
import {
  canKeepMetricValues,
  filterMetricsBySearch,
  filterMetricsByView,
  sortMetricsByRecentEntry,
} from './metric-filters.js';
import { generateNutritionSvgChart, generateSvgChart, renderSparkline } from './chart.js';
import { mountStrengthSetEditor, normalizeStrengthSet } from './strength-set-editor.js';
import { renderMetricPicker, setMetricPickerOpen } from './metric-picker.js';
import {
  archiveWorkoutPlan,
  listWorkoutPlans,
  listWorkoutSessions,
  saveWorkoutPlan,
  saveWorkoutPlanImport,
  saveWorkoutSession,
} from './workout-data.js';
import { mountWorkoutsView } from './workouts-view.js';
import {
  formatNutrientValue,
  filterNutritionDaysForPeriod,
  getNutritionPreviewRecords,
  NUTRIENTS,
  parseNutritionImportJson,
  RESERVED_NUTRITION_METRIC_NAMES,
  formatNutritionTarget,
  NUTRITION_TARGET_TYPES,
} from './nutrition.js';

const ui = {
  primaryNav: document.querySelector('.tabs'),
  tabs: Array.from(document.querySelectorAll('.tab')),
  views: Array.from(document.querySelectorAll('.view')),
  metricGrid: document.querySelector('#metricGrid'),
  homeNoMetrics: document.querySelector('#homeNoMetrics'),
  createFirstMetric: document.querySelector('#createFirstMetric'),
  quickStartCard: document.querySelector('#quickStartCard'),
  dismissQuickStart: document.querySelector('#dismissQuickStart'),
  neverShowQuickStart: document.querySelector('#neverShowQuickStart'),
  showQuickStart: document.querySelector('#showQuickStart'),
  homeAddMetricBtn: document.querySelector('#homeAddMetricBtn'),
  homeAddCategoryBtn: document.querySelector('#homeAddCategoryBtn'),
  homeSettingsLink: document.querySelector('#homeSettingsLink'),
  manageAttributesDetails: document.querySelector('#manageAttributesDetails'),
  homeSearchClear: document.querySelector('#homeSearchClear'),
  homeSearchExpand: document.querySelector('#homeSearchExpand'),
  homeSearchSuggestions: document.querySelector('#homeSearchSuggestions'),
  metricSelect: document.querySelector('#metricSelect'),
  addMetricPicker: document.querySelector('#addMetricPicker'),
  addSelectedMetric: document.querySelector('#addSelectedMetric'),
  metricSelectSearch: document.querySelector('#metricSelectSearch'),
  addMetricClear: document.querySelector('#addMetricClear'),
  addMetricSuggestions: document.querySelector('#addMetricSuggestions'),
  statsMetricPicker: document.querySelector('#statsMetricPicker'),
  statsSelectedMetric: document.querySelector('#statsSelectedMetric'),
  statsMetricSearch: document.querySelector('#statsMetricSearch'),
  statsMetricClear: document.querySelector('#statsMetricClear'),
  statsMetricSuggestions: document.querySelector('#statsMetricSuggestions'),
  entryFields: document.querySelector('#entryFields'),
  entryFieldsHint: document.querySelector('#entryFieldsHint'),
  metricSwitchModal: document.querySelector('#metricSwitchModal'),
  metricSwitchMessage: document.querySelector('#metricSwitchMessage'),
  cancelMetricSwitch: document.querySelector('#cancelMetricSwitch'),
  keepMetricValues: document.querySelector('#keepMetricValues'),
  clearMetricValues: document.querySelector('#clearMetricValues'),
  metricName: document.querySelector('#metricName'),
  metricCategory: document.querySelector('#metricCategory'),
  metricUnit: document.querySelector('#metricUnit'),
  metricType: document.querySelector('#metricType'),
  metricKind: document.querySelector('#metricKind'),
  strengthMeasureField: document.querySelector('#strengthMeasureField'),
  strengthMeasure: document.querySelector('#strengthMeasure'),
  metricDescription: document.querySelector('#metricDescription'),
  metricList: document.querySelector('#metricList'),
  metricSearch: document.querySelector('#metricSearch'),
  metricSearchDatalist: document.querySelector('#metricSearchDatalist'),
  metricEditForm: document.querySelector('#metricEditForm'),
  addMetricBtn: document.querySelector('#addMetricBtn'),
  editMetricBtn: document.querySelector('#editMetricBtn'),
  saveMetricEdit: document.querySelector('#saveMetricEdit'),
  archiveMetricEdit: document.querySelector('#archiveMetricEdit'),
  deleteMetricEdit: document.querySelector('#deleteMetricEdit'),
  cancelMetric: document.querySelector('#cancelMetric'),
  categoryList: document.querySelector('#categoryList'),
  categoryForm: document.querySelector('#categoryForm'),
  categoryName: document.querySelector('#categoryName'),
  categoryDescriptionAdd: document.querySelector('#categoryDescriptionAdd'),
  categorySearch: document.querySelector('#categorySearch'),
  categorySearchDatalist: document.querySelector('#categorySearchDatalist'),
  categoryEditForm: document.querySelector('#categoryEditForm'),
  categoryEditFields: document.querySelector('#categoryEditFields'),
  editCategoryName: document.querySelector('#editCategoryName'),
  editCategoryDescription: document.querySelector('#editCategoryDescription'),
  addCategoryBtn: document.querySelector('#addCategoryBtn'),
  editCategoryBtn: document.querySelector('#editCategoryBtn'),
  deleteCategoryBtn: document.querySelector('#deleteCategoryBtn'),
  saveCategoryEdit: document.querySelector('#saveCategoryEdit'),
  cancelCategoryEdit: document.querySelector('#cancelCategoryEdit'),
  cancelCategory: document.querySelector('#cancelCategory'),
  changeList: document.querySelector('#changeList'),
  workoutApp: document.querySelector('#workoutApp'),
  nutritionJsonInput: document.querySelector('#nutritionJsonInput'),
  nutritionReviewJsonButton: document.querySelector('#nutritionReviewJsonButton'),
  nutritionImportButton: document.querySelector('#nutritionImportButton'),
  nutritionImportFile: document.querySelector('#nutritionImportFile'),
  nutritionImportPreview: document.querySelector('#nutritionImportPreview'),
  nutritionImportSummary: document.querySelector('#nutritionImportSummary'),
  nutritionImportWarning: document.querySelector('#nutritionImportWarning'),
  nutritionImportRecords: document.querySelector('#nutritionImportRecords'),
  nutritionConfirmImport: document.querySelector('#nutritionConfirmImport'),
  nutritionCancelImport: document.querySelector('#nutritionCancelImport'),
  nutritionDayForm: document.querySelector('#nutritionDayForm'),
  nutritionDate: document.querySelector('#nutritionDate'),
  nutritionValueFields: document.querySelector('#nutritionValueFields'),
  nutritionNewDayButton: document.querySelector('#nutritionNewDayButton'),
  nutritionEditorHeading: document.querySelector('#nutritionEditorHeading'),
  nutritionCurrentTargets: document.querySelector('#nutritionCurrentTargets'),
  nutritionTargetHistory: document.querySelector('#nutritionTargetHistory'),
  nutritionTargetForm: document.querySelector('#nutritionTargetForm'),
  nutritionTargetFormHeading: document.querySelector('#nutritionTargetFormHeading'),
  nutritionTargetNutrient: document.querySelector('#nutritionTargetNutrient'),
  nutritionTargetType: document.querySelector('#nutritionTargetType'),
  nutritionTargetSingleValueField: document.querySelector('#nutritionTargetSingleValueField'),
  nutritionTargetSingleValueLabel: document.querySelector('#nutritionTargetSingleValueLabel'),
  nutritionTargetValue: document.querySelector('#nutritionTargetValue'),
  nutritionTargetRangeFields: document.querySelector('#nutritionTargetRangeFields'),
  nutritionTargetMinValue: document.querySelector('#nutritionTargetMinValue'),
  nutritionTargetMaxValue: document.querySelector('#nutritionTargetMaxValue'),
  nutritionTargetEffectiveFrom: document.querySelector('#nutritionTargetEffectiveFrom'),
  nutritionTargetNote: document.querySelector('#nutritionTargetNote'),
  nutritionTargetClearButton: document.querySelector('#nutritionTargetClearButton'),
  nutritionVisibilitySettings: document.querySelector('#nutritionVisibilitySettings'),
  nutritionHistory: document.querySelector('#nutritionHistory'),
  nutritionPeriodControl: document.querySelector('#nutritionPeriodControl'),
  nutritionChartContainer: document.querySelector('#nutritionChartContainer'),
  statsSummary: document.querySelector('#statsSummary'),
  entryForm: document.querySelector('#entryForm'),
  changeForm: document.querySelector('#changeForm'),
  metricForm: document.querySelector('#metricForm'),
  exportButton: document.querySelector('#exportButton'),
  importButton: document.querySelector('#importButton'),
  importFile: document.querySelector('#importFile'),
  installButton: document.querySelector('#installButton'),
  numericValueField: document.querySelector('#numericValueField'),
  entryValue: document.querySelector('#entryValue'),
  strengthWorkoutFields: document.querySelector('#strengthWorkoutFields'),
  strengthLoadInput: document.querySelector('#strengthLoadInput'),
  strengthLoadLabel: document.querySelector('#strengthLoadLabel'),
  strengthMeasureLabel: document.querySelector('#strengthMeasureLabel'),
  strengthRepsInput: document.querySelector('#strengthRepsInput'),
  strengthAddSetButton: document.querySelector('#strengthAddSetButton'),
  strengthSetList: document.querySelector('#strengthSetList'),
  strengthBaseline: document.querySelector('#strengthBaseline'),
  entryTargetAction: document.querySelector('#entryTargetAction'),
  targetActionField: document.querySelector('#targetActionField'),
  entryDatePills: document.querySelector('#entryDatePills'),
  entryDate: document.querySelector('#entryDate'),
  entryTime: document.querySelector('#entryTime'),
  dateTimeFields: document.querySelector('#dateTimeFields'),
  targetActionPills: document.querySelector('#targetActionPills'),
  homeSearch: document.querySelector('#homeSearch'),
  showCategoriesBtn: document.querySelector('#showCategoriesBtn'),
  showMetricsBtn: document.querySelector('#showMetricsBtn'),
  settingsCategoriesPanel: document.querySelector('#settingsCategoriesPanel'),
  settingsMetricsPanel: document.querySelector('#settingsMetricsPanel'),
  showArchivedMetricsToggle: document.querySelector('#showArchivedMetricsToggle'),
  backupReminderBanner: document.querySelector('#backupReminderBanner'),
  unsavedCount: document.querySelector('#unsavedCount'),
  backupExportButton: document.querySelector('#backupExportButton'),
  backupSnoozeButton: document.querySelector('#backupSnoozeButton'),
  logShowArchived: document.querySelector('#logShowArchived'),
  changeCategory: document.querySelector('#changeCategory'),
  changeDate: document.querySelector('#changeDate'),
  changeTime: document.querySelector('#changeTime'),
  statsMetricSelect: document.querySelector('#statsMetricSelect'),
  statsControls: document.querySelector('#statsControls'),
  statsPeriodControl: document.querySelector('#statsPeriodControl'),
  statsZerosToggle: document.querySelector('#statsZerosToggle'),
  statsStrengthControl: document.querySelector('#statsStrengthControl'),
  statsStrengthSelect: document.querySelector('#statsStrengthSelect'),
  statsChartContainer: document.querySelector('#statsChartContainer'),
  themeToggle: document.querySelector('#themeToggle'),
  entriesModal: document.querySelector('#entriesModal'),
  entriesModalTitle: document.querySelector('#entriesModalTitle'),
  entriesTableBody: document.querySelector('#entriesTableBody'),
  closeEntriesModal: document.querySelector('#closeEntriesModal'),
  modalOverlay: document.querySelector('.modal-overlay'),
};

let deferredPrompt = null;
let addSelectedMetricId = null;
let strengthInputsDirty = false;
let metricSwitchChoiceResolver = null;
let suppressStrengthLoadPrefill = false;
const strengthSetEditor = mountStrengthSetEditor({
  container: ui.strengthSetList,
  loadInput: ui.strengthLoadInput,
  repsInput: ui.strengthRepsInput,
  addButton: ui.strengthAddSetButton,
});
const workoutsView = mountWorkoutsView(ui.workoutApp, {
  listMetrics: (includeArchived = false) => listMetrics(includeArchived),
  listCategories,
  listEntries,
  listWorkoutPlans,
  listWorkoutSessions,
  saveWorkoutPlan,
  saveWorkoutPlanImport,
  archiveWorkoutPlan,
  saveWorkoutSession,
  onDataChanged: async () => {
    incrementUnsavedCount();
    await renderAll();
  },
});

let editingEventId = null;
let endingEventId = null;
let revivingEventId = null;
let editingEntryId = null;
let pendingNutritionImport = null;
const NUTRITION_VISIBILITY_KEY = 'quantifi-nutrition-visible-nutrients';
let visibleNutritionNutrients = loadVisibleNutritionNutrients();

let activeFilters = { home: 'Recent', add: 'Recent', stats: 'Recent', log: 'Recent' };
let homeSearchTerm = '';
let homeSearchOptions = [];
let homeSearchSuggestionsOpen = false;
let openManageAttributesOnSettings = false;
let addMetricSearchTerm = '';
let statsMetricSearchTerm = '';
let addMetricCandidates = [];
let addMetricCategories = [];
let statsMetricCandidates = [];
let addMetricPickerOpen = false;
let statsMetricPickerOpen = false;
let statsRenderRequestId = 0;
const SHOW_ARCHIVED_METRICS_KEY = 'quantifi-show-archived-metrics';
const QUICK_START_DISMISSED_KEY = 'quantifi-quick-start-dismissed';
const QUICK_START_NEVER_SHOW_KEY = 'quantifi-quick-start-never-show';
let showArchivedMetrics = localStorage.getItem(SHOW_ARCHIVED_METRICS_KEY) === 'true';
const BACKUP_CHANGE_THRESHOLD = 10;
const BACKUP_REMINDER_AGE_MS = 7 * 24 * 60 * 60 * 1000;
const PWA_BACKUP_CHANGE_THRESHOLD = 25;
const PWA_BACKUP_REMINDER_AGE_MS = 30 * 24 * 60 * 60 * 1000;
const BACKUP_SNOOZE_MS = 3 * 24 * 60 * 60 * 1000;
const BACKUP_BUTTON_PRESSED_AT_KEY = 'quantifi-backup-button-pressed-at';
let backupReminderTimer = null;

let activeVizSettings = {
  metricId: null,
  period: 'Month',
  zeros: false,
  strengthAgg: 'Max Load',
};
let activeNutritionPeriod = 'Month';
let nutritionChartDays = [];

function renderMarkdown(text) {
  if (!text) return '';
  let html = text
    .replace(/&/g, '&')
    .replace(/</g, '<')
    .replace(/>/g, '>');

  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  html = html.replace(/`(.*?)`/g, '<code>$1</code>');

  const lines = html.split('\n');
  let inList = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.startsWith('- ') || line.startsWith('* ')) {
      const content = line.substring(2);
      if (!inList) {
        lines[i] = '<ul><li>' + content + '</li>';
        inList = true;
      } else {
        lines[i] = '<li>' + content + '</li>';
      }
    } else {
      if (inList) {
        lines[i] = '</ul>' + lines[i];
        inList = false;
      }
    }
  }
  if (inList) {
    lines.push('</ul>');
  }
  html = lines.join('\n');

  const blocks = html.split(/\n\s*\n/);
  html = blocks.map(block => {
    block = block.trim();
    if (!block) return '';
    if (block.startsWith('<h') || block.startsWith('<ul') || block.startsWith('<li') || block.startsWith('<ol')) {
      return block;
    }
    return `<p>${block.replace(/\n/g, '<br />')}</p>`;
  }).join('');

  return html;
}

function resetChangeFormDateTime() {
  const now = new Date();
  const dateStr = now.toISOString().split('T')[0];
  const timeStr = now.toTimeString().slice(0, 5);
  if (ui.changeDate) ui.changeDate.value = dateStr;
  if (ui.changeTime) ui.changeTime.value = timeStr;
}

function selectMetric(metricId) {
  if (!metricId) return;
  currentMetricId = metricId;
  activeVizSettings.metricId = metricId;
}

function updateHomeSearchClearButton() {
  ui.homeSearchClear?.classList.toggle('hidden', !ui.homeSearch?.value);
}

function renderHomeSearchSuggestions() {
  const suggestions = ui.homeSearchSuggestions;
  const searchTerm = ui.homeSearch?.value.trim().toLowerCase() || '';
  const archivedOnly = searchTerm.startsWith('#');
  const query = archivedOnly ? searchTerm.slice(1).trim() : searchTerm;
  const matchingOptions = homeSearchOptions.filter((option) => {
    if (archivedOnly && !option.isArchived) return false;
    return !query || option.value.toLowerCase().includes(query);
  });

  suggestions.replaceChildren();
  matchingOptions.slice(0, 12).forEach((option) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'search-dropdown-suggestion';
    button.setAttribute('role', 'option');
    button.textContent = option.value;
    button.addEventListener('click', () => {
      ui.homeSearch.value = option.value;
      homeSearchTerm = option.value.trim().toLowerCase();
      homeSearchSuggestionsOpen = false;
      updateHomeSearchClearButton();
      renderHome();
      ui.homeSearch.focus();
    });
    suggestions.append(button);
  });

  if (!matchingOptions.length) {
    const emptyMessage = document.createElement('p');
    emptyMessage.className = 'search-dropdown-empty';
    emptyMessage.textContent = 'No matching metrics or categories.';
    suggestions.append(emptyMessage);
  }

  suggestions.classList.toggle('hidden', !homeSearchSuggestionsOpen);
  ui.homeSearchExpand?.setAttribute('aria-expanded', String(homeSearchSuggestionsOpen));
  ui.homeSearch?.setAttribute('aria-expanded', String(homeSearchSuggestionsOpen));
  ui.homeSearchExpand?.setAttribute(
    'aria-label',
    homeSearchSuggestionsOpen ? 'Hide matching metrics and categories' : 'Show matching metrics and categories'
  );
}

function setHomeSearchOptions(categories, metrics) {
  const options = new Map();
  categories.forEach((category) => {
    options.set(category.name.toLowerCase(), { value: category.name, isArchived: false });
  });
  metrics.forEach((metric) => {
    const value = `${metric.isArchived ? '# ' : ''}${metric.name}`;
    options.set(value.toLowerCase(), { value, isArchived: metric.isArchived });
  });
  homeSearchOptions = [...options.values()].sort((a, b) => a.value.localeCompare(b.value));
  renderHomeSearchSuggestions();
}

function isStandalonePwa() {
  return window.matchMedia?.('(display-mode: standalone)').matches === true
    || navigator.standalone === true;
}

function updateBackupBanner() {
  const storedCount = Number(localStorage.getItem('quantifi-unsaved-count') || 0);
  const count = Number.isFinite(storedCount) ? Math.max(0, storedCount) : 0;
  const now = Date.now();
  let unsavedSince = Number(localStorage.getItem('quantifi-unsaved-since') || 0);
  if (count > 0 && !unsavedSince) {
    unsavedSince = now;
    localStorage.setItem('quantifi-unsaved-since', String(unsavedSince));
  }
  ui.unsavedCount.textContent = count;
  const lastExportAt = Number(localStorage.getItem('quantifi-last-export-at') || 0);
  const backupButtonPressedAt = Number(localStorage.getItem(BACKUP_BUTTON_PRESSED_AT_KEY) || 0);
  const reminderAgeStart = Math.max(lastExportAt, backupButtonPressedAt) || unsavedSince;
  const standalonePwa = isStandalonePwa();
  const changeThreshold = standalonePwa ? PWA_BACKUP_CHANGE_THRESHOLD : BACKUP_CHANGE_THRESHOLD;
  const reminderAge = standalonePwa ? PWA_BACKUP_REMINDER_AGE_MS : BACKUP_REMINDER_AGE_MS;
  const shouldRemind = count >= changeThreshold
    || (count > 0 && now - reminderAgeStart >= reminderAge);
  const snoozedUntil = Number(localStorage.getItem('quantifi-backup-snoozed-until') || 0);

  if (backupReminderTimer) {
    clearTimeout(backupReminderTimer);
    backupReminderTimer = null;
  }
  if (!shouldRemind) {
    ui.backupReminderBanner.classList.add('hidden');
    return;
  }
  if (now < snoozedUntil) {
    ui.backupReminderBanner.classList.add('hidden');
    backupReminderTimer = setTimeout(updateBackupBanner, snoozedUntil - now);
    return;
  }

  ui.backupReminderBanner.classList.remove('hidden');
}

function incrementUnsavedCount(amount = 1) {
  const storedCount = Number(localStorage.getItem('quantifi-unsaved-count') || 0);
  const previousCount = Number.isFinite(storedCount) ? Math.max(0, storedCount) : 0;
  const count = previousCount + amount;
  if (previousCount <= 0) localStorage.setItem('quantifi-unsaved-since', String(Date.now()));
  localStorage.setItem('quantifi-unsaved-count', String(count));
  updateBackupBanner();
}

function resetUnsavedCount({ exported = false } = {}) {
  localStorage.setItem('quantifi-unsaved-count', '0');
  localStorage.removeItem('quantifi-unsaved-since');
  localStorage.removeItem('quantifi-backup-snoozed-until');
  if (exported) localStorage.setItem('quantifi-last-export-at', String(Date.now()));
  updateBackupBanner();
}

function snoozeBackupReminder() {
  localStorage.setItem('quantifi-backup-snoozed-until', String(Date.now() + BACKUP_SNOOZE_MS));
  updateBackupBanner();
}

function loadVisibleNutritionNutrients() {
  const saved = localStorage.getItem(NUTRITION_VISIBILITY_KEY);
  if (!saved) return new Set(NUTRIENTS.map((nutrient) => nutrient.id));
  try {
    const parsed = JSON.parse(saved);
    if (!Array.isArray(parsed)) throw new Error('Stored nutrient visibility must be an array.');
    return new Set(parsed.filter((id) => NUTRIENTS.some((nutrient) => nutrient.id === id)));
  } catch (error) {
    console.warn('Could not read nutrition visibility settings:', error);
    return new Set(NUTRIENTS.map((nutrient) => nutrient.id));
  }
}

function localDateString(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function initializeNutritionForm() {
  ui.nutritionValueFields.replaceChildren();
  NUTRIENTS.forEach((nutrient) => {
    const label = document.createElement('label');
    label.textContent = `${nutrient.label} (${nutrient.unit})`;
    const input = document.createElement('input');
    input.id = `nutrition-${nutrient.id}`;
    input.type = 'number';
    input.min = '0';
    input.step = nutrient.decimals ? 'any' : '1';
    input.inputMode = 'decimal';
    input.placeholder = 'Unknown';
    input.autocomplete = 'off';
    label.append(input);
    ui.nutritionValueFields.append(label);
  });
}

function formatNutritionDate(date) {
  return new Date(`${date}T12:00:00`).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function appendNutritionValues(container, values, nutrientIds = null) {
  const nutrients = NUTRIENTS.filter((nutrient) => !nutrientIds || nutrientIds.has(nutrient.id));
  nutrients.forEach((nutrient) => {
    const value = values[nutrient.id];
    if (value === null || value === undefined) return;
    const item = document.createElement('span');
    item.className = 'nutrition-value';
    item.textContent = `${nutrient.label}: ${formatNutrientValue(value, nutrient)}`;
    container.append(item);
  });
}

function initializeNutritionTargetForm() {
  ui.nutritionTargetNutrient.innerHTML = NUTRIENTS
    .map((nutrient) => `<option value="${nutrient.id}">${nutrient.label} (${nutrient.unit})</option>`)
    .join('');
  ui.nutritionTargetEffectiveFrom.value = localDateString();
  updateNutritionTargetFields();
}

function updateNutritionTargetFields() {
  const type = ui.nutritionTargetType.value;
  const nutrient = NUTRIENTS.find((item) => item.id === ui.nutritionTargetNutrient.value);
  const range = type === 'range';
  ui.nutritionTargetRangeFields.classList.toggle('hidden', !range);
  ui.nutritionTargetSingleValueField.classList.toggle('hidden', range);
  ui.nutritionTargetValue.required = !range;
  ui.nutritionTargetMinValue.required = range;
  ui.nutritionTargetMaxValue.required = range;
  const typeLabel = NUTRITION_TARGET_TYPES.find((item) => item.id === type)?.label || 'Target';
  ui.nutritionTargetSingleValueLabel.textContent = `${typeLabel} (${nutrient?.unit || ''})`;
  ui.nutritionTargetMinValue.parentElement.firstChild.textContent = `Minimum (${nutrient?.unit || ''})`;
  ui.nutritionTargetMaxValue.parentElement.firstChild.textContent = `Maximum (${nutrient?.unit || ''})`;
}

function editNutritionTarget(target) {
  setWorkflowSection('nutrition', 'data-nutrition-section', 'data-nutrition-section-button', 'targets');
  ui.nutritionTargetNutrient.value = target.nutrientId;
  ui.nutritionTargetType.value = target.type;
  ui.nutritionTargetValue.value = target.value ?? '';
  ui.nutritionTargetMinValue.value = target.minValue ?? '';
  ui.nutritionTargetMaxValue.value = target.maxValue ?? '';
  ui.nutritionTargetEffectiveFrom.value = target.effectiveFrom;
  ui.nutritionTargetNote.value = target.note || '';
  ui.nutritionTargetFormHeading.textContent = `Change ${NUTRIENTS.find((item) => item.id === target.nutrientId)?.label || 'nutrition'} target`;
  updateNutritionTargetFields();
  ui.nutritionTargetForm.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function resetNutritionTargetForm() {
  ui.nutritionTargetForm.reset();
  ui.nutritionTargetEffectiveFrom.value = localDateString();
  ui.nutritionTargetFormHeading.textContent = 'Add or change a target';
  updateNutritionTargetFields();
}

function getEffectiveNutritionTargets(targets, date = localDateString()) {
  const effectiveTargets = new Map();
  targets
    .filter((target) => target.effectiveFrom <= date)
    .sort((a, b) => a.effectiveFrom.localeCompare(b.effectiveFrom))
    .forEach((target) => effectiveTargets.set(target.nutrientId, target));
  return effectiveTargets;
}

async function renderNutritionTargets() {
  const targets = await listNutritionTargets();
  const today = localDateString();
  const effectiveTargets = getEffectiveNutritionTargets(targets, today);
  ui.nutritionCurrentTargets.replaceChildren();
  ui.nutritionTargetHistory.replaceChildren();

  NUTRIENTS.forEach((nutrient) => {
    const applicable = effectiveTargets.get(nutrient.id);
    const card = document.createElement('article');
    card.className = 'nutrition-target-row';
    const heading = document.createElement('div');
    heading.className = 'nutrition-record-heading';
    const title = document.createElement('h4');
    title.textContent = nutrient.label;
    heading.append(title);
    if (applicable) {
      const edit = document.createElement('button');
      edit.type = 'button';
      edit.className = 'secondary';
      edit.dataset.editNutritionTarget = applicable.id;
      edit.textContent = 'Edit';
      heading.append(edit);
    }
    const value = document.createElement('p');
    value.className = applicable ? 'nutrition-target-value' : 'nutrition-target-value muted-text';
    value.textContent = applicable ? formatNutritionTarget(applicable, nutrient) : 'No target set';
    const date = document.createElement('span');
    date.className = 'nutrition-target-date muted-text';
    date.textContent = applicable ? `Since ${formatNutritionDate(applicable.effectiveFrom)}` : '';
    card.append(heading, value);
    if (applicable) card.append(date);
    ui.nutritionCurrentTargets.append(card);
  });

  if (!targets.length) {
    const empty = document.createElement('p');
    empty.className = 'muted-text';
    empty.textContent = 'No target history yet.';
    ui.nutritionTargetHistory.append(empty);
    return;
  }

  targets.slice().sort((a, b) => (
    b.effectiveFrom.localeCompare(a.effectiveFrom)
    || a.nutrientId.localeCompare(b.nutrientId)
  )).forEach((target) => {
    const nutrient = NUTRIENTS.find((item) => item.id === target.nutrientId);
    const card = document.createElement('article');
    card.className = 'nutrition-record';
    const heading = document.createElement('div');
    heading.className = 'nutrition-record-heading';
    const title = document.createElement('h4');
    title.textContent = `${nutrient.label} · ${formatNutritionDate(target.effectiveFrom)}`;
    const edit = document.createElement('button');
    edit.type = 'button';
    edit.className = 'secondary';
    edit.dataset.editNutritionTarget = target.id;
    edit.textContent = 'Edit';
    heading.append(title, edit);
    const value = document.createElement('p');
    value.className = 'muted-text';
    value.textContent = formatNutritionTarget(target, nutrient);
    card.append(heading, value);
    if (target.note) {
      const note = document.createElement('p');
      note.textContent = target.note;
      card.append(note);
    }
    ui.nutritionTargetHistory.append(card);
  });
}

async function renderNutrition() {
  const days = await listNutritionDays();
  nutritionChartDays = days;
  await renderNutritionTargets();
  ui.nutritionHistory.replaceChildren();
  ui.nutritionVisibilitySettings.replaceChildren();
  renderNutritionTrends(days);

  NUTRIENTS.forEach((nutrient) => {
    const label = document.createElement('label');
    label.className = 'checkbox-label nutrition-visibility-option';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = visibleNutritionNutrients.has(nutrient.id);
    checkbox.dataset.nutrientId = nutrient.id;
    label.append(checkbox, document.createTextNode(nutrient.label));
    ui.nutritionVisibilitySettings.append(label);
  });

  if (!days.length) {
    const empty = document.createElement('p');
    empty.className = 'muted-text';
    empty.textContent = 'No nutrition days yet. Import your Gemini JSON or add a day from Add > Manual entry.';
    ui.nutritionHistory.append(empty);
    return;
  }

  days.forEach((day) => {
    const card = document.createElement('article');
    card.className = 'nutrition-record';
    const heading = document.createElement('div');
    heading.className = 'nutrition-record-heading';
    const title = document.createElement('h4');
    title.textContent = formatNutritionDate(day.date);
    const edit = document.createElement('button');
    edit.type = 'button';
    edit.className = 'secondary';
    edit.dataset.editNutritionDate = day.date;
    edit.textContent = 'Edit';
    heading.append(title, edit);
    const values = document.createElement('div');
    values.className = 'nutrition-values';
    appendNutritionValues(values, day.values, visibleNutritionNutrients);
    if (!values.childElementCount) {
      const empty = document.createElement('span');
      empty.className = 'muted-text';
      empty.textContent = 'No visible nutrient values for this day.';
      values.append(empty);
    }
    card.append(heading, values);
    ui.nutritionHistory.append(card);
  });
}

function renderNutritionTrends(days) {
  ui.nutritionPeriodControl.querySelectorAll('.segment').forEach((button) => {
    const isActive = button.dataset.period === activeNutritionPeriod;
    button.classList.toggle('active', isActive);
    button.setAttribute('aria-pressed', String(isActive));
  });
  ui.nutritionChartContainer.innerHTML = generateNutritionSvgChart(
    filterNutritionDaysForPeriod(days, activeNutritionPeriod)
  );
}

async function showNutritionImportPreview(parsed) {
  pendingNutritionImport = parsed;
  setWorkflowSection('nutrition', 'data-nutrition-section', 'data-nutrition-section-button', 'add');
  setNutritionAddMode('import');
  ui.nutritionImportRecords.replaceChildren();
  const preview = getNutritionPreviewRecords(parsed.records);
  let days;
  try {
    days = await listNutritionDays();
  } catch (error) {
    pendingNutritionImport = null;
    ui.nutritionImportPreview.classList.add('hidden');
    window.alert(`Could not load existing nutrition days: ${error.message}`);
    return;
  }
  const existingDates = new Set(days.map((day) => day.date));
  preview.records.forEach((record) => {
    const card = document.createElement('article');
    card.className = 'nutrition-record';
    const heading = document.createElement('h4');
    heading.textContent = `${formatNutritionDate(record.date)}${existingDates.has(record.date) ? ' — will replace existing day' : ''}`;
    const values = document.createElement('div');
    values.className = 'nutrition-values';
    appendNutritionValues(values, record.values);
    card.append(heading, values);
    ui.nutritionImportRecords.append(card);
  });

  const omittedSummary = preview.omittedCount
    ? ` Showing ${preview.records.length}; ${preview.omittedCount} additional day${preview.omittedCount === 1 ? '' : 's'} omitted from preview.`
    : '';
  ui.nutritionImportSummary.textContent = `${preview.totalCount} day${preview.totalCount === 1 ? '' : 's'} ready to import.${omittedSummary} Existing dates will be replaced; other dates are unchanged.`;
  if (parsed.unknownFields.length) {
    ui.nutritionImportWarning.textContent = `Unrecognized fields will be ignored: ${parsed.unknownFields.join(', ')}.`;
    ui.nutritionImportWarning.classList.remove('hidden');
  } else {
    ui.nutritionImportWarning.classList.add('hidden');
    ui.nutritionImportWarning.textContent = '';
  }
  ui.nutritionImportPreview.classList.remove('hidden');
}

function resetNutritionImportPreview() {
  pendingNutritionImport = null;
  ui.nutritionImportFile.value = '';
  ui.nutritionImportPreview.classList.add('hidden');
  ui.nutritionImportRecords.replaceChildren();
}

function editNutritionDay(day) {
  setWorkflowSection('nutrition', 'data-nutrition-section', 'data-nutrition-section-button', 'add');
  setNutritionAddMode('manual');
  ui.nutritionDate.value = day.date;
  NUTRIENTS.forEach((nutrient) => {
    const input = ui.nutritionValueFields.querySelector(`#nutrition-${nutrient.id}`);
    input.value = day.values[nutrient.id] ?? '';
  });
  ui.nutritionEditorHeading.textContent = `Edit nutrition for ${formatNutritionDate(day.date)}`;
  ui.nutritionDayForm.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function setWorkflowSection(viewName, sectionAttribute, buttonAttribute, selectedSection, scope = null) {
  const root = scope || document.querySelector(`#view-${viewName}`);
  root.querySelectorAll(`[${buttonAttribute}]`).forEach((button) => {
    const isActive = button.getAttribute(buttonAttribute) === selectedSection;
    button.classList.toggle('active', isActive);
    button.setAttribute('aria-pressed', String(isActive));
  });
  root.querySelectorAll(`[${sectionAttribute}]`).forEach((section) => {
    section.classList.toggle('hidden', section.getAttribute(sectionAttribute) !== selectedSection);
  });
}

function setNutritionAddMode(mode) {
  setWorkflowSection(
    'nutrition',
    'data-nutrition-add-mode',
    'data-nutrition-add-mode-button',
    mode,
    document.querySelector('#nutritionAddSection'),
  );
}

function resetEntryFormDateTime() {
  const now = new Date();
  const dateStr = now.toISOString().split('T')[0];
  const timeStr = now.toTimeString().slice(0, 5);
  if (ui.entryDate) ui.entryDate.value = dateStr;
  if (ui.entryTime) ui.entryTime.value = timeStr;
}

async function initializeDatabase() {
  // Initialize light/dark theme preference
  const savedTheme = localStorage.getItem('quantifi-pwa-theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  if (ui.themeToggle) {
    ui.themeToggle.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('quantifi-pwa-theme', newTheme);
    });
  }

  const quickStartDismissed = localStorage.getItem(QUICK_START_DISMISSED_KEY) === 'true';
  const quickStartNeverShow = localStorage.getItem(QUICK_START_NEVER_SHOW_KEY) === 'true';
  ui.quickStartCard.classList.toggle('hidden', quickStartDismissed || quickStartNeverShow);
  ui.showQuickStart.classList.toggle('hidden', !quickStartDismissed || quickStartNeverShow);
  await seedBaseData();
  try {
    await migrateLegacyNutritionDays();
    await listNutritionMetrics();
    initializeNutritionTargetForm();
  } catch (error) {
    console.error('Nutrition setup error:', error);
    window.alert(`Nutrition setup failed: ${error.message}`);
  }
  initializeNutritionForm();
  ui.nutritionDate.value = localDateString();
  resetEntryFormDateTime();
  resetChangeFormDateTime();
  updateBackupBanner();
  renderAll();
}

async function renderAll() {
  await renderMetricDropdown();
  await renderHome();
  await renderLogs();
  await renderStats();
  await renderSettings();
  await workoutsView.render();
  await renderNutrition();
}

async function syncAddFormMode() {
  const metrics = await listMetrics(false);
  const metric = metrics.find((item) => item.id === ui.metricSelect.value) || null;

  const isStrength = metric?.metricKind === 'strength_session';
  ui.numericValueField.classList.toggle('hidden', isStrength);
  ui.strengthWorkoutFields.classList.toggle('hidden', !isStrength);

  const isScore = metric?.metricKind === 'score' || metric?.unitType === 'integer_range';
  ui.targetActionField.classList.toggle('hidden', isScore);
  ui.entryFields.classList.toggle('strength-mode', isStrength);

  if (isStrength) {
    const loadUnit = metric.unitName || 'kg';
    const strengthMeasure = metric.strengthMeasure || 'reps';
    ui.strengthLoadLabel.textContent = `Load (${loadUnit})`;
    ui.strengthMeasureLabel.textContent = strengthMeasure === 'duration' ? 'Hold (seconds)' : 'Reps';
    ui.strengthRepsInput.step = strengthMeasure === 'duration' ? 'any' : '1';
    ui.strengthRepsInput.min = strengthMeasure === 'duration' ? '0.01' : '1';
    if (!strengthInputsDirty) ui.strengthRepsInput.value = strengthMeasure === 'duration' ? '30' : '5';
    ui.strengthLoadInput.required = strengthMeasure !== 'duration';
    strengthSetEditor.setLoadUnit(loadUnit);
    strengthSetEditor.setMeasure(strengthMeasure, Number(ui.strengthRepsInput.value));
    const [entries] = await Promise.all([listEntries()]);
    const metricEntries = entries.filter((entry) => entry.metricId === metric.id);
    const lastEntry = metricEntries.sort((a, b) => new Date(b.recordedAt) - new Date(a.recordedAt))[0];
    if (strengthMeasure === 'duration' || suppressStrengthLoadPrefill) {
      ui.strengthLoadInput.value = '';
    } else if (!strengthInputsDirty) {
      ui.strengthLoadInput.value = lastEntry?.loadValue ?? lastEntry?.loadKg ?? lastEntry?.value ?? 0;
    }
    
    if (lastEntry && Array.isArray(lastEntry.sets) && lastEntry.sets.length > 0) {
      const formattedSets = lastEntry.sets
        .map((set, index) => strengthMeasure === 'duration'
          ? `Set ${index + 1}: ${set.durationSeconds} sec${set.loadValue === undefined ? '' : ` · ${set.loadValue} ${loadUnit}`}`
          : `Set ${index + 1}: ${Number(set.loadValue ?? set.loadKg ?? set.load_kg ?? 0).toFixed(1)} ${loadUnit} × ${set.reps} reps`)
        .join(' — ');
      const dateStr = new Date(lastEntry.recordedAt).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
      ui.strengthBaseline.innerHTML = `<strong>📊 Previous Session (${dateStr}):</strong><br>${formattedSets}`;
      ui.strengthBaseline.classList.remove('hidden');
    } else {
      ui.strengthBaseline.innerHTML = '';
      ui.strengthBaseline.classList.add('hidden');
    }

    strengthSetEditor.render();
  }
}

async function renderMetricDropdown() {
  const [metrics, entries, categories] = await Promise.all([
    listMetrics(false).then((rows) => rows.filter((metric) => !metric.nutritionId)),
    listEntries(),
    listCategories(),
  ]);

  // Render date pills
  if (ui.entryDatePills && !ui.entryDatePills.children.length) {
    ui.entryDatePills.innerHTML = ['Now', 'Yesterday', 'Custom']
      .map((opt) => `<button type="button" class="pill ${opt === 'Now' ? 'active' : ''}" data-date="${opt}">${opt}</button>`)
      .join('');
    
    // Set default date/time for Now
    const now = new Date();
    if (ui.entryDate) ui.entryDate.value = now.toISOString().split('T')[0];
    if (ui.entryTime) ui.entryTime.value = now.toTimeString().slice(0, 5);
  }

  // Render target action pills
  if (ui.targetActionPills && !ui.targetActionPills.children.length) {
    ui.targetActionPills.innerHTML = ['Reduce', 'Stay', 'Increase']
      .map((opt) => `<button type="button" class="pill" data-target="${opt}">${opt}</button>`)
      .join('');
  }

  if (addSelectedMetricId && !metrics.some((metric) => metric.id === addSelectedMetricId)) {
    addSelectedMetricId = null;
  }
  let filteredMetrics = filterMetricsByView(activeFilters.add, metrics, entries, categories);
  const currentMetric = metrics.find((metric) => metric.id === addSelectedMetricId);
  if (currentMetric && !filteredMetrics.some((metric) => metric.id === currentMetric.id)) {
    filteredMetrics = [...filteredMetrics, currentMetric];
  }
  filteredMetrics = sortMetricsByRecentEntry(filteredMetrics, entries);
  ui.metricSelectSearch.value = addMetricSearchTerm;
  addMetricCandidates = filteredMetrics;
  addMetricCategories = categories;
  renderAddMetricSelect();
  await syncAddFormMode();
}

function renderAddMetricSelect() {
  const currentMetricIsAvailable = addMetricCandidates.some((metric) => metric.id === addSelectedMetricId);
  const selectedMetricId = currentMetricIsAvailable ? addSelectedMetricId : '';
  ui.metricSelect.innerHTML = addMetricCandidates
    .map((metric) => `<option value="${metric.id}">${metric.name}</option>`)
    .join('');
  ui.metricSelect.value = selectedMetricId || '';
  ui.entryFields.disabled = !selectedMetricId;
  ui.entryFieldsHint.classList.toggle('hidden', Boolean(selectedMetricId));
  const selectedMetric = addMetricCandidates.find((metric) => metric.id === selectedMetricId);
  renderMetricPicker({
    selectedContainer: ui.addSelectedMetric,
    pickerContainer: ui.addMetricPicker,
    suggestionsContainer: ui.addMetricSuggestions,
    searchInput: ui.metricSelectSearch,
    clearButton: ui.addMetricClear,
    metrics: addMetricCandidates,
    categories: addMetricCategories,
    selectedMetric,
    isOpen: addMetricPickerOpen,
  });
}

function hasEntryValues() {
  const selectedMetric = addMetricCandidates.find((metric) => metric.id === addSelectedMetricId);
  const strengthMeasure = selectedMetric?.strengthMeasure || 'reps';
  const defaultMeasureValue = strengthMeasure === 'duration' ? '30' : '5';
  return Boolean(
    ui.entryValue.value.trim()
    || strengthSetEditor.getSets().length
    || (
      strengthInputsDirty
      && (ui.strengthLoadInput.value.trim() || ui.strengthRepsInput.value !== defaultMeasureValue)
    )
    || ui.targetActionPills.querySelector('.pill.active')
  );
}

function clearEntryValues() {
  ui.entryValue.value = '';
  ui.strengthLoadInput.value = '';
  ui.strengthRepsInput.value = '5';
  strengthSetEditor.clear();
  strengthInputsDirty = false;
  ui.targetActionPills.querySelectorAll('.pill').forEach((pill) => {
    pill.classList.remove('active');
  });
}

function requestMetricSwitchChoice(canKeepValues) {
  return new Promise((resolve) => {
    metricSwitchChoiceResolver = resolve;
    ui.keepMetricValues.classList.toggle('hidden', !canKeepValues);
    ui.metricSwitchModal.classList.remove('hidden');
    ui.cancelMetricSwitch.focus();
  });
}

function finishMetricSwitchChoice(choice) {
  if (!metricSwitchChoiceResolver) return;
  ui.metricSwitchModal.classList.add('hidden');
  const resolve = metricSwitchChoiceResolver;
  metricSwitchChoiceResolver = null;
  resolve(choice);
}

async function changeAddMetric(metricId) {
  if (metricId === addSelectedMetricId) return true;

  const metrics = await listMetrics(false);
  const metric = metrics.find((item) => item.id === metricId);
  if (!metric) return false;

  if (hasEntryValues()) {
    const currentMetric = metrics.find((item) => item.id === addSelectedMetricId);
    const canKeepValues = canKeepMetricValues(currentMetric, metric);
    ui.metricSwitchMessage.textContent = canKeepValues
      ? `You have entered data for ${currentMetric.name}. `
        + `Switch to ${metric.name}? You can keep the entered values or clear them.`
      : `You have entered data for ${currentMetric?.name || 'the current metric'}. `
        + `Switching to ${metric.name} uses a different metric type, so the entered values must be cleared.`;
    const choice = await requestMetricSwitchChoice(canKeepValues);
    if (choice === 'cancel') return false;
    if (choice === 'clear') {
      clearEntryValues();
      suppressStrengthLoadPrefill = true;
    } else {
      suppressStrengthLoadPrefill = false;
    }
  } else {
    suppressStrengthLoadPrefill = false;
  }

  addSelectedMetricId = metricId;
  selectMetric(metricId);
  const [entries, categories] = await Promise.all([listEntries(), listCategories()]);
  addMetricCategories = categories;
  addMetricCandidates = sortMetricsByRecentEntry(
    filterMetricsByView(activeFilters.add, metrics, entries, categories),
    entries
  );
  ui.metricSelect.value = metricId;
  renderAddMetricSelect();
  await syncAddFormMode();
  return true;
}

async function renderHome() {
  console.log('renderHome called');
  const [metrics, entries, categories, nutritionTargets] = await Promise.all([
    listMetrics(true),
    listEntries(),
    listCategories(),
    listNutritionTargets(),
  ]);
  const effectiveNutritionTargets = getEffectiveNutritionTargets(nutritionTargets);
  console.log('Metrics:', metrics.length, 'Active:', metrics.filter(m => !m.isArchived).length);

  const visibleMetrics = showArchivedMetrics ? metrics : metrics.filter((m) => !m.isArchived);
  const hasActiveMetrics = metrics.some((metric) => !metric.isArchived);
  setHomeSearchOptions(categories, visibleMetrics);
  let filteredMetrics = filterMetricsByView(activeFilters.home, visibleMetrics, entries, categories);
  const currentSearchTerm = ui.homeSearch ? ui.homeSearch.value.trim().toLowerCase() : homeSearchTerm;
  homeSearchTerm = currentSearchTerm;
  updateHomeSearchClearButton();
  filteredMetrics = filterMetricsBySearch(filteredMetrics, categories, currentSearchTerm);

  const categoryMap = Object.fromEntries(categories.map((category) => [category.id, category.name]));
  filteredMetrics = filteredMetrics.filter((metric) => (
    !metric.nutritionId || visibleNutritionNutrients.has(metric.nutritionId)
  ));

  ui.metricGrid.innerHTML = filteredMetrics.map((metric) => {
    const metricEntries = entries.filter((entry) => entry.metricId === metric.id);
    const sortedEntries = [...metricEntries].sort((a, b) => new Date(a.recordedAt) - new Date(b.recordedAt));
    const latest = sortedEntries[sortedEntries.length - 1];
    const categoryName = categoryMap[metric.categoryId] || 'General';

    const cleanValues = sortedEntries
      .map(e => metric.metricKind === 'strength_session'
        ? (metric.strengthMeasure === 'duration'
          ? computeDurationValue(e, 'Max Duration')
          : computeStrengthValue(e, 'Total Volume'))
        : e.value)
      .filter(v => v !== null && v !== undefined && !Number.isNaN(v));
    const sparkValues = cleanValues.slice(-12);

    const safeCatName = categoryName.toUpperCase();
    const safeMName = metric.name.charAt(0).toUpperCase() + metric.name.slice(1);
    const nutritionTarget = metric.nutritionId
      ? effectiveNutritionTargets.get(metric.nutritionId)
      : null;
    const nutrient = NUTRIENTS.find((item) => item.id === metric.nutritionId);
    const nutritionTargetHtml = nutritionTarget && nutrient
      ? `<div class="nutrition-card-target">Target: ${formatNutritionTarget(nutritionTarget, nutrient)}</div>`
      : '';
    
    let latestLabel = '—';
    let suffix = '';
    if (latest) {
      if (metric.metricKind === 'strength_session') {
        const aggValue = metric.strengthMeasure === 'duration'
          ? computeDurationValue(latest, 'Max Duration')
          : computeStrengthValue(latest, activeVizSettings.strengthAgg || 'Max Load');
        latestLabel = aggValue !== null && aggValue !== undefined ? Number(aggValue).toFixed(1) : '—';
        suffix = metric.strengthMeasure === 'duration' ? ' sec' : metric.unitName ? ` ${metric.unitName}` : '';
      } else {
        latestLabel = latest.value !== null && latest.value !== undefined ? latest.value : '—';
        suffix = metric.unitName ? ` ${metric.unitName}` : '';
      }
    }

    const latestValueStr = latestLabel !== '—' ? `${latestLabel}${suffix}` : '';
    const lastDateStr = latest ? new Date(latest.recordedAt).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : '';

    let targetHtml = '';
    if (latest && latest.targetAction) {
      const colorMap = {
        'Increase': '#10b981',
        'Reduce': '#ef4444',
        'Stay': '#3b82f6',
        'Pause': '#64748b',
      };
      const tx = colorMap[latest.targetAction] || '#64748b';
      targetHtml = `<div class="overview-target" style="color: ${tx}; border-color: ${tx};">${latest.targetAction.toUpperCase()}</div>`;
    }

    const sparkSvg = renderSparkline(sparkValues, 'var(--primary)', {
      kind: metric.metricKind || metric.unitType || 'quantitative',
      higherIsBetter: metric.higherIsBetter !== false,
      rangeStart: metric.rangeStart,
      rangeEnd: metric.rangeEnd,
    });

    return `
      <div class="overview-card${metric.nutritionId ? ' overview-card--nutrition' : ''}" data-metric-id="${metric.id}">
        <div class="overview-title-row">
          <div class="title-left">
            <span class="overview-cat${metric.nutritionId ? ' nutrition-card-badge' : ''}">${metric.nutritionId ? 'Nutrition' : safeCatName}</span>
            <span class="overview-name" title="${safeMName}">${metric.isArchived ? '# ' : ''}${safeMName}</span>
            ${metric.isArchived ? '<span class="archived-metric-badge">Archived</span>' : ''}
          </div>
          <div class="title-right">
            ${latestValueStr ? `<span class="metric-value">${latestValueStr}</span>` : ''}
            ${lastDateStr ? `<span class="metric-date">${lastDateStr}</span>` : ''}
          </div>
        </div>
        ${nutritionTargetHtml}
        <div class="overview-spark-wrap">
          ${targetHtml}
          ${sparkSvg}
        </div>
        <div class="card-pills">
          ${metric.isArchived ? '' : `<button class="card-pill" data-action="${metric.nutritionId ? 'nutrition' : 'add'}" data-id="${metric.id}" title="${metric.nutritionId ? 'Add daily nutrition' : 'Add Entry'}">➕</button>`}
          ${metric.metricKind === 'strength_session' ? `<button class="card-pill" data-action="last-session" data-id="${metric.id}" title="Last session">💡</button>` : ''}
          <button class="card-pill" data-action="stats" data-id="${metric.id}" title="View Stats">📊</button>
          ${metric.nutritionId ? '' : `<button class="card-pill" data-action="settings" data-id="${metric.id}" title="Edit Metric">⚙️</button>
          <button class="card-pill" data-action="edit-entries" data-id="${metric.id}" title="Edit Entries">📋</button>`}
        </div>
      </div>
    `;
  }).join('') || (currentSearchTerm.startsWith('#') && !showArchivedMetrics
    ? '<p>No archived metrics shown. Enable “Show archived metrics in search and Stats” in Settings → Default behaviour.</p>'
    : '<p>No metrics match this filter.</p>');
  ui.homeNoMetrics.classList.toggle('hidden', hasActiveMetrics || Boolean(currentSearchTerm));
}

async function renderLogs() {
  const [events, categories] = await Promise.all([
    listChangeEvents(),
    listCategories(),
  ]);
  const catMap = Object.fromEntries(categories.map((item) => [item.id, item.name]));
  
  if (ui.changeCategory) {
    ui.changeCategory.innerHTML = '<option value="">Uncategorized</option>' + categories
      .map(c => `<option value="${c.id}">${c.name.charAt(0).toUpperCase() + c.name.slice(1)}</option>`)
      .join('');
  }

  const showArchived = ui.logShowArchived?.checked || false;
  const sortedEvents = [...events].sort((a, b) => {
    const aTime = showArchived
      ? new Date(a.endAt || a.recordedAt).getTime()
      : new Date(a.recordedAt).getTime();
    const bTime = showArchived
      ? new Date(b.endAt || b.recordedAt).getTime()
      : new Date(b.recordedAt).getTime();
    return bTime - aTime;
  });

  let filteredEvents = showArchived
    ? sortedEvents
    : sortedEvents.filter(e => !e.isArchived);

  const filter = activeFilters.log || 'Recent';
  if (filter !== 'Recent') {
    filteredEvents = filteredEvents.filter(e => {
      const catName = catMap[e.categoryId] || 'Uncategorized';
      return catName.toLowerCase() === filter.toLowerCase();
    });
  }

  if (filter === 'Recent') {
    filteredEvents = filteredEvents.slice(0, 8);
  }

  ui.changeList.innerHTML = filteredEvents.map((event) => {
    const isEditing = editingEventId === event.id;
    const isEnding = endingEventId === event.id;
    const isReviving = revivingEventId === event.id;

    const recordedDateStr = new Date(event.recordedAt).toISOString().split('T')[0];
    const recordedTimeStr = new Date(event.recordedAt).toTimeString().slice(0, 5);

    if (isEditing) {
      return `
        <div class="item edit-mode" style="padding: 12px; border: 1px solid var(--primary); border-radius: 8px; margin-bottom: 8px;">
          <strong>Edit Change</strong>
          <form class="stacked-form" data-edit-form-id="${event.id}" style="margin-top: 8px;">
            <label>
              Category
              <select class="edit-category">
                <option value="">Uncategorized</option>
                ${categories.map(c => `<option value="${c.id}" ${c.id === event.categoryId ? 'selected' : ''}>${c.name.charAt(0).toUpperCase() + c.name.slice(1)}</option>`).join('')}
              </select>
            </label>
            <label>
              Title
              <input type="text" class="edit-title" value="${event.title}" required />
            </label>
            <label>
              Notes (Markdown supported)
              <textarea class="edit-notes" rows="4">${event.notes || ''}</textarea>
            </label>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
              <label>
                Date
                <input type="date" class="edit-date" value="${recordedDateStr}" required />
              </label>
              <label>
                Time
                <input type="time" class="edit-time" value="${recordedTimeStr}" required />
              </label>
            </div>
            <div style="display: flex; gap: 8px; margin-top: 8px;">
              <button type="submit" class="primary" style="flex: 1;">Save Changes</button>
              <button type="button" class="secondary cancel-action" style="flex: 1;">Cancel</button>
            </div>
          </form>
        </div>
      `;
    }

    if (isEnding) {
      const now = new Date();
      const nowDateStr = now.toISOString().split('T')[0];
      const nowTimeStr = now.toTimeString().slice(0, 5);
      return `
        <div class="item edit-mode" style="padding: 12px; border: 1px solid var(--primary); border-radius: 8px; margin-bottom: 8px;">
          <strong>End Change</strong>
          <p style="font-size: 0.85rem; color: var(--muted); margin: 4px 0 8px 0;">Pick the date/time when this change ended.</p>
          <form class="stacked-form" data-end-form-id="${event.id}">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
              <label>
                End Date
                <input type="date" class="end-date" value="${nowDateStr}" required />
              </label>
              <label>
                End Time
                <input type="time" class="end-time" value="${nowTimeStr}" required />
              </label>
            </div>
            <div style="display: flex; gap: 8px; margin-top: 8px;">
              <button type="submit" class="primary" style="flex: 1;">Confirm End Date</button>
              <button type="button" class="secondary cancel-action" style="flex: 1;">Cancel</button>
            </div>
          </form>
        </div>
      `;
    }

    if (isReviving) {
      const now = new Date();
      const nowDateStr = now.toISOString().split('T')[0];
      const nowTimeStr = now.toTimeString().slice(0, 5);
      return `
        <div class="item edit-mode" style="padding: 12px; border: 1px solid var(--primary); border-radius: 8px; margin-bottom: 8px;">
          <strong>Restart Change</strong>
          <p style="font-size: 0.85rem; color: var(--muted); margin: 4px 0 8px 0;">Pick a new start date/time to restart this change.</p>
          <form class="stacked-form" data-revive-form-id="${event.id}">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
              <label>
                New Start Date
                <input type="date" class="revive-date" value="${nowDateStr}" required />
              </label>
              <label>
                New Start Time
                <input type="time" class="revive-time" value="${nowTimeStr}" required />
              </label>
            </div>
            <div style="display: flex; gap: 8px; margin-top: 8px;">
              <button type="submit" class="primary" style="flex: 1;">Confirm New Start Date</button>
              <button type="button" class="secondary cancel-action" style="flex: 1;">Cancel</button>
            </div>
          </form>
        </div>
      `;
    }

    const startStr = new Date(event.recordedAt).toLocaleString(undefined, {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit'
    });
    const endStr = event.endAt ? new Date(event.endAt).toLocaleString(undefined, {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit'
    }) : null;

    const categoryLabel = catMap[event.categoryId] ? catMap[event.categoryId].charAt(0).toUpperCase() + catMap[event.categoryId].slice(1) : 'Uncategorized';
    const metadataStr = event.isArchived
      ? `Category: ${categoryLabel} | Started: ${startStr} | Ended: ${endStr}`
      : `Category: ${categoryLabel} | Started: ${startStr}`;

    const displayedTitle = event.isArchived ? `[Archived] ${event.title}` : event.title;

    return `
      <details class="routine-item" style="margin-bottom: 8px;">
        <summary style="padding: 12px 10px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); cursor: pointer; list-style: none; display: flex; justify-content: space-between; align-items: center;">
          <strong style="font-size: 1.1rem;">${displayedTitle}</strong>
          <span class="collapse-indicator">▶</span>
        </summary>
        <div class="item" style="padding: 12px; border: 1px solid var(--border); border-top: none; border-radius: 0 0 8px 8px; margin-top: -1px; background: var(--surface);">
          <div class="notes-content" style="margin-bottom: 8px; font-size: 0.95rem; line-height: 1.4;">
            ${event.notes ? renderMarkdown(event.notes) : '<span style="color: var(--muted); font-style: italic;">No notes.</span>'}
          </div>
          <div style="margin-bottom: 10px;"><small style="color: var(--muted); font-weight: 500;">${metadataStr}</small></div>
          <div style="display: flex; gap: 6px;">
          ${event.isArchived 
            ? `<button type="button" data-action="revive" data-id="${event.id}" class="primary" style="flex: 1; padding: 6px 8px; min-height: 32px; font-size: 0.85rem;">Restart change</button>`
            : `<button type="button" data-action="end" data-id="${event.id}" class="primary" style="flex: 1; padding: 6px 8px; min-height: 32px; font-size: 0.85rem;">End change</button>`
          }
          <button type="button" data-action="edit-event" data-id="${event.id}" style="flex: 1; padding: 6px 8px; min-height: 32px; font-size: 0.85rem;">Edit</button>
          <button type="button" data-action="delete-event" data-id="${event.id}" style="flex: 1; padding: 6px 8px; min-height: 32px; font-size: 0.85rem;" class="secondary">Delete</button>
        </div>
      </div>
      </details>
    `;
  }).join('') || '<p>No changes yet.</p>';
}

function ensureEntriesTableMarkup() {
  const body = ui.entriesModal.querySelector('.modal-body');
  if (!body) return;
  if (!body.querySelector('#entriesTableContainer')) {
    body.innerHTML = `
      <div id="entriesTableContainer" class="table-container">
        <table id="entriesTable">
          <thead>
            <tr>
              <th>Date</th>
              <th>Value</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="entriesTableBody"></tbody>
        </table>
      </div>
    `;
  }
  ui.entriesTableBody = body.querySelector('#entriesTableBody');
}

async function openStrengthSessionDetails(metricId) {
  const actionId = ++entriesModalActionId;
  const metrics = await listMetrics(true);
  if (actionId !== entriesModalActionId) return;
  const metric = metrics.find((m) => m.id === metricId);
  if (!metric) return;

  const entries = await listEntries();
  if (actionId !== entriesModalActionId) return;
  const metricEntries = entries
    .filter((entry) => entry.metricId === metricId)
    .sort((a, b) => new Date(b.recordedAt) - new Date(a.recordedAt));

  const body = ui.entriesModal.querySelector('.modal-body');
  if (!body) return;

  if (metricEntries.length === 0) {
    body.innerHTML = '<p>No strength sessions recorded yet for this metric.</p>';
  } else {
    const latest = metricEntries[0];
    const loadUnit = metric.unitName || 'kg';
    const strengthMeasure = metric.strengthMeasure || 'reps';
    const recommendation = strengthMeasure === 'duration'
      ? null
      : buildStrengthProgressRecommendation(metricEntries, loadUnit);
    const sets = Array.isArray(latest.sets) ? latest.sets : [];
    const setLines = sets.length
      ? sets.map((set, index) => {
          if (strengthMeasure === 'duration') {
            return `<li>Set ${index + 1}: ${set.durationSeconds} sec${set.loadValue === undefined ? '' : ` · ${set.loadValue} ${loadUnit}`}</li>`;
          }
          const load = Number(set.loadValue ?? set.loadKg ?? set.load_kg ?? 0).toFixed(1);
          const reps = Number(set.reps ?? 0);
          return `<li>Set ${index + 1}: ${load} ${loadUnit} × ${reps} reps</li>`;
        }).join('')
      : `<li>${Number(latest.loadValue ?? latest.loadKg ?? latest.value ?? 0).toFixed(1)} ${loadUnit} × ${Number(latest.reps ?? 0)} reps</li>`;
    const totalVolume = strengthMeasure === 'duration' ? computeDurationValue(latest, 'Total Duration') : computeStrengthValue(latest, 'Total Volume');
    const maxLoad = strengthMeasure === 'duration' ? computeDurationValue(latest, 'Max Duration') : computeStrengthValue(latest, 'Max Load');

    body.innerHTML = `
      <div class="session-detail">
        <p><strong>Last session:</strong> ${new Date(latest.recordedAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</p>
        <ul class="session-sets">${setLines}</ul>
        <p><strong>${strengthMeasure === 'duration' ? 'Total hold time' : 'Total volume'}:</strong> ${Number(totalVolume).toFixed(1)} ${strengthMeasure === 'duration' ? 'sec' : `${loadUnit} × reps`}</p>
        <p><strong>${strengthMeasure === 'duration' ? 'Best hold' : 'Max load'}:</strong> ${Number(maxLoad).toFixed(1)} ${strengthMeasure === 'duration' ? 'sec' : loadUnit}</p>
        <div class="recommendation">
          <strong>Recommendation</strong>
          <p>${recommendation ?? 'No progression recommendation for this session.'}</p>
        </div>
      </div>`;
  }

  ui.entriesModalTitle.textContent = `${metric.name} — Last session`;
  ui.entriesModal.classList.remove('hidden');
}

async function renderStats() {
  const renderRequestId = ++statsRenderRequestId;
  const [metrics, entries, categories] = await Promise.all([
    listMetrics(true),
    listEntries(),
    listCategories(),
  ]);
  if (renderRequestId !== statsRenderRequestId) return;

  const availableMetrics = showArchivedMetrics ? metrics : metrics.filter((m) => !m.isArchived);

  let filteredMetrics = filterMetricsByView(activeFilters.stats, availableMetrics, entries, categories);
  const currentMetric = availableMetrics.find((metric) => metric.id === currentMetricId);
  if (currentMetric && !filteredMetrics.some((metric) => metric.id === currentMetric.id)) {
    filteredMetrics = [...filteredMetrics, currentMetric];
  }
  filteredMetrics = sortMetricsByRecentEntry(filteredMetrics, entries);
  ui.statsMetricSearch.value = statsMetricSearchTerm;
  const metricCandidates = filteredMetrics;

  const currentMetricIsAvailable = metricCandidates.some((metric) => metric.id === currentMetricId);
  const selectedMetricId = currentMetricIsAvailable
    ? currentMetricId
    : metricCandidates[0]?.id ?? '';
  statsMetricCandidates = metricCandidates;
  ui.statsMetricSelect.innerHTML = metricCandidates
    .map((m) => `<option value="${m.id}">${m.isArchived ? '# ' : ''}${m.name}${m.isArchived ? ' (Archived)' : ''}</option>`)
    .join('');
  ui.statsMetricSelect.value = selectedMetricId;
  if (selectedMetricId) selectMetric(selectedMetricId);
  const selectedMetric = metricCandidates.find((m) => m.id === selectedMetricId);
  renderMetricPicker({
    selectedContainer: ui.statsSelectedMetric,
    pickerContainer: ui.statsMetricPicker,
    suggestionsContainer: ui.statsMetricSuggestions,
    searchInput: ui.statsMetricSearch,
    clearButton: ui.statsMetricClear,
    metrics: statsMetricCandidates,
    categories,
    selectedMetric,
    isOpen: statsMetricPickerOpen,
  });

  if (selectedMetric) {
    ui.statsControls.classList.remove('hidden');
    ui.statsChartContainer.classList.remove('hidden');

    const isStrength = selectedMetric.metricKind === 'strength_session';
    ui.statsStrengthControl.classList.toggle('hidden', !isStrength);
    const strengthMeasure = selectedMetric.strengthMeasure || 'reps';
    ui.statsStrengthSelect.innerHTML = (strengthMeasure === 'duration'
      ? ['Max Duration', 'Total Duration']
      : ['Total Volume', 'Max Load', 'Average Load', 'Max e1RM'])
      .map((aggregate) => `<option value="${aggregate}">${aggregate}</option>`)
      .join('');
    if (!Array.from(ui.statsStrengthSelect.options).some((option) => option.value === activeVizSettings.strengthAgg)) {
      activeVizSettings.strengthAgg = strengthMeasure === 'duration' ? 'Max Duration' : 'Max Load';
    }

    activeVizSettings.metricId = selectedMetricId;
    
    const segments = ui.statsPeriodControl.querySelectorAll('.segment');
    segments.forEach((seg) => {
      const isCurrent = seg.dataset.period === activeVizSettings.period;
      seg.classList.toggle('active', isCurrent);
      if (isCurrent) {
        seg.style.background = 'var(--primary, #3b82f6)';
        seg.style.color = 'white';
      } else {
        seg.style.background = 'transparent';
        seg.style.color = 'var(--text-color, #f8fafc)';
      }
    });

    ui.statsZerosToggle.checked = activeVizSettings.zeros;
    ui.statsStrengthSelect.value = activeVizSettings.strengthAgg;

    const processedData = resampleAndProcessData(
      entries,
      selectedMetric,
      activeVizSettings.period,
      activeVizSettings.zeros,
      activeVizSettings.strengthAgg
    );

    ui.statsChartContainer.innerHTML = generateSvgChart(processedData, selectedMetric.strengthMeasure === 'duration'
      ? { ...selectedMetric, unitName: 'sec' }
      : selectedMetric);
  } else {
    ui.statsControls.classList.add('hidden');
    ui.statsChartContainer.classList.add('hidden');
    ui.statsChartContainer.innerHTML = '';
  }

  const selectedSummary = (selectedMetric ? [selectedMetric] : [])
    .map((metric) => {
      const metricEntries = entries.filter((entry) => entry.metricId === metric.id);
      const sortedEntries = [...metricEntries].sort((a, b) => new Date(a.recordedAt) - new Date(b.recordedAt));
      const latestEntry = sortedEntries[sortedEntries.length - 1];

      const values = metricEntries.map((entry) => Number(entry.value)).filter((n) => !Number.isNaN(n));
      const total = values.reduce((sum, value) => sum + value, 0);

      let latestLabel = '—';
      if (latestEntry) {
        if (metric.metricKind === 'strength_session') {
          latestLabel = formatStrengthSession(
            latestEntry,
            metric.unitName || 'kg',
            metric.strengthMeasure || 'reps'
          );
        } else {
          latestLabel = latestEntry.value !== null && latestEntry.value !== undefined ? latestEntry.value : '—';
          if (latestEntry.targetAction) {
            latestLabel += ` (${latestEntry.targetAction})`;
          }
        }
      }

      const isSelected = metric.id === selectedMetricId;
      const highlightStyle = isSelected ? 'border: 1px solid var(--primary); background: rgba(59, 130, 246, 0.05);' : '';

      return `
        <div class="item" style="${highlightStyle} padding: 10px; border-radius: 8px; margin-bottom: 8px; cursor: pointer;" data-stats-metric-id="${metric.id}">
          <strong>${metric.name} ${isSelected ? '★' : ''}</strong>
          <div>${values.length} entries · total ${total.toFixed(1)} · latest ${latestLabel}</div>
        </div>
      `;
    });
  ui.statsSummary.innerHTML = selectedSummary.join('') || '<p>No stats match this filter.</p>';
}

let settingsShowCategories = false;
let isAddingCategory = false;
let isEditingCategory = false;
let selectedCategoryForEdit = null;
let categorySearchTerm = '';
let isAddingMetric = false;
let isEditingMetric = false;
let selectedMetricForEdit = null;
let metricSearchTerm = '';
let currentMetricId = null;
let suppressDetailsReset = false;
let settingsMode = 'categories';
let entriesModalActionId = 0;
let settingsCreateFocusButtonId = null;

function updateSettingsSectionAvailability() {
  const manageAttributes = document.querySelector('#manageAttributesDetails');
  const exclusiveSections = [
    document.querySelector('#backupDetails'),
    document.querySelector('#defaultBehaviourDetails'),
  ];
  if (!manageAttributes) return;

  const isManagingAttributes = manageAttributes.open;
  exclusiveSections.forEach((section) => {
    if (!section) return;
    section.classList.toggle('section-disabled', isManagingAttributes);
    section.querySelector('summary')?.setAttribute('aria-disabled', String(isManagingAttributes));
    if (isManagingAttributes) section.open = false;
  });
}

function activateSettingsMode(mode) {
  settingsMode = mode;
  if (ui.settingsCategoriesPanel) {
    ui.settingsCategoriesPanel.classList.toggle('hidden', mode !== 'categories');
  }
  if (ui.settingsMetricsPanel) {
    ui.settingsMetricsPanel.classList.toggle('hidden', mode !== 'metrics');
  }
  if (ui.showCategoriesBtn && ui.showMetricsBtn) {
    ui.showCategoriesBtn.classList.toggle('active', mode === 'categories');
    ui.showMetricsBtn.classList.toggle('active', mode === 'metrics');
  }
}

if (ui.showCategoriesBtn) {
  ui.showCategoriesBtn.addEventListener('click', async () => {
    activateSettingsMode('categories');
    renderSettings();
  });
}

if (ui.showMetricsBtn) {
  ui.showMetricsBtn.addEventListener('click', async () => {
    activateSettingsMode('metrics');
    renderSettings();
  });
}

ui.showArchivedMetricsToggle.addEventListener('change', async () => {
  showArchivedMetrics = ui.showArchivedMetricsToggle.checked;
  localStorage.setItem(SHOW_ARCHIVED_METRICS_KEY, String(showArchivedMetrics));
  await Promise.all([renderHome(), renderStats()]);
});

async function renderSettings() {
  activateSettingsMode(settingsMode);
  ui.showArchivedMetricsToggle.checked = showArchivedMetrics;
  const [categories, metrics] = await Promise.all([
    listCategories(),
    listMetrics(true),
  ]);

  // Reset UI states
  ui.categoryForm.style.display = isAddingCategory ? 'grid' : 'none';
  ui.categoryEditForm.style.display = isEditingCategory ? 'grid' : 'none';
  ui.categoryEditFields.style.display = isEditingCategory && selectedCategoryForEdit ? 'block' : 'none';

  if (isEditingCategory && selectedCategoryForEdit) {
    const selectedCat = categories.find(c => c.id === selectedCategoryForEdit);
    if (selectedCat) {
      ui.editCategoryName.value = selectedCat.name || '';
      ui.editCategoryDescription.value = selectedCat.description || '';
    }
  }

  await updateDeleteCategoryButtonState(categories);
  renderCategorySearchDatalist(categories);

  // Only show category cards when searching (categorySearchTerm is set) but not when editing a specific category
  if (categorySearchTerm && !selectedCategoryForEdit) {
    // Filter categories based on search term
    const filteredCategories = categories.filter(category => 
      category.name.toLowerCase().includes(categorySearchTerm)
    );

    if (filteredCategories.length > 0) {
      ui.categoryList.innerHTML = filteredCategories.map((category) => `
        <div class="item">
          <strong>${category.name}</strong>
          ${category.description ? `<div style="opacity: 0.7;">${category.description}</div>` : ''}
          <div>
            <button data-action="rename-category" data-id="${category.id}" class="secondary">Rename</button>
            <button data-action="delete-category" data-id="${category.id}" class="secondary">Delete</button>
          </div>
        </div>
      `).join('');
    } else {
      ui.categoryList.innerHTML = '<p class="muted-text" style="padding: 1rem; text-align: center; opacity: 0.6;">No matching categories found</p>';
    }
  } else {
    ui.categoryList.innerHTML = '';
  }
  
  // Always show categories if there are any
  settingsShowCategories = categories.length > 0;

  const currentMetricCategoryId = ui.metricCategory.value;
  ui.metricCategory.innerHTML = '<option value="">No category</option>' + categories
    .map((category) => `<option value="${category.id}">${category.name}</option>`)
    .join('');
  if (categories.some((category) => category.id === currentMetricCategoryId)) {
    ui.metricCategory.value = currentMetricCategoryId;
  }

  // Reset UI states for metrics
  ui.metricForm.style.display = isAddingMetric || (isEditingMetric && selectedMetricForEdit) ? 'grid' : 'none';
  ui.metricEditForm.style.display = isEditingMetric && !isAddingMetric ? 'grid' : 'none';

  if (isEditingMetric && selectedMetricForEdit) {
    const selectedMetric = metrics.find(m => m.id === selectedMetricForEdit);
    if (selectedMetric?.nutritionId) {
      ui.metricForm.style.display = 'none';
      ui.metricEditForm.style.display = 'none';
      ui.metricList.innerHTML = '<p class="muted-text">Nutrition metrics are managed in the Nutrition view. Their names and units are fixed so imports remain consistent.</p>';
      return;
    }
    ui.deleteMetricEdit.hidden = !selectedMetric?.isArchived;
    ui.archiveMetricEdit.classList.toggle('hidden', !selectedMetric);
    if (selectedMetric) {
      if (ui.metricForm.dataset.metricId !== selectedMetric.id) {
        ui.metricName.value = selectedMetric.name || '';
        ui.metricDescription.value = selectedMetric.description || '';
        ui.metricUnit.value = selectedMetric.unitName || '';
        ui.metricType.value = selectedMetric.unitType || 'float';
        ui.metricKind.value = selectedMetric.metricKind || 'quantitative';
        ui.strengthMeasure.value = selectedMetric.strengthMeasure || 'reps';
        ui.metricCategory.value = selectedMetric.categoryId || '';
        ui.metricForm.dataset.metricId = selectedMetric.id;
      }
      ui.archiveMetricEdit.textContent = selectedMetric.isArchived ? 'Unarchive' : 'Archive';
      ui.saveMetricEdit.textContent = 'Save changes';
      ui.strengthMeasureField.classList.toggle('hidden', ui.metricKind.value !== 'strength_session');
    }
  } else {
    ui.metricForm.dataset.metricId = '';
    ui.deleteMetricEdit.hidden = true;
    ui.archiveMetricEdit.classList.add('hidden');
    ui.saveMetricEdit.textContent = 'Create metric';
  }

  renderMetricSearchDatalist(metrics);

  // Don't show metric cards when searching - only show edit fields when there's an exact match
  ui.metricList.innerHTML = '';
}

ui.dismissQuickStart.addEventListener('click', () => {
  localStorage.setItem(QUICK_START_DISMISSED_KEY, 'true');
  ui.quickStartCard.classList.add('hidden');
  ui.showQuickStart.classList.remove('hidden');
});

ui.neverShowQuickStart.addEventListener('click', () => {
  localStorage.setItem(QUICK_START_NEVER_SHOW_KEY, 'true');
  localStorage.removeItem(QUICK_START_DISMISSED_KEY);
  ui.quickStartCard.classList.add('hidden');
  ui.showQuickStart.classList.add('hidden');
});

ui.showQuickStart.addEventListener('click', () => {
  localStorage.removeItem(QUICK_START_DISMISSED_KEY);
  ui.quickStartCard.classList.remove('hidden');
  ui.showQuickStart.classList.add('hidden');
});

ui.createFirstMetric.addEventListener('click', () => ui.homeAddMetricBtn.click());

function startMetricCreation() {
  settingsMode = 'metrics';
  isAddingMetric = true;
  isEditingMetric = false;
  selectedMetricForEdit = null;
  metricSearchTerm = '';
  ui.metricSearch.value = '';
  ui.metricForm.reset();
  ui.strengthMeasureField.classList.add('hidden');
  isAddingCategory = false;
  isEditingCategory = false;
  selectedCategoryForEdit = null;
  ui.addMetricBtn.classList.add('active');
  ui.editMetricBtn.classList.remove('active');
  ui.addCategoryBtn.classList.remove('active');
  ui.editCategoryBtn.classList.remove('active');
}

function startCategoryCreation() {
  settingsMode = 'categories';
  isAddingCategory = true;
  isEditingCategory = false;
  selectedCategoryForEdit = null;
  categorySearchTerm = '';
  ui.categorySearch.value = '';
  ui.categoryForm.reset();
  isAddingMetric = false;
  isEditingMetric = false;
  selectedMetricForEdit = null;
  ui.addCategoryBtn.classList.add('active');
  ui.editCategoryBtn.classList.remove('active');
  ui.addMetricBtn.classList.remove('active');
  ui.editMetricBtn.classList.remove('active');
}

function openSettingsManagement(mode, create = false) {
  if (create && mode === 'metrics') startMetricCreation();
  if (create && mode === 'categories') startCategoryCreation();
  settingsCreateFocusButtonId = create
    ? mode === 'metrics' ? 'addMetricBtn' : 'addCategoryBtn'
    : null;
  settingsMode = mode;
  openManageAttributesOnSettings = true;
  document.querySelector('.tab[data-view="settings"]').click();
}

ui.homeSettingsLink.addEventListener('click', (event) => {
  event.preventDefault();
  openSettingsManagement(settingsMode);
});

ui.homeAddMetricBtn.addEventListener('click', () => openSettingsManagement('metrics', true));
ui.homeAddCategoryBtn.addEventListener('click', () => openSettingsManagement('categories', true));

async function showFocusedView(viewName) {
  ui.primaryNav.classList.add('hidden');
  ui.tabs.forEach((item) => item.classList.toggle('active', item.dataset.view === 'home'));
  ui.views.forEach((view) => view.classList.remove('active'));
  const focusedView = document.querySelector(`#view-${viewName}`);
  focusedView.classList.add('active');

  suppressDetailsReset = true;
  focusedView.querySelectorAll('details').forEach((detail) => detail.removeAttribute('open'));
  suppressDetailsReset = false;

  if (viewName === 'stats') await renderStats();
}

ui.tabs.forEach((tab) => {
  tab.addEventListener('click', async () => {
    ui.primaryNav.classList.remove('hidden');
    if (tab.dataset.view === 'home' && currentMetricId) {
      const metrics = await listMetrics(showArchivedMetrics);
      const selectedMetric = metrics.find((metric) => metric.id === currentMetricId);
      if (selectedMetric && ui.homeSearch) {
        ui.homeSearch.value = selectedMetric.name;
        homeSearchTerm = selectedMetric.name.toLowerCase();
        updateHomeSearchClearButton();
      }
    }

    ui.tabs.forEach((item) => item.classList.remove('active'));
    ui.views.forEach((view) => view.classList.remove('active'));
    tab.classList.add('active');
    const newActiveView = document.querySelector(`#view-${tab.dataset.view}`);
    newActiveView.classList.add('active');
    // Reset all collapsible panels in the new view
    suppressDetailsReset = true;
    newActiveView.querySelectorAll('details').forEach((d) => {
      d.removeAttribute('open');
    });
    suppressDetailsReset = false;
    if (tab.dataset.view === 'settings') updateSettingsSectionAvailability();
    if (tab.dataset.view === 'settings' && openManageAttributesOnSettings) {
      ui.manageAttributesDetails.open = true;
      openManageAttributesOnSettings = false;
    }
    if (tab.dataset.view === 'settings') {
      activateSettingsMode(settingsMode);
      await renderSettings();
      if (settingsCreateFocusButtonId) {
        const button = document.getElementById(settingsCreateFocusButtonId);
        settingsCreateFocusButtonId = null;
        button?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        button?.focus({ preventScroll: true });
      }
    }
    if (tab.dataset.view === 'workouts') {
      await workoutsView.render();
    }
    if (tab.dataset.view === 'nutrition') {
      setWorkflowSection('nutrition', 'data-nutrition-section', 'data-nutrition-section-button', 'add');
      setNutritionAddMode('import');
      await renderNutrition();
    }
    // Render Home when switching to Home tab
    if (tab.dataset.view === 'home') {
      await renderHome();
    }
  });
});

// Auto-close other collapsible panels when one is opened
document.querySelectorAll('details').forEach((detail) => {
  detail.addEventListener('toggle', (event) => {
    if (event.newState === 'open') {
      // Close all other details in the same view
      const view = detail.closest('.view');
      if (view) {
        view.querySelectorAll('details').forEach((d) => {
          if (d !== detail) {
            d.removeAttribute('open');
          }
        });
      }
    }
    if (['manageAttributesDetails', 'backupDetails', 'defaultBehaviourDetails'].includes(detail.id)) {
      updateSettingsSectionAvailability();
    }
  });
});

document.querySelectorAll('#backupDetails > summary, #defaultBehaviourDetails > summary').forEach((summary) => {
  summary.addEventListener('click', (event) => {
    if (document.querySelector('#manageAttributesDetails')?.open) {
      event.preventDefault();
    }
  });
});

// Back button handler
document.querySelectorAll('.back-button').forEach((btn) => {
  btn.addEventListener('click', () => {
    const homeTab = document.querySelector('.tab[data-view="home"]');
    if (homeTab) homeTab.click();
  });
});

ui.metricSelect.addEventListener('change', async () => {
  const changed = await changeAddMetric(ui.metricSelect.value);
  if (!changed) renderAddMetricSelect();
});

ui.metricSelectSearch.addEventListener('input', () => {
  addMetricSearchTerm = ui.metricSelectSearch.value.trim();
  addMetricPickerOpen = true;
  renderAddMetricSelect();
});

ui.metricSelectSearch.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') event.preventDefault();
  if (event.key === 'Escape' && addMetricPickerOpen) {
    addMetricPickerOpen = false;
    setMetricPickerOpen(false, ui.addMetricSuggestions, ui.metricSelectSearch, null, ui.addMetricPicker, ui.addSelectedMetric);
  }
});

ui.addSelectedMetric.addEventListener('click', () => {
  addMetricPickerOpen = !addMetricPickerOpen;
  renderAddMetricSelect();
  if (addMetricPickerOpen) ui.metricSelectSearch.focus();
});

ui.addMetricClear.addEventListener('click', () => {
  addMetricSearchTerm = '';
  ui.metricSelectSearch.value = '';
  addMetricPickerOpen = true;
  renderAddMetricSelect();
  ui.metricSelectSearch.focus();
});

ui.addMetricSuggestions.addEventListener('click', async (event) => {
  const button = event.target.closest('button[data-metric-id]');
  if (!button) return;

  const changed = await changeAddMetric(button.dataset.metricId);
  if (!changed) return;
  addMetricSearchTerm = '';
  ui.metricSelectSearch.value = '';
  addMetricPickerOpen = false;
  renderAddMetricSelect();
});

ui.metricSwitchModal.addEventListener('click', (event) => {
  if (event.target === ui.metricSwitchModal.querySelector('.modal-overlay')) {
    finishMetricSwitchChoice('cancel');
  }
});

ui.metricSwitchModal.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    event.preventDefault();
    finishMetricSwitchChoice('cancel');
  }
});

ui.cancelMetricSwitch.addEventListener('click', () => finishMetricSwitchChoice('cancel'));
ui.keepMetricValues.addEventListener('click', () => finishMetricSwitchChoice('keep'));
ui.clearMetricValues.addEventListener('click', () => finishMetricSwitchChoice('clear'));

ui.strengthLoadInput.addEventListener('input', () => { strengthInputsDirty = true; });
ui.strengthRepsInput.addEventListener('input', () => { strengthInputsDirty = true; });

ui.statsMetricSearch.addEventListener('input', () => {
  statsMetricSearchTerm = ui.statsMetricSearch.value.trim();
  statsMetricPickerOpen = true;
  renderStats();
});

ui.statsMetricSearch.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') event.preventDefault();
  if (event.key === 'Escape' && statsMetricPickerOpen) {
    statsMetricPickerOpen = false;
    setMetricPickerOpen(false, ui.statsMetricSuggestions, ui.statsMetricSearch, null, ui.statsMetricPicker, ui.statsSelectedMetric);
  }
});

ui.statsSelectedMetric.addEventListener('click', () => {
  statsMetricPickerOpen = !statsMetricPickerOpen;
  renderStats();
  if (statsMetricPickerOpen) ui.statsMetricSearch.focus();
});

ui.statsMetricClear.addEventListener('click', () => {
  statsMetricSearchTerm = '';
  ui.statsMetricSearch.value = '';
  statsMetricPickerOpen = true;
  renderStats();
  ui.statsMetricSearch.focus();
});

ui.statsMetricSuggestions.addEventListener('click', (event) => {
  const button = event.target.closest('button[data-metric-id]');
  if (!button) return;

  selectMetric(button.dataset.metricId);
  ui.statsMetricSelect.value = button.dataset.metricId;
  statsMetricSearchTerm = '';
  ui.statsMetricSearch.value = '';
  statsMetricPickerOpen = false;
  renderStats();
});

if (ui.homeSearch) {
  ui.homeSearch.addEventListener('input', () => {
    homeSearchTerm = ui.homeSearch.value.trim().toLowerCase();
    homeSearchSuggestionsOpen = Boolean(ui.homeSearch.value.trim());
    updateHomeSearchClearButton();
    renderHomeSearchSuggestions();
    renderHome();
  });
  ui.homeSearch.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && homeSearchSuggestionsOpen) {
      homeSearchSuggestionsOpen = false;
      renderHomeSearchSuggestions();
    }
  });
}

ui.homeSearchExpand?.addEventListener('click', () => {
  homeSearchSuggestionsOpen = !homeSearchSuggestionsOpen;
  renderHomeSearchSuggestions();
  if (homeSearchSuggestionsOpen) ui.homeSearch.focus();
});

ui.homeSearchClear?.addEventListener('click', () => {
  ui.homeSearch.value = '';
  homeSearchTerm = '';
  homeSearchSuggestionsOpen = false;
  updateHomeSearchClearButton();
  renderHomeSearchSuggestions();
  renderHome();
  ui.homeSearch.focus();
});

document.addEventListener('click', (event) => {
  const eventPath = event.composedPath();
  if (addMetricPickerOpen && !eventPath.includes(ui.addMetricPicker)) {
    addMetricPickerOpen = false;
    setMetricPickerOpen(false, ui.addMetricSuggestions, ui.metricSelectSearch, null, ui.addMetricPicker, ui.addSelectedMetric);
  }
  if (statsMetricPickerOpen && !eventPath.includes(ui.statsMetricPicker)) {
    statsMetricPickerOpen = false;
    setMetricPickerOpen(false, ui.statsMetricSuggestions, ui.statsMetricSearch, null, ui.statsMetricPicker, ui.statsSelectedMetric);
  }
  if (
    homeSearchSuggestionsOpen
    && !event.target.closest('.search-dropdown-control')
  ) {
    homeSearchSuggestionsOpen = false;
    renderHomeSearchSuggestions();
  }
});

ui.entryForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const metricId = ui.metricSelect.value;
    if (!metricId) {
      window.alert('Please select a metric.');
      return;
    }

    const metrics = await listMetrics(false);
    const metric = metrics.find((item) => item.id === metricId) || null;
    const dateValue = ui.entryDate?.value;
    const timeValue = ui.entryTime?.value;
    const valueInput = ui.entryValue;
    
    if (metric?.metricKind !== 'strength_session' && !valueInput?.value) {
      window.alert('Please enter a value.');
      return;
    }
    if (!dateValue || !timeValue) {
      window.alert(`Date: "${dateValue}", Time: "${timeValue}"`);
      return;
    }
  const recordedAt = new Date(`${dateValue}T${timeValue}`).toISOString();

  // Get target action from active pill
  const activeTargetPill = ui.targetActionPills?.querySelector('.pill.active');
  const targetAction = activeTargetPill?.dataset.target ?? null;

  if (editingEntryId) {
    // Update existing entry
    const entry = (await listEntries()).find(e => e.id === editingEntryId);
    if (entry) {
      if (metric?.metricKind === 'strength_session') {
        const strengthSets = strengthSetEditor.getSets();
        if (!strengthSets.length) {
          window.alert('Add at least one set before saving the workout.');
          return;
        }
        const firstSet = strengthSets[0];
        const value = metric.strengthMeasure === 'duration' ? firstSet.durationSeconds : firstSet.loadValue;
        await updateEntry(editingEntryId, {
          metricId,
          value,
          loadValue: firstSet.loadValue ?? null,
          sets: strengthSets,
          targetAction,
          recordedAt,
        });
      } else {
        await updateEntry(editingEntryId, {
          metricId,
          value: Number(valueInput.value),
          targetAction,
          recordedAt,
        });
      }
      editingEntryId = null;
      // Refresh entries table if visible
      const modal = ui.entriesModal;
      if (modal && !modal.classList.contains('hidden')) {
        const metricId = ui.metricSelect.value;
        const metrics = await listMetrics(true);
        const metric = metrics.find(m => m.id === metricId);
        if (metricId && metric) {
          await renderEntriesTable(metricId, metric);
        }
      }
    }
  } else {
    // Create new entry
    if (metric?.metricKind === 'strength_session') {
      const strengthSets = strengthSetEditor.getSets();
      if (!strengthSets.length) {
        window.alert('Add at least one set before saving the workout.');
        return;
      }

      const firstSet = strengthSets[0];
      const value = metric?.strengthMeasure === 'duration' ? firstSet.durationSeconds : firstSet.loadValue;
      await createEntry({
        metricId,
        value,
        loadValue: firstSet.loadValue ?? null,
        sets: strengthSets,
        targetAction,
        recordedAt,
      });
    } else {
      await createEntry({
        metricId,
        value: Number(valueInput.value),
        targetAction,
        recordedAt,
      });
    }
  }
  } catch (e) {
    console.error('Form submission error:', e);
    window.alert('Error: ' + e.message);
    return;
  }

  window.alert('Entry saved!');
  strengthSetEditor.clear();
  strengthInputsDirty = false;
  suppressStrengthLoadPrefill = false;
  ui.targetActionPills.querySelectorAll('.pill').forEach((pill) => pill.classList.remove('active'));
  ui.entryForm.reset();
  resetEntryFormDateTime();
  incrementUnsavedCount();
  renderAll();
});

ui.categoryForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const name = ui.categoryName.value.trim();
  if (!name) return;
  
  // Check for duplicate category names
  const categories = await listCategories();
  const duplicate = categories.some(cat => cat.name.toLowerCase() === name.toLowerCase());
  if (duplicate) {
    window.alert('A category with this name already exists.');
    return;
  }
  
  const description = ui.categoryDescriptionAdd.value.trim();
  await createCategory(name, description);
  window.alert('Category created!');
  isAddingCategory = false;
  ui.categoryForm.reset();
  ui.categoryForm.style.display = 'none';
  
  // Clear active button states
  ui.addCategoryBtn.classList.remove('active');
  
  incrementUnsavedCount();
  renderAll();
});

// Add category button
ui.addCategoryBtn.addEventListener('click', () => {
  startCategoryCreation();
  renderSettings();

  // Update active button states
  ui.addCategoryBtn.classList.add('active');
  ui.editCategoryBtn.classList.remove('active');
  ui.addMetricBtn.classList.remove('active');
  ui.editMetricBtn.classList.remove('active');
});

// Edit category button
ui.editCategoryBtn.addEventListener('click', () => {
  isAddingCategory = false;
  isEditingCategory = true;
  selectedCategoryForEdit = null;
  categorySearchTerm = '';
  ui.categorySearch.value = '';
  ui.categoryEditFields.style.display = 'none';
  ui.categoryEditForm.style.display = 'grid';
  ui.categoryForm.style.display = 'none';
  renderAll(); // Reset the category list filtering
  
  // Update active button states
  ui.addCategoryBtn.classList.remove('active');
  ui.editCategoryBtn.classList.add('active');
});

// Category search with autocomplete and filtering
ui.categorySearch.addEventListener('input', async () => {
  categorySearchTerm = ui.categorySearch.value.trim().toLowerCase();
  selectedCategoryForEdit = null;
  await updateDeleteCategoryButtonState();

  if (categorySearchTerm) {
    const categories = await listCategories();
    const exactMatch = categories.find(cat => cat.name.toLowerCase() === categorySearchTerm);
    if (exactMatch) {
      isAddingCategory = false;
      isEditingCategory = true;
      selectedCategoryForEdit = exactMatch.id;
      ui.categoryEditForm.style.display = 'grid';
      ui.categoryEditFields.style.display = 'block';
      ui.addCategoryBtn.classList.remove('active');
      ui.editCategoryBtn.classList.add('active');
      ui.editCategoryName.value = exactMatch.name || '';
      ui.editCategoryDescription.value = exactMatch.description || '';
      await updateDeleteCategoryButtonState(categories);
      renderSettings();
      return;
    }
  }

  renderSettings();
});

ui.categorySearch.addEventListener('focus', async () => {
  const categories = await listCategories();
  renderCategorySearchDatalist(categories);
  ui.categorySearch.value = ui.categorySearch.value + ' ';
  ui.categorySearch.value = ui.categorySearch.value.trim();
});

ui.categorySearch.addEventListener('change', async () => {
  categorySearchTerm = ui.categorySearch.value.trim().toLowerCase();
  const categories = await listCategories();
  const exactMatch = categories.find(cat => cat.name.toLowerCase() === categorySearchTerm);
  if (exactMatch) {
    isAddingCategory = false;
    isEditingCategory = true;
    selectedCategoryForEdit = exactMatch.id;
    ui.categoryEditForm.style.display = 'grid';
    ui.categoryEditFields.style.display = 'block';
    ui.addCategoryBtn.classList.remove('active');
    ui.editCategoryBtn.classList.add('active');
    ui.editCategoryName.value = exactMatch.name || '';
    ui.editCategoryDescription.value = exactMatch.description || '';
    await updateDeleteCategoryButtonState(categories);
    renderSettings();
    return;
  }
  isAddingCategory = false;
  isEditingCategory = false;
  selectedCategoryForEdit = null;
  await updateDeleteCategoryButtonState(categories);
  renderSettings();
});

// Save category edit
ui.saveCategoryEdit.addEventListener('click', async () => {
  if (!selectedCategoryForEdit) return;
  
  const name = ui.editCategoryName.value.trim();
  if (!name) return;
  
  // Check for duplicate category names (excluding the current category being edited)
  const categories = await listCategories();
  const duplicate = categories.some(cat => 
    cat.id !== selectedCategoryForEdit && cat.name.toLowerCase() === name.toLowerCase()
  );
  if (duplicate) {
    window.alert('A category with this name already exists.');
    return;
  }
  
  const updates = { name: name.toLowerCase() };
  const description = ui.editCategoryDescription.value.trim();
  if (description) {
    updates.description = description;
  }
  
  await updateCategory(selectedCategoryForEdit, updates);
  isEditingCategory = false;
  selectedCategoryForEdit = null;
  categorySearchTerm = '';
  ui.categorySearch.value = '';
  ui.categoryEditForm.style.display = 'none';
  
  // Clear active button states
  ui.addCategoryBtn.classList.remove('active');
  ui.editCategoryBtn.classList.remove('active');
  
  incrementUnsavedCount();
  renderAll();
});

// Cancel category edit
ui.cancelCategoryEdit.addEventListener('click', () => {
  isEditingCategory = false;
  selectedCategoryForEdit = null;
  categorySearchTerm = '';
  ui.categorySearch.value = '';
  ui.categoryEditForm.style.display = 'none';
  ui.categoryEditFields.style.display = 'none';
  
  // Clear active button states
  ui.addCategoryBtn.classList.remove('active');
  ui.editCategoryBtn.classList.remove('active');
  
  renderAll();
});

// Cancel category add
ui.cancelCategory.addEventListener('click', () => {
  isAddingCategory = false;
  ui.categoryForm.style.display = 'none';
  ui.categoryForm.reset();
  
  // Clear active button states
  ui.addCategoryBtn.classList.remove('active');
  ui.editCategoryBtn.classList.remove('active');
  
  renderAll();
});

// Add metric button
ui.addMetricBtn.addEventListener('click', () => {
  startMetricCreation();
  renderSettings();

  // Update active button states
  ui.addMetricBtn.classList.add('active');
  ui.editMetricBtn.classList.remove('active');
  ui.addCategoryBtn.classList.remove('active');
  ui.editCategoryBtn.classList.remove('active');
});

// Edit metric button
ui.editMetricBtn.addEventListener('click', () => {
  isAddingMetric = false;
  isEditingMetric = true;
  selectedMetricForEdit = null;
  metricSearchTerm = '';
  ui.metricSearch.value = '';
  ui.metricEditForm.style.display = 'grid';
  ui.metricForm.style.display = 'none';
  renderAll(); // Reset the metric list filtering
  
  // Update active button states
  ui.addMetricBtn.classList.remove('active');
  ui.editMetricBtn.classList.add('active');
});

// Metric search (native datalist)
ui.metricSearch.addEventListener('input', async () => {
  metricSearchTerm = ui.metricSearch.value.trim().toLowerCase();
  selectedMetricForEdit = null;

  if (metricSearchTerm) {
    const metrics = await listMetrics(true);
    const searchName = metricSearchTerm.replace(/^#\s*/, '');
    const exactMatch = metrics.find(metric => metric.name.toLowerCase() === searchName);
    if (exactMatch) {
      isAddingMetric = false;
      isEditingMetric = true;
      selectedMetricForEdit = exactMatch.id;
      ui.metricEditForm.style.display = 'grid';
      ui.addMetricBtn.classList.remove('active');
      ui.editMetricBtn.classList.add('active');
      renderSettings();
      return;
    }
  }

  renderSettings();
});

ui.metricSearch.addEventListener('focus', async () => {
  const metrics = await listMetrics(true);
  renderMetricSearchDatalist(metrics);
  ui.metricSearch.value = ui.metricSearch.value + ' ';
  ui.metricSearch.value = ui.metricSearch.value.trim();
});

ui.metricSearch.addEventListener('change', async () => {
  metricSearchTerm = ui.metricSearch.value.trim().toLowerCase();
  const metrics = await listMetrics(true);
  const searchName = metricSearchTerm.replace(/^#\s*/, '');
  const exactMatch = metrics.find(metric => metric.name.toLowerCase() === searchName);
  if (exactMatch) {
    isAddingMetric = false;
    isEditingMetric = true;
    selectedMetricForEdit = exactMatch.id;
    ui.metricEditForm.style.display = 'grid';
    ui.addMetricBtn.classList.remove('active');
    ui.editMetricBtn.classList.add('active');
    renderSettings();
    return;
  }
  isAddingMetric = false;
  isEditingMetric = false;
  selectedMetricForEdit = null;
  renderSettings();
});


// Archive metric from edit view
ui.archiveMetricEdit.addEventListener('click', async () => {
  if (!selectedMetricForEdit) return;
  
  const metrics = await listMetrics(true);
  const metric = metrics.find(m => m.id === selectedMetricForEdit);
  if (!metric) return;
  
  // Toggle archive state
  const newArchiveState = !metric.isArchived;
  await updateMetric(selectedMetricForEdit, { isArchived: newArchiveState });
  
  // Update the button text based on new state
  ui.archiveMetricEdit.textContent = newArchiveState ? 'Unarchive' : 'Archive';
  
  incrementUnsavedCount();
  renderAll();
});

ui.deleteMetricEdit.addEventListener('click', async () => {
  if (!selectedMetricForEdit) return;

  const metrics = await listMetrics(true);
  const metric = metrics.find((item) => item.id === selectedMetricForEdit);
  if (!metric) {
    window.alert('Metric not found.');
    return;
  }
  if (!metric.isArchived) {
    window.alert('Only archived metrics can be deleted.');
    return;
  }

  const confirmed = window.confirm(
    `Permanently delete the archived metric "${metric.name}" and all of its entries? This cannot be undone.`
  );
  if (!confirmed) return;

  try {
    await deleteMetric(metric.id);
  } catch (error) {
    console.error('Metric deletion error:', error);
    window.alert(`Unable to delete metric: ${error.message}`);
    return;
  }

  isEditingMetric = false;
  selectedMetricForEdit = null;
  metricSearchTerm = '';
  ui.metricSearch.value = '';
  ui.metricEditForm.style.display = 'none';
  ui.addMetricBtn.classList.remove('active');
  ui.editMetricBtn.classList.remove('active');

  incrementUnsavedCount();
  renderAll();
});

// Cancel metric add
ui.cancelMetric.addEventListener('click', () => {
  isAddingMetric = false;
  isEditingMetric = false;
  selectedMetricForEdit = null;
  metricSearchTerm = '';
  ui.metricSearch.value = '';
  ui.metricForm.style.display = 'none';
  ui.metricForm.reset();
  ui.strengthMeasureField.classList.add('hidden');
  
  // Clear active button states
  ui.addMetricBtn.classList.remove('active');
  ui.editMetricBtn.classList.remove('active');
  
  renderAll();
});

ui.metricKind.addEventListener('change', () => {
  ui.strengthMeasureField.classList.toggle('hidden', ui.metricKind.value !== 'strength_session');
});

ui.metricForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const metricId = isEditingMetric ? selectedMetricForEdit : null;
  const categoryId = ui.metricCategory.value;
  const name = ui.metricName.value.trim();
  if (!name) return;
  const normalizedName = name.toLowerCase();
  if (RESERVED_NUTRITION_METRIC_NAMES.has(normalizedName)) {
    window.alert(`"${name}" is reserved for a nutrition metric. Choose a different metric name.`);
    return;
  }
  
  const metrics = await listMetrics(true);
  const duplicate = metrics.some((metric) => (
    metric.id !== metricId && metric.name.toLowerCase() === name.toLowerCase()
  ));
  if (duplicate) {
    window.alert('A metric with this name already exists.');
    return;
  }
  
  const changes = {
    name: name.toLowerCase(),
    description: ui.metricDescription.value.trim() || null,
    categoryId: categoryId || null,
    unitName: ui.metricUnit.value.trim() || null,
    unitType: ui.metricType.value,
    metricKind: ui.metricKind.value,
    strengthMeasure: ui.metricKind.value === 'strength_session' ? ui.strengthMeasure.value : null,
  };
  try {
    if (metricId) {
      const metric = metrics.find((item) => item.id === metricId);
      if (!metric) {
        window.alert('Metric not found.');
        return;
      }
      await updateMetric(metricId, changes);
    } else {
      await createMetric({ ...changes, higherIsBetter: true, isArchived: false });
      window.alert('Metric created!');
    }
  } catch (error) {
    console.error('Metric save error:', error);
    window.alert(`Unable to save metric: ${error.message}`);
    return;
  }

  isAddingMetric = false;
  isEditingMetric = false;
  selectedMetricForEdit = null;
  ui.metricForm.reset();
  ui.strengthMeasureField.classList.add('hidden');
  ui.metricForm.style.display = 'none';
  ui.metricEditForm.style.display = 'none';
  metricSearchTerm = '';
  ui.metricSearch.value = '';
  
  // Clear active button states
  ui.addMetricBtn.classList.remove('active');
  
  incrementUnsavedCount();
  renderAll();
});

ui.changeForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const catId = ui.changeCategory.value || null;
  const dateVal = ui.changeDate.value;
  const timeVal = ui.changeTime.value;
  const recordedAt = new Date(`${dateVal}T${timeVal}`).toISOString();

  await createChangeEvent({
    title: document.querySelector('#changeTitle').value.trim(),
    notes: document.querySelector('#changeNotes').value.trim() || null,
    recordedAt,
    endAt: null,
    isArchived: false,
    categoryId: catId,
  });
  ui.changeForm.reset();
  resetChangeFormDateTime();
  incrementUnsavedCount();
  renderAll();
});

ui.changeList.addEventListener('click', async (event) => {
  const btn = event.target.closest('[data-action]');
  if (btn) {
    const action = btn.dataset.action;
    const eventId = btn.dataset.id;
    if (action === 'edit-event') {
      editingEventId = eventId;
      endingEventId = null;
      revivingEventId = null;
      renderLogs();
    } else if (action === 'end') {
      endingEventId = eventId;
      editingEventId = null;
      revivingEventId = null;
      renderLogs();
    } else if (action === 'revive') {
      revivingEventId = eventId;
      editingEventId = null;
      endingEventId = null;
      renderLogs();
    } else if (action === 'delete-event') {
      if (window.confirm('Delete this change?')) {
        await deleteChangeEvent(eventId);
        incrementUnsavedCount();
        renderAll();
      }
    }
    return;
  }

  const cancelBtn = event.target.closest('.cancel-action');
  if (cancelBtn) {
    editingEventId = null;
    endingEventId = null;
    revivingEventId = null;
    renderLogs();
    return;
  }
});

// Mutually exclusive collapse for routine items in Existing Routines
// Handle click on summary elements to collapse others first
ui.changeList.addEventListener('click', (event) => {
  const summary = event.target.closest('details.routine-item summary');
  if (summary) {
    const details = summary.parentElement;
    const allRoutineItems = ui.changeList.querySelectorAll('details.routine-item');
    
    // Close all other routine items first
    allRoutineItems.forEach(item => {
      if (item !== details) {
        item.removeAttribute('open');
      }
    });
  }
});

ui.changeList.addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  if (form.hasAttribute('data-edit-form-id')) {
    const eventId = form.getAttribute('data-edit-form-id');
    const title = form.querySelector('.edit-title').value.trim();
    const notes = form.querySelector('.edit-notes').value.trim();
    const catId = form.querySelector('.edit-category').value || null;
    const dateVal = form.querySelector('.edit-date').value;
    const timeVal = form.querySelector('.edit-time').value;
    const recordedAt = new Date(`${dateVal}T${timeVal}`).toISOString();

    await updateChangeEvent(eventId, {
      title,
      notes: notes || null,
      categoryId: catId,
      recordedAt,
    });
    editingEventId = null;
    incrementUnsavedCount();
    renderAll();
  } else if (form.hasAttribute('data-end-form-id')) {
    const eventId = form.getAttribute('data-end-form-id');
    const dateVal = form.querySelector('.end-date').value;
    const timeVal = form.querySelector('.end-time').value;
    const endAt = new Date(`${dateVal}T${timeVal}`).toISOString();

    await updateChangeEvent(eventId, {
      endAt,
      isArchived: true,
    });
    endingEventId = null;
    incrementUnsavedCount();
    renderAll();
  } else if (form.hasAttribute('data-revive-form-id')) {
    const eventId = form.getAttribute('data-revive-form-id');
    const dateVal = form.querySelector('.revive-date').value;
    const timeVal = form.querySelector('.revive-time').value;
    const recordedAt = new Date(`${dateVal}T${timeVal}`).toISOString();

    await updateChangeEvent(eventId, {
      recordedAt,
      endAt: null,
      isArchived: false,
    });
    revivingEventId = null;
    incrementUnsavedCount();
    renderAll();
  }
});

if (ui.logShowArchived) {
  ui.logShowArchived.addEventListener('change', () => {
    activeFilters.log = 'Recent';
    renderLogs();
  });
}


ui.metricList.addEventListener('click', async (event) => {
  const actionButton = event.target.closest('[data-action]');
  if (actionButton) {
    const metricId = actionButton.dataset.id;
    if (actionButton.dataset.action === 'rename-metric') {
      isEditingMetric = true;
      selectedMetricForEdit = metricId;
      ui.metricEditForm.style.display = 'grid';
      ui.addMetricBtn.classList.remove('active');
      ui.editMetricBtn.classList.add('active');
      renderSettings();
      return;
    }
    if (actionButton.dataset.action === 'archive-metric') {
      const metrics = await listMetrics(true);
      const metric = metrics.find((m) => m.id === metricId);
      if (metric) {
        await updateMetric(metricId, { isArchived: !metric.isArchived });
        incrementUnsavedCount();
      }
      metricSearchTerm = '';
      renderAll();
      return;
    }
  }

  const item = event.target.closest('.item[data-metric-id]');
  if (item) {
    isEditingMetric = true;
    selectedMetricForEdit = item.dataset.metricId;
    ui.metricEditForm.style.display = 'grid';
    ui.addMetricBtn.classList.remove('active');
    ui.editMetricBtn.classList.add('active');
    renderSettings();
  }
});

// Reset states when collapsing sections
function setupCollapsibleReset(detailsElement, resetFunction) {
  if (detailsElement) {
    detailsElement.addEventListener('toggle', async function() {
      if (!this.open && !suppressDetailsReset) {
        await resetFunction();
      }
    });
  }
}

// For categories section - find the details element that contains categoryList
const allDetails = document.querySelectorAll('details');
allDetails.forEach(details => {
  if (details.querySelector('#categoryList')) {
    setupCollapsibleReset(details, () => {
      isAddingCategory = false;
      isEditingCategory = false;
      selectedCategoryForEdit = null;
      categorySearchTerm = '';
      ui.categoryName.value = '';
      ui.categorySearch.value = '';
      ui.categoryForm.style.display = 'none';
      ui.categoryEditForm.style.display = 'none';
      ui.categoryEditFields.style.display = 'none';
      ui.addCategoryBtn.classList.remove('active');
      ui.editCategoryBtn.classList.remove('active');
      renderAll();
    });
  }
  
  if (details.querySelector('#metricList')) {
    setupCollapsibleReset(details, () => {
      isAddingMetric = false;
      isEditingMetric = false;
      selectedMetricForEdit = null;
      metricSearchTerm = '';
      ui.metricName.value = '';
      ui.metricSearch.value = '';
      ui.metricForm.style.display = 'none';
      ui.metricEditForm.style.display = 'none';
      ui.addMetricBtn.classList.remove('active');
      ui.editMetricBtn.classList.remove('active');
      renderAll();
    });
  }
});

ui.categoryList.addEventListener('click', async (event) => {
  const actionButton = event.target.closest('[data-action]');
  if (actionButton) {
    const categoryId = actionButton.dataset.id;
    if (actionButton.dataset.action === 'rename-category') {
      isEditingCategory = true;
      selectedCategoryForEdit = categoryId;
      ui.categoryEditForm.style.display = 'grid';
      ui.categoryEditFields.style.display = 'block';
      const categories = await listCategories();
      const selectedCat = categories.find((c) => c.id === categoryId);
      if (selectedCat) {
        ui.editCategoryName.value = selectedCat.name || '';
        ui.editCategoryDescription.value = selectedCat.description || '';
      }
      ui.addCategoryBtn.classList.remove('active');
      ui.editCategoryBtn.classList.add('active');
      return;
    }
    if (actionButton.dataset.action === 'delete-category') {
      await confirmAndDeleteCategory(categoryId);
      return;
    }
  }

  const item = event.target.closest('.item[data-category-id]');
  if (item) {
    isEditingCategory = true;
    selectedCategoryForEdit = item.dataset.categoryId;
    ui.categoryEditForm.style.display = 'grid';
    ui.categoryEditFields.style.display = 'block';
    ui.addCategoryBtn.classList.remove('active');
    ui.editCategoryBtn.classList.add('active');
    const categories = await listCategories();
    const selectedCat = categories.find((c) => c.id === selectedCategoryForEdit);
    if (selectedCat) {
      ui.editCategoryName.value = selectedCat.name || '';
      ui.editCategoryDescription.value = selectedCat.description || '';
    }
  }
});

ui.deleteCategoryBtn.addEventListener('click', async () => {
  const categoryName = ui.categoryName.value.trim() || ui.categorySearch.value.trim();
  const categories = await listCategories();
  const exactMatch = categories.find((c) => c.name.toLowerCase() === categoryName.toLowerCase());
  if (exactMatch) {
    await confirmAndDeleteCategory(exactMatch.id);
  } else {
    window.alert('Type the exact category name to delete it.');
  }
});

async function updateDeleteCategoryButtonState(categories = null) {
  if (!ui.deleteCategoryBtn) return;
  const exactMatch = await findExactCategoryMatch(categories);
  ui.deleteCategoryBtn.disabled = !exactMatch;
}

async function findExactCategoryMatch(categories = null) {
  const allCategories = categories || await listCategories();
  const typedName = ui.categorySearch.value.trim();
  if (!typedName) return null;
  return allCategories.find((c) => c.name.toLowerCase() === typedName.toLowerCase()) || null;
}

function renderCategorySearchDatalist(categories) {
  if (!ui.categorySearchDatalist) return;
  ui.categorySearchDatalist.innerHTML = categories
    .map((category) => `<option value="${category.name}"></option>`) 
    .join('');
}

function renderMetricSearchDatalist(metrics) {
  if (!ui.metricSearchDatalist) return;
  ui.metricSearchDatalist.innerHTML = metrics
    .map((metric) => `<option value="${metric.isArchived ? '# ' : ''}${metric.name}"></option>`)
    .join('');
}

async function confirmAndDeleteCategory(categoryId) {
  const categories = await listCategories();
  const category = categories.find((cat) => cat.id === categoryId);
  if (!category) {
    window.alert('Category not found.');
    return;
  }

  const metrics = await listMetrics(true);
  const impactedMetrics = metrics.filter((metric) => metric.categoryId === categoryId);
  const impactedNames = impactedMetrics.map((metric) => metric.name).join(', ');
  const metricMessage = impactedMetrics.length
    ? `This will remove the category from ${impactedMetrics.length} metric(s): ${impactedNames}.`
    : 'No metrics currently use this category.';

  const confirmed = window.confirm(
    `Delete category "${category.name}"? ${metricMessage}\n\nThis action will remove the category from affected metrics.`
  );
  if (!confirmed) return;

  for (const metric of impactedMetrics) {
    await updateMetric(metric.id, { categoryId: null });
  }
  await deleteCategory(categoryId);
  incrementUnsavedCount();
  ui.categoryName.value = '';
  ui.categorySearch.value = '';
  ui.categoryForm.style.display = 'none';
  ui.categoryEditForm.style.display = 'none';
  ui.categoryEditFields.style.display = 'none';
  isAddingCategory = false;
  isEditingCategory = false;
  selectedCategoryForEdit = null;
  categorySearchTerm = '';
  renderAll();
}

async function triggerCsvExport({ fromBackupReminder = false } = {}) {
  const csv = await exportDataAsCsv();
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  const date = new Date();
  const datePrefix = [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, '0'),
    String(date.getDate()).padStart(2, '0'),
  ].join('-');
  link.href = url;
  link.download = `${datePrefix}-quantifi-pwa-export.csv`;
  link.click();
  URL.revokeObjectURL(url);
  if (fromBackupReminder) {
    localStorage.setItem(BACKUP_BUTTON_PRESSED_AT_KEY, String(Date.now()));
  }
  resetUnsavedCount({ exported: true });
}

ui.exportButton.addEventListener('click', async () => {
  await triggerCsvExport();
});

ui.importButton.addEventListener('click', () => {
  ui.importFile.click();
});

ui.nutritionImportButton.addEventListener('click', () => {
  ui.nutritionImportFile.click();
});

document.querySelector('#nutritionSectionNav').addEventListener('click', (event) => {
  const button = event.target.closest('[data-nutrition-section-button]');
  if (button) {
    setWorkflowSection(
      'nutrition',
      'data-nutrition-section',
      'data-nutrition-section-button',
      button.dataset.nutritionSectionButton,
    );
    if (button.dataset.nutritionSectionButton === 'add') setNutritionAddMode('import');
  }
});

document.querySelector('#nutritionAddModeNav').addEventListener('click', (event) => {
  const button = event.target.closest('[data-nutrition-add-mode-button]');
  if (button) {
    setNutritionAddMode(button.dataset.nutritionAddModeButton);
  }
});

ui.nutritionPeriodControl.addEventListener('click', (event) => {
  const button = event.target.closest('.segment');
  if (!button) return;
  activeNutritionPeriod = button.dataset.period;
  renderNutritionTrends(nutritionChartDays);
});

ui.nutritionChartContainer.addEventListener('click', (event) => {
  const point = event.target.closest('.chart-point');
  const wasOpen = point?.classList.contains('is-open');
  ui.nutritionChartContainer.querySelectorAll('.chart-point.is-open').forEach((openPoint) => {
    openPoint.classList.remove('is-open');
  });
  if (point && !wasOpen) point.classList.add('is-open');
});

document.querySelector('#changeSectionNav').addEventListener('click', (event) => {
  const button = event.target.closest('[data-change-section-button]');
  if (button) {
    setWorkflowSection(
      'log',
      'data-change-section',
      'data-change-section-button',
      button.dataset.changeSectionButton,
    );
  }
});

ui.nutritionReviewJsonButton.addEventListener('click', async () => {
  try {
    const parsed = parseNutritionImportJson(ui.nutritionJsonInput.value);
    await showNutritionImportPreview(parsed);
  } catch (error) {
    window.alert(error.message);
  }
});

ui.nutritionImportFile.addEventListener('change', async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    const parsed = parseNutritionImportJson(await file.text());
    await showNutritionImportPreview(parsed);
  } catch (error) {
    ui.nutritionImportFile.value = '';
    window.alert(error.message);
  }
});

ui.nutritionConfirmImport.addEventListener('click', async () => {
  if (!pendingNutritionImport) return;
  try {
    for (const record of pendingNutritionImport.records) {
      await saveNutritionDay(record);
    }
    const count = pendingNutritionImport.records.length;
    resetNutritionImportPreview();
    ui.nutritionJsonInput.value = '';
    incrementUnsavedCount(count);
    await renderAll();
    window.alert(`Imported or updated ${count} nutrition day${count === 1 ? '' : 's'}.`);
  } catch (error) {
    window.alert(`Nutrition import failed: ${error.message}`);
  }
});

ui.nutritionCancelImport.addEventListener('click', resetNutritionImportPreview);

ui.nutritionVisibilitySettings.addEventListener('change', (event) => {
  const checkbox = event.target.closest('input[data-nutrient-id]');
  if (!checkbox) return;
  if (checkbox.checked) visibleNutritionNutrients.add(checkbox.dataset.nutrientId);
  else visibleNutritionNutrients.delete(checkbox.dataset.nutrientId);
  localStorage.setItem(NUTRITION_VISIBILITY_KEY, JSON.stringify([...visibleNutritionNutrients]));
  renderNutrition();
  renderHome();
});

ui.nutritionHistory.addEventListener('click', async (event) => {
  const button = event.target.closest('button[data-edit-nutrition-date]');
  if (!button) return;
  const day = (await listNutritionDays()).find((item) => item.date === button.dataset.editNutritionDate);
  if (day) editNutritionDay(day);
});

ui.nutritionTargetType.addEventListener('change', updateNutritionTargetFields);
ui.nutritionTargetNutrient.addEventListener('change', updateNutritionTargetFields);

ui.nutritionTargetHistory.addEventListener('click', async (event) => {
  const button = event.target.closest('button[data-edit-nutrition-target]');
  if (!button) return;
  const target = (await listNutritionTargets()).find((item) => item.id === button.dataset.editNutritionTarget);
  if (target) editNutritionTarget(target);
});

ui.nutritionCurrentTargets.addEventListener('click', async (event) => {
  const button = event.target.closest('button[data-edit-nutrition-target]');
  if (!button) return;
  const target = (await listNutritionTargets()).find((item) => item.id === button.dataset.editNutritionTarget);
  if (target) editNutritionTarget(target);
});

ui.nutritionTargetClearButton.addEventListener('click', resetNutritionTargetForm);

ui.nutritionTargetForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const type = ui.nutritionTargetType.value;
  const payload = {
    nutrientId: ui.nutritionTargetNutrient.value,
    type,
    value: type === 'range' || !ui.nutritionTargetValue.value.trim()
      ? null
      : Number(ui.nutritionTargetValue.value),
    minValue: type !== 'range' || !ui.nutritionTargetMinValue.value.trim()
      ? null
      : Number(ui.nutritionTargetMinValue.value),
    maxValue: type !== 'range' || !ui.nutritionTargetMaxValue.value.trim()
      ? null
      : Number(ui.nutritionTargetMaxValue.value),
    effectiveFrom: ui.nutritionTargetEffectiveFrom.value,
    note: ui.nutritionTargetNote.value,
  };
  try {
    await saveNutritionTarget(payload);
    incrementUnsavedCount();
    resetNutritionTargetForm();
    await renderAll();
  } catch (error) {
    window.alert(`Could not save nutrition target: ${error.message}`);
  }
});

ui.nutritionNewDayButton.addEventListener('click', () => {
  ui.nutritionDayForm.reset();
  ui.nutritionDate.value = localDateString();
  ui.nutritionEditorHeading.textContent = 'Add or edit a day';
});

ui.nutritionDayForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const values = {};
  NUTRIENTS.forEach((nutrient) => {
    const input = ui.nutritionValueFields.querySelector(`#nutrition-${nutrient.id}`);
    values[nutrient.id] = input.value.trim() ? Number(input.value) : null;
  });
  try {
    await saveNutritionDay({ date: ui.nutritionDate.value, values });
    incrementUnsavedCount();
    await renderAll();
    ui.nutritionDayForm.reset();
    ui.nutritionDate.value = localDateString();
    ui.nutritionEditorHeading.textContent = 'Add or edit a day';
  } catch (error) {
    window.alert(`Could not save nutrition day: ${error.message}`);
  }
});

ui.importFile.addEventListener('change', async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  const text = await file.text();
  const summary = await importCsvText(text);
  resetUnsavedCount();
  await renderAll();
  alert(`Import complete. ${summary.entries} entries, ${summary.changes} changes, ${summary.workoutPlans} workout plans, ${summary.workoutSessions} workout sessions, and ${summary.nutritionTargets} nutrition targets imported; ${summary.metrics} new metrics created. Matching metrics were reused where possible.`);

  await showFocusedView('stats');
});

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch((error) => console.warn(error));
  });
}

window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  deferredPrompt = event;
  ui.installButton.classList.remove('hidden');
});

ui.installButton.addEventListener('click', async () => {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  await deferredPrompt.userChoice;
  deferredPrompt = null;
  ui.installButton.classList.add('hidden');
});

ui.statsChartContainer.addEventListener('click', (event) => {
  const point = event.target.closest('.chart-point');
  const wasOpen = point?.classList.contains('is-open');
  ui.statsChartContainer.querySelectorAll('.chart-point.is-open').forEach((openPoint) => {
    openPoint.classList.remove('is-open');
  });
  if (point && !wasOpen) point.classList.add('is-open');
});


// Date pills handler
if (ui.entryDatePills) {
  ui.entryDatePills.addEventListener('click', (event) => {
    const pill = event.target.closest('.pill');
    if (!pill) return;
    
    // Update active state
    ui.entryDatePills.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    
    // Show/hide dateTimeFields
    if (pill.dataset.date === 'Custom') {
      ui.dateTimeFields.classList.remove('hidden');
    } else {
      ui.dateTimeFields.classList.add('hidden');
      // Set default date/time based on selection
      const now = new Date();
      if (pill.dataset.date === 'Yesterday') {
        const yesterday = new Date(now);
        yesterday.setDate(yesterday.getDate() - 1);
        ui.entryDate.value = yesterday.toISOString().split('T')[0];
        ui.entryTime.value = '12:00';
      } else {
        ui.entryDate.value = now.toISOString().split('T')[0];
        ui.entryTime.value = now.toTimeString().slice(0, 5);
      }
    }
  });
}

// Target action pills handler
if (ui.targetActionPills) {
  ui.targetActionPills.addEventListener('click', (event) => {
    const pill = event.target.closest('.pill');
    if (!pill) return;

    const wasActive = pill.classList.contains('active');
    ui.targetActionPills.querySelectorAll('.pill').forEach((option) => option.classList.remove('active'));
    if (!wasActive) pill.classList.add('active');
  });
}


ui.metricGrid.addEventListener('click', async (event) => {
  const btn = event.target.closest('.card-pill');
  if (btn) {
    event.stopPropagation();
    const action = btn.dataset.action;
    const metricId = btn.dataset.id;
    if (action === 'add') {
      activeFilters.add = 'Recent';
      const didSwitchMetric = await changeAddMetric(metricId);
      if (!didSwitchMetric) return;
      addMetricSearchTerm = '';
      ui.metricSelectSearch.value = '';
      addMetricPickerOpen = false;
      renderAddMetricSelect();
      const metrics = await listMetrics(false);
      const metric = metrics.find((item) => item.id === metricId);
      if (metric && ui.homeSearch) {
        ui.homeSearch.value = metric.name;
        homeSearchTerm = metric.name.toLowerCase();
        updateHomeSearchClearButton();
      }
      await renderMetricDropdown();
      ui.metricSelect.value = metricId;
      await syncAddFormMode();
      await showFocusedView('add');
    } else if (action === 'nutrition') {
      const nutritionTab = document.querySelector('.tab[data-view="nutrition"]');
      if (nutritionTab) {
        nutritionTab.click();
        setWorkflowSection('nutrition', 'data-nutrition-section', 'data-nutrition-section-button', 'add');
        setNutritionAddMode('manual');
      }
    } else if (action === 'stats') {
      activeFilters.stats = 'Recent';
      selectMetric(metricId);
      statsMetricSearchTerm = '';
      ui.statsMetricSearch.value = '';
      statsMetricPickerOpen = false;
      const metrics = await listMetrics(false);
      const metric = metrics.find((item) => item.id === metricId);
      if (metric && ui.homeSearch) {
        ui.homeSearch.value = metric.name;
        homeSearchTerm = metric.name.toLowerCase();
        updateHomeSearchClearButton();
      }
      await showFocusedView('stats');
    } else if (action === 'settings') {
      isAddingMetric = false;
      isEditingMetric = true;
      selectedMetricForEdit = metricId;
      metricSearchTerm = '';
      const metrics = await listMetrics(true);
      ui.metricSearch.value = metrics.find((metric) => metric.id === metricId)?.name || '';
      openSettingsManagement('metrics');
    } else if (action === 'last-session') {
      await openStrengthSessionDetails(metricId);
    } else if (action === 'edit-entries') {
      await openEntriesModal(metricId);
    }
    return;
  }
});

ui.backupExportButton.addEventListener('click', async () => {
  await triggerCsvExport({ fromBackupReminder: true });
});

ui.backupSnoozeButton.addEventListener('click', snoozeBackupReminder);

document.addEventListener('visibilitychange', () => {
  if (!document.hidden) updateBackupBanner();
});

ui.statsMetricSelect.addEventListener('change', () => {
  selectMetric(ui.statsMetricSelect.value);
  renderStats();
});

ui.statsMetricSuggestions.addEventListener('click', (event) => {
  const button = event.target.closest('button[data-metric-id]');
  if (!button) return;

  selectMetric(button.dataset.metricId);
  ui.statsMetricSelect.value = button.dataset.metricId;
  statsMetricSearchTerm = '';
  ui.statsMetricSearch.value = '';
  statsMetricPickerOpen = false;
  renderStats();
});

ui.statsPeriodControl.addEventListener('click', (event) => {
  const btn = event.target.closest('.segment');
  if (btn) {
    activeVizSettings.period = btn.dataset.period;
    renderStats();
  }
});

ui.statsZerosToggle.addEventListener('change', () => {
  activeVizSettings.zeros = ui.statsZerosToggle.checked;
  renderStats();
});

ui.statsStrengthSelect.addEventListener('change', () => {
  activeVizSettings.strengthAgg = ui.statsStrengthSelect.value;
  renderStats();
});

ui.statsSummary.addEventListener('click', (event) => {
  const row = event.target.closest('[data-stats-metric-id]');
  if (row) {
    const metricId = row.dataset.statsMetricId;
    selectMetric(metricId);
    ui.statsMetricSelect.value = metricId;
    renderStats();
    ui.statsChartContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
});

async function openEntriesModal(metricId) {
  const actionId = ++entriesModalActionId;
  const metrics = await listMetrics(true);
  if (actionId !== entriesModalActionId) return;
  const metric = metrics.find(m => m.id === metricId);
  if (!metric) return;

  ensureEntriesTableMarkup();
  ui.entriesModalTitle.textContent = metric.name;
  await renderEntriesTable(metricId, metric, actionId);
  if (actionId !== entriesModalActionId) return;
  ui.entriesModal.classList.remove('hidden');
}

async function closeEntriesModal() {
  entriesModalActionId += 1;
  ui.entriesModal.classList.add('hidden');
  await renderHome();
}

window.handleEditEntry = async function(entryId, metricId, trElement) {
  const entry = (await listEntries()).find(e => e.id === entryId);
  const metrics = await listMetrics(true);
  const metric = metrics.find(m => m.id === metricId);
  
  if (!entry || !metric) return;
  
  if (metric.metricKind === 'strength_session') {
    const valueCell = trElement.querySelector('td:nth-child(2)');
    const sets = Array.isArray(entry.sets) ? entry.sets : [];
    const strengthMeasure = metric.strengthMeasure || 'reps';
    const editor = document.createElement('div');
    editor.className = 'strength-edit-sets';
    editor.dataset.strengthMeasure = strengthMeasure;
    editor.dataset.loadUnit = metric.unitName || 'kg';
    const setHeader = document.createElement('div');
    setHeader.className = 'strength-edit-set-header';
    setHeader.innerHTML = strengthMeasure === 'duration'
      ? `<span>Load (${metric.unitName || 'kg'}, optional)</span><span>Hold (seconds)</span><span aria-hidden="true"></span>`
      : `<span>Load (${metric.unitName || 'kg'})</span><span>Reps</span><span aria-hidden="true"></span>`;
    editor.append(setHeader);
    sets.forEach((set) => addStrengthSetEditorRow(
      editor,
      set.loadValue ?? set.loadKg ?? set.load_kg,
      strengthMeasure === 'duration' ? set.durationSeconds : set.reps,
      metric.unitName || 'kg',
      strengthMeasure
    ));

    const addButton = document.createElement('button');
    addButton.type = 'button';
    addButton.className = 'secondary';
    addButton.dataset.addStrengthSet = '';
    addButton.textContent = 'Add set';
    editor.append(addButton);
    valueCell.replaceChildren(editor);

    trElement.querySelector('.action-buttons').innerHTML = `
      <button type="button" data-save-strength-session title="Save">✓</button>
      <button type="button" data-cancel-strength-session title="Cancel">✕</button>
    `;
    return;
  }
  
  // Replace value cell with input field
  const valueCell = trElement.querySelector('td:nth-child(2)');
  const originalValue = valueCell.textContent.trim();
  
  valueCell.innerHTML = `
    <input type="number" value="${entry.value}" class="edit-input" 
           data-entry-id="${entryId}" data-metric-id="${metricId}" 
           onkeydown="if(event.key==='Enter') window.saveInlineEdit(this); if(event.key==='Escape') window.cancelInlineEdit(this)">
  `;
  
  // Replace actions with Save/Cancel icons
  const actionsCell = trElement.querySelector('.action-buttons');
  actionsCell.innerHTML = `
    <button onclick="window.saveInlineEdit(this.closest('tr').querySelector('.edit-input'))" class="action-btn save-btn" title="Save">✓</button>
    <button onclick="window.cancelInlineEdit(this.closest('tr').querySelector('.edit-input'))" class="action-btn cancel-btn" title="Cancel">✕</button>
  `;
  
  // Focus the input
  const input = valueCell.querySelector('.edit-input');
  if (input) input.focus();
  
  // Reset global edit state
  editingEntryId = null;
}

function addStrengthSetEditorRow(container, loadValue = '', measureValue = '', loadUnit = 'kg', strengthMeasure = 'reps') {
  const row = document.createElement('div');
  row.className = 'strength-edit-set';
  row.style.cssText = 'display: grid; grid-template-columns: 1fr 1fr auto; gap: 6px; margin-bottom: 6px;';

  const loadInput = document.createElement('input');
  loadInput.type = 'number';
  loadInput.step = '0.5';
  loadInput.min = '0';
  loadInput.required = strengthMeasure !== 'duration';
  loadInput.placeholder = `Load (${loadUnit})`;
  loadInput.dataset.strengthLoad = '';
  loadInput.value = loadValue;

  const measureInput = document.createElement('input');
  measureInput.type = 'number';
  measureInput.step = strengthMeasure === 'duration' ? 'any' : '1';
  measureInput.min = strengthMeasure === 'duration' ? '0.01' : '1';
  measureInput.required = true;
  measureInput.placeholder = strengthMeasure === 'duration' ? 'Hold (seconds)' : 'Reps';
  measureInput.dataset.strengthMeasureValue = '';
  measureInput.value = measureValue;

  const removeButton = document.createElement('button');
  removeButton.type = 'button';
  removeButton.className = 'secondary';
  removeButton.dataset.removeStrengthSet = '';
  removeButton.textContent = '×';
  removeButton.title = 'Remove set';

  row.append(loadInput, measureInput, removeButton);
  container.insertBefore(row, container.querySelector('[data-add-strength-set]'));
}

window.saveStrengthSessionEdit = async function(trElement) {
  const rows = Array.from(trElement.querySelectorAll('.strength-edit-set'));
  if (!rows.length) {
    window.alert('A strength session must contain at least one set.');
    return;
  }

  const sets = [];
  const strengthMeasure = trElement.querySelector('.strength-edit-sets').dataset.strengthMeasure || 'reps';
  for (const row of rows) {
    const loadInput = row.querySelector('[data-strength-load]');
    const measureInput = row.querySelector('[data-strength-measure-value]');
    try {
      sets.push(normalizeStrengthSet(loadInput.value, measureInput.value, strengthMeasure));
    } catch (error) {
      window.alert(error.message);
      (loadInput.value.trim() || strengthMeasure === 'duration' ? measureInput : loadInput).focus();
      return;
    }
  }

  const firstSetValue = strengthMeasure === 'duration'
    ? sets[0].durationSeconds
    : sets[0].loadValue;
  await updateEntry(trElement.dataset.entryId, {
    sets,
    value: firstSetValue,
    loadValue: sets[0].loadValue ?? null,
  });
  const closeModal = window.confirm(
    'Entry updated. Close the edit window? Choose Cancel to edit another entry.'
  );
  incrementUnsavedCount();
  const metricId = trElement.dataset.metricId;
  const metrics = await listMetrics(true);
  const metric = metrics.find((item) => item.id === metricId);
  if (metric) await renderEntriesTable(metricId, metric);

  const statsView = document.querySelector('#view-stats');
  const homeView = document.querySelector('#view-home');
  if (statsView?.classList.contains('active')) await renderStats();
  if (closeModal) {
    await closeEntriesModal();
  } else if (homeView?.classList.contains('active')) {
    await renderHome();
  }
};

window.saveInlineEdit = async function(input) {
  const entryId = input.dataset.entryId;
  const metricId = input.dataset.metricId;
  const newValue = Number(input.value);
  
  if (!Number.isFinite(newValue)) {
    window.alert('Please enter a valid numeric value.');
    input.focus();
    return;
  }

  await updateEntry(entryId, { value: newValue });
  const closeModal = window.confirm(
    'Entry updated. Close the edit window? Choose Cancel to edit another entry.'
  );
  incrementUnsavedCount();
  editingEntryId = null;
  const metrics = await listMetrics(true);
  const metric = metrics.find((item) => item.id === metricId);
  if (metric) await renderEntriesTable(metricId, metric);
  // Refresh active views
  const statsView = document.querySelector('#view-stats');
  const homeView = document.querySelector('#view-home');
  if (statsView && statsView.classList.contains('active')) {
    await renderStats();
  }
  if (closeModal) {
    await closeEntriesModal();
  } else if (homeView && homeView.classList.contains('active')) {
    await renderHome();
  }
}

window.cancelInlineEdit = async function(input) {
  editingEntryId = null;
  const tr = input.closest('tr');
  const metricId = tr.dataset.metricId;
  const metrics = await listMetrics(true);
  const metric = metrics.find(m => m.id === metricId);
  if (metric) {
    await renderEntriesTable(metricId, metric);
  }
}

window.handleDeleteEntry = async function(entryId, metricId, metricName) {
  if (confirm(`Delete this entry for ${metricName}?`)) {
    await deleteEntry(entryId);
    incrementUnsavedCount();
    const metrics = await listMetrics(true);
    const metric = metrics.find(m => m.id === metricId);
    if (metricId && metric) {
      await renderEntriesTable(metricId, metric);
    }
    // Refresh active views
    const statsView = document.querySelector('#view-stats');
    const homeView = document.querySelector('#view-home');
    if (statsView && statsView.classList.contains('active')) {
      await renderStats();
    }
    if (homeView && homeView.classList.contains('active')) {
      await renderHome();
    }
  }
}

async function renderEntriesTable(metricId, metric, actionId = null) {
  const valueHeader = ui.entriesModal.querySelector('#entriesTable thead th:nth-child(2)');
  if (valueHeader) {
    valueHeader.textContent = metric.metricKind === 'strength_session' ? 'Entry' : 'Value';
  }

  const entries = await listEntries();
  if (actionId !== null && actionId !== entriesModalActionId) return;
  const metricEntries = entries.filter(e => e.metricId === metricId);
  metricEntries.sort((a, b) => new Date(b.recordedAt) - new Date(a.recordedAt));

  ui.entriesTableBody.innerHTML = metricEntries.map(entry => {
    const d = new Date(entry.recordedAt);
    const shortDate = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    const shortTime = d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false });
    let displayValue = entry.value;
    let displayContent;
    if (metric && metric.metricKind === 'strength_session') {
      displayValue = computeStrengthValue(entry, 'Total Volume');
      const sets = Array.isArray(entry.sets) ? entry.sets : [];
      if (sets.length) {
        const strengthMeasure = metric.strengthMeasure || 'reps';
        const setRows = sets.map((set, index) => {
          if (strengthMeasure === 'duration') {
            return `<li>Set ${index + 1}: ${set.durationSeconds} sec${set.loadValue === undefined ? '' : ` · ${set.loadValue} ${metric.unitName || 'kg'}`}</li>`;
          }
          const loadValue = Number(set.loadValue ?? set.loadKg ?? set.load_kg ?? 0);
          const reps = Number(set.reps ?? 0);
          return `<li>Set ${index + 1}: ${loadValue.toFixed(1)} ${metric.unitName || 'kg'} × ${reps} reps</li>`;
        }).join('');
        displayValue = strengthMeasure === 'duration'
          ? computeDurationValue(entry, 'Total Duration')
          : computeStrengthValue(entry, 'Total Volume');
        displayContent = `<strong>${strengthMeasure === 'duration' ? `Total hold time: ${displayValue} sec` : `Total volume: ${displayValue}`}</strong><ul class="entry-strength-sets">${setRows}</ul>`;
      }
    }

    return `
      <tr data-entry-id="${entry.id}" data-metric-id="${metricId}">
        <td title="${d.toLocaleString()}" style="white-space: nowrap;">${shortDate}<br>${shortTime}</td>
        <td>${displayContent ?? (displayValue !== null && displayValue !== undefined ? displayValue : '')}</td>
        <td class="action-buttons">
          <button onclick="window.handleEditEntry('${entry.id}', '${metricId}', this.closest('tr'))" title="Edit">✏️</button>
          <button onclick="window.handleDeleteEntry('${entry.id}', '${metricId}', '${metric?.name || ''}')" title="Delete">🗑️</button>
        </td>
      </tr>
    `;
  }).join('');
}

ui.closeEntriesModal?.addEventListener('click', closeEntriesModal);
ui.modalOverlay?.addEventListener('click', closeEntriesModal);

ui.entriesTableBody.addEventListener('click', async (event) => {
  const addButton = event.target.closest('[data-add-strength-set]');
  if (addButton) {
    const editor = addButton.closest('.strength-edit-sets');
    addStrengthSetEditorRow(
      editor,
      '',
      '',
      editor.dataset.loadUnit || 'kg',
      editor.dataset.strengthMeasure || 'reps'
    );
    editor.querySelector('.strength-edit-set:last-of-type [data-strength-measure-value]').focus();
    return;
  }

  const removeButton = event.target.closest('[data-remove-strength-set]');
  if (removeButton) {
    removeButton.closest('.strength-edit-set').remove();
    return;
  }

  const row = event.target.closest('tr');
  if (event.target.closest('[data-save-strength-session]')) {
    await window.saveStrengthSessionEdit(row);
  } else if (event.target.closest('[data-cancel-strength-session]')) {
    await window.cancelInlineEdit(row);
  }
});

initializeDatabase();
