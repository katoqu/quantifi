import { renderMetricPicker, setMetricPickerOpen } from './metric-picker.js';
import { mountStrengthSetEditor } from './strength-set-editor.js';
import { summarizeWorkoutBlock, validateWorkoutPlan } from './workout-model.js';
import { findWorkoutMetricMatches, parseWorkoutImportJson } from './workout-import.js';

const CREATE_IMPORTED_METRIC = '__create_new__';

const WORKOUT_CHATBOT_PROMPT = `Help me create a workout plan for Quantifi. First ask me about my goals, experience, available equipment, schedule, and any relevant limitations. Once you have enough information, create a practical plan and return only valid JSON using this exact structure:
{
  "format": "quantifi-workout",
  "version": 1,
  "plan": {
    "name": "Plan name",
    "exercises": [
      {
        "key": "exercise-1",
        "metric": {
          "name": "Exercise name",
          "strengthMeasure": "reps",
          "unitName": "kg",
          "aliases": []
        },
        "targetSets": 3,
        "targetReps": 8
      }
    ],
    "outcomeMetrics": []
  }
}

For each exercise, use a unique stable key, a clear metric name, and optional alternate names in aliases. Use strengthMeasure "reps" with a whole-number targetReps, or "duration" with a positive targetDurationSeconds instead; include exactly one of those target fields. Include targetSets as a positive whole number. Include unitName only when relevant. Do not include workout logs, personal data, IDs, or target loads.

If I request outcome metrics, include no more than two in outcomeMetrics, each shaped like {"key":"outcome-1","metric":{"name":"Metric name","unitName":"unit","unitType":"float","aliases":[]},"direction":"increase"}. Use "increase" or "decrease" for direction. Otherwise leave outcomeMetrics empty.

Do not repeat the same exercise metric in a plan. Return JSON only, without Markdown fences or commentary.`;

const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
}[character]));

const dateInputValue = (date) => {
  const localDate = new Date(date);
  const offset = localDate.getTimezoneOffset() * 60_000;
  return new Date(localDate.getTime() - offset).toISOString().slice(0, 10);
};

const formatWorkoutDuration = (durationSeconds) => {
  const seconds = Math.max(0, Math.round(durationSeconds));
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const remainingSeconds = seconds % 60;
  const secondsLabel = remainingSeconds ? ` ${remainingSeconds} sec` : '';
  return hours
    ? `${hours} hr ${minutes % 60} min${secondsLabel}`
    : minutes
      ? `${minutes} min${secondsLabel}`
      : `${seconds} sec`;
};

export function mountWorkoutsView(root, {
  listMetrics,
  listCategories,
  listEntries,
  listWorkoutPlans,
  listWorkoutSessions,
  saveWorkoutPlan,
  saveWorkoutPlanImport,
  archiveWorkoutPlan,
  saveWorkoutSession,
  onDataChanged,
}) {
  let mode = 'plans';
  let metrics = [];
  let categories = [];
  let entries = [];
  let plans = [];
  let sessions = [];
  let showWorkoutImport = false;
  let pendingWorkoutImport = null;
  let workoutImportSelections = {};
  let workoutImportFileName = '';
  let workoutImportError = '';
  let workoutImportJson = '';
  let planSection = 'select';
  let editingPlanId = null;
  let isEditingPlan = false;
  let planName = '';
  let exerciseRows = [];
  let outcomeRows = [];
  let sessionPlan = null;
  let sessionSets = [];
  let completedExercises = [];
  let sessionRecordedAt = null;
  let activeExerciseIndex = 0;
  let editingExerciseIndex = null;
  let holdStopwatchStartedAt = null;
  let holdStopwatchElapsedMs = 0;
  let holdStopwatchInterval = null;
  let holdStopwatchExerciseIndex = null;
  let reviewResult = null;
  let reviewRange = null;
  let reviewPlanId = null;

  const strengthMetrics = () => metrics.filter((metric) => metric.metricKind === 'strength_session');
  const outcomeMetrics = () => metrics.filter((metric) => metric.metricKind !== 'strength_session');
  const metricFor = (id) => metrics.find((metric) => metric.id === id);
  const getPickerParts = (container) => ({
    selectedContainer: container.querySelector('.selected-metric-indicator'),
    suggestionsContainer: container.querySelector('.search-dropdown-suggestions'),
    searchInput: container.querySelector('.search-field'),
    clearButton: container.querySelector('.search-dropdown-clear'),
    expandButton: container.querySelector('.search-dropdown-expand'),
  });

  function renderPicker(container, row, candidates, label) {
    if (!container) return;
    const parts = getPickerParts(container);
    const selectedMetric = candidates.find((metric) => metric.id === row.metricId);
    parts.searchInput.value = row.searchTerm || '';
    renderMetricPicker({
      ...parts,
      metrics: candidates,
      categories,
      selectedMetric,
      isOpen: Boolean(row.isOpen),
    });
    const labelElement = container.querySelector('.search-label > label');
    if (labelElement) labelElement.textContent = label;
  }

  function pickerMarkup(type, index, row, label) {
    const pickerId = `workout-${type}-metric-${index}`;
    return `
      <div class="metric-picker workout-metric-picker" data-picker-type="${type}" data-picker-index="${index}">
        <div class="search-label">
          <label for="${pickerId}-search">${escapeHtml(label)}</label>
          <div class="search-dropdown-control">
            <input type="search" id="${pickerId}-search" class="search-field" placeholder="Type a metric name..." autocomplete="off" aria-controls="${pickerId}-suggestions" aria-expanded="false" />
            <button class="search-dropdown-clear hidden" type="button" aria-label="Clear metric search">×</button>
            <button class="search-dropdown-expand" type="button" aria-label="Show matching metrics" aria-expanded="false">
              <span aria-hidden="true">⌄</span>
            </button>
            <div id="${pickerId}-suggestions" class="search-dropdown-suggestions hidden" role="listbox" aria-label="${escapeHtml(label)}"></div>
          </div>
        </div>
        <div class="selected-metric-indicator" aria-live="polite"></div>
      </div>
    `;
  }

  function renderModes() {
    if (mode === 'session') {
      return '<button type="button" class="secondary" data-cancel-session>← Back to plans</button>';
    }
    const activeMode = mode;
    return `
      <nav class="workout-mode-switch" aria-label="Workout sections">
        <button type="button" data-workout-mode="plans" class="${activeMode === 'plans' ? 'active' : ''}">Plans</button>
        <button type="button" data-workout-mode="history" class="${activeMode === 'history' ? 'active' : ''}">History</button>
        <button type="button" data-workout-mode="review" class="${activeMode === 'review' ? 'active' : ''}">Review</button>
      </nav>
    `;
  }

  function getWorkoutImportReview() {
    if (!pendingWorkoutImport) {
      return {
        summary: '',
        warning: workoutImportError,
        invalid: Boolean(workoutImportError),
      };
    }

    const definitions = pendingWorkoutImport.metrics;
    const duplicateAssignments = [];
    for (const role of ['exercise', 'outcome']) {
      const selectedIds = new Set();
      for (const definition of definitions.filter((item) => item.role === role)) {
        const selectedId = workoutImportSelections[definition.key];
        if (selectedId === CREATE_IMPORTED_METRIC) continue;
        if (selectedIds.has(selectedId)) duplicateAssignments.push(definition.name);
        selectedIds.add(selectedId);
      }
    }
    const duplicateNewNames = new Set();
    const newNames = new Set();
    for (const definition of definitions) {
      if (workoutImportSelections[definition.key] !== CREATE_IMPORTED_METRIC) continue;
      const name = definition.name.toLowerCase();
      if (newNames.has(name)) duplicateNewNames.add(name);
      newNames.add(name);
    }
    const invalid = duplicateAssignments.length > 0 || duplicateNewNames.size > 0;
    let warning = '';
    if (duplicateAssignments.length) {
      warning = 'The same existing metric cannot be used for multiple exercises or outcomes of the same type.';
    } else if (duplicateNewNames.size) {
      warning = 'Choose an existing metric for one of the repeated names, or use distinct names for the new metrics.';
    } else if (plans.some((item) => item.name.trim().toLowerCase() === pendingWorkoutImport.plan.name.toLowerCase())) {
      warning = `A plan named "${pendingWorkoutImport.plan.name}" already exists. Import will create a separate plan and leave the existing one unchanged.`;
    }
    const createdCount = definitions.filter(
      (definition) => workoutImportSelections[definition.key] === CREATE_IMPORTED_METRIC
    ).length;
    return {
      summary: `${pendingWorkoutImport.plan.exercises.length} exercise${pendingWorkoutImport.plan.exercises.length === 1 ? '' : 's'} ready; ${createdCount} metric${createdCount === 1 ? '' : 's'} to create and ${definitions.length - createdCount} to reuse.`,
      warning,
      invalid,
    };
  }

  function renderWorkoutImportMetric(definition) {
    const selectedId = workoutImportSelections[definition.key] || CREATE_IMPORTED_METRIC;
    const matches = findWorkoutMetricMatches(definition, metrics);
    const options = matches.map((match) => {
      const details = [];
      details.push(match.exact ? 'name or alias match' : 'similar name');
      if (match.measureMismatch) details.push(`measure is ${match.metric.strengthMeasure || 'reps'}`);
      if (match.metricKindMismatch) details.push(`type is ${match.metric.metricKind || 'other'}`);
      if (match.unitMismatch) details.push(`unit is ${match.metric.unitName}, file uses ${definition.unitName}`);
      return `
        <option value="${escapeHtml(match.metric.id)}" ${selectedId === match.metric.id ? 'selected' : ''} ${match.compatible ? '' : 'disabled'}>
          Use existing: ${escapeHtml(match.metric.name)} (${escapeHtml(details.join('; '))})
        </option>
      `;
    }).join('');
    const measure = definition.role === 'exercise'
      ? ` · ${definition.strengthMeasure === 'duration' ? 'duration' : 'reps'}`
      : '';
    return `
      <label class="workout-import-metric">
        ${escapeHtml(definition.role === 'exercise' ? 'Exercise' : 'Outcome')}: ${escapeHtml(definition.name)}${escapeHtml(measure)}
        <select data-import-metric-key="${escapeHtml(definition.key)}">
          <option value="${CREATE_IMPORTED_METRIC}" ${selectedId === CREATE_IMPORTED_METRIC ? 'selected' : ''}>Create new metric: ${escapeHtml(definition.name)}</option>
          ${options}
        </select>
      </label>
    `;
  }

  function renderWorkoutImport() {
    const review = getWorkoutImportReview();
    const preview = pendingWorkoutImport ? `
      <div class="workout-import-preview" data-workout-import-preview>
        <h3>${escapeHtml(pendingWorkoutImport.plan.name)}</h3>
        <ol>
          ${pendingWorkoutImport.plan.exercises.map((exercise) => {
            const definition = pendingWorkoutImport.metrics.find((item) => item.key === exercise.metricKey);
            const target = exercise.strengthMeasure === 'duration'
              ? `${exercise.targetDurationSeconds} sec hold`
              : `${exercise.targetReps} reps`;
            return `<li>${escapeHtml(definition.name)} — ${exercise.targetSets} × ${target}</li>`;
          }).join('')}
        </ol>
        ${pendingWorkoutImport.plan.outcomeMetrics.length
          ? `<p>Outcome metrics: ${pendingWorkoutImport.plan.outcomeMetrics.map((outcome) => {
            const definition = pendingWorkoutImport.metrics.find((item) => item.key === outcome.metricKey);
            return `${escapeHtml(definition.name)} (${escapeHtml(outcome.direction)})`;
          }).join(', ')}</p>`
          : ''}
        <h3>Match or create metrics</h3>
        <p class="muted-text">Exact and similar names are suggestions. Review each choice; incompatible metric types or exercise measures cannot be reused.</p>
        <div class="stacked-form">${pendingWorkoutImport.metrics.map(renderWorkoutImportMetric).join('')}</div>
        <p data-workout-import-summary>${escapeHtml(review.summary)}</p>
        <p class="${review.invalid ? '' : 'muted-text'}" data-workout-import-warning role="${review.invalid ? 'alert' : 'status'}">${escapeHtml(review.warning)}</p>
        <div class="workout-exercise-actions">
          <button type="button" class="primary" data-workout-import-confirm ${review.invalid ? 'disabled' : ''}>Import plan</button>
          <button type="button" class="secondary" data-workout-import-cancel>Cancel</button>
        </div>
      </div>
    ` : '';
    return `
      <section id="workoutImportPanel" class="panel${showWorkoutImport ? '' : ' hidden'}" aria-label="Import workout plan">
        <p class="muted-text">Paste version 1 Quantifi workout JSON below or choose a JSON file. No metrics or plan are saved until you confirm the review.</p>
        <input type="file" data-workout-import-file accept=".json,application/json" hidden />
        <div class="workout-import-json-header">
          <label for="workoutImportJson">Workout JSON</label>
          <button type="button" class="secondary" data-workout-prompt-open>AI prompt</button>
        </div>
        <textarea id="workoutImportJson" data-workout-import-json rows="10" placeholder="Paste workout JSON here..." aria-describedby="workoutImportJsonHelp">${escapeHtml(workoutImportJson)}</textarea>
        <p id="workoutImportJsonHelp" class="muted-text">Use the AI prompt for a template, then paste the chatbot's JSON response here.</p>
        ${workoutImportFileName ? `<p class="muted-text">File: ${escapeHtml(workoutImportFileName)}</p>` : ''}
        <p class="${workoutImportError ? '' : 'hidden'}" data-workout-import-error role="alert">${escapeHtml(workoutImportError)}</p>
        <div class="workout-exercise-actions">
          <button type="button" class="primary" data-workout-import-review>Review JSON</button>
          <button type="button" class="secondary" data-workout-import-choose>Choose JSON file</button>
        </div>
        ${preview}
        <dialog class="workout-prompt-dialog" data-workout-prompt-dialog aria-labelledby="workoutPromptHeading">
          <div class="workout-prompt-dialog-content">
            <h2 id="workoutPromptHeading" class="workflow-card-heading">Prompt for your chatbot</h2>
            <p class="muted-text">Copy this prompt into a chatbot. It will ask about your needs, then produce version 1 Quantifi JSON for this importer.</p>
            <textarea data-workout-prompt readonly rows="18" aria-label="Chatbot prompt">${escapeHtml(WORKOUT_CHATBOT_PROMPT)}</textarea>
            <div class="workout-exercise-actions">
              <button type="button" class="primary" data-workout-prompt-copy>Copy prompt</button>
              <button type="button" class="secondary" data-workout-prompt-close>Close</button>
            </div>
            <p data-workout-prompt-status aria-live="polite"></p>
          </div>
        </dialog>
      </section>
    `;
  }

  function renderPlans() {
    const sectionNav = `
      <nav class="workflow-subsection-switch" aria-label="Workout plan actions">
        <button type="button" class="${planSection === 'select' && !showWorkoutImport ? 'active' : ''}" data-plan-section="select" aria-pressed="${planSection === 'select' && !showWorkoutImport}">Select Workout</button>
        <button type="button" class="${planSection === 'create' && !showWorkoutImport ? 'active' : ''}" data-plan-section="create" aria-pressed="${planSection === 'create' && !showWorkoutImport}">Create Plan</button>
        <button type="button" class="${showWorkoutImport ? 'active' : ''}" data-workout-import-toggle aria-controls="workoutImportPanel" aria-expanded="${showWorkoutImport}" aria-pressed="${showWorkoutImport}">Import plan</button>
      </nav>
    `;
    if (showWorkoutImport) return `${sectionNav}${renderWorkoutImport()}`;

    const planCards = plans.filter((plan) => !plan.isArchived).map((plan) => {
      const canStart = plan.exercises.every((exercise) => metricFor(exercise.metricId));
      const exerciseLabels = plan.exercises.map((exercise) => {
        const metric = metricFor(exercise.metricId);
        const strengthMeasure = exercise.strengthMeasure || metric?.strengthMeasure || 'reps';
        const target = strengthMeasure === 'duration'
          ? `${exercise.targetDurationSeconds ?? exercise.targetReps} sec hold`
          : `${exercise.targetReps} reps`;
        return `<li>${escapeHtml(metric?.name || 'Archived exercise')} — ${exercise.targetSets} × ${target}</li>`;
      }).join('');
      const outcomeLabels = (plan.outcomeMetrics || []).map((outcome) => {
        const metric = metricFor(outcome.metricId);
        const direction = outcome.direction === 'increase' ? 'increase' : 'decrease';
        return `<li>${escapeHtml(metric?.name || 'Archived metric')}: aim to ${direction}</li>`;
      }).join('');
      return `
        <article class="panel">
          <h3>${escapeHtml(plan.name)}</h3>
          <ol>${exerciseLabels}</ol>
          ${outcomeLabels ? `<p><strong>Outcomes to follow</strong></p><ul>${outcomeLabels}</ul>` : ''}
          <div class="workout-exercise-actions">
            <button type="button" class="primary" data-plan-action="start" data-plan-id="${escapeHtml(plan.id)}" ${canStart ? '' : 'disabled'}>Start workout</button>
            <button type="button" class="secondary" data-plan-action="edit" data-plan-id="${escapeHtml(plan.id)}">Edit</button>
            <button type="button" class="secondary" data-plan-action="archive" data-plan-id="${escapeHtml(plan.id)}">Archive</button>
          </div>
        </article>
      `;
    }).join('');
    if (planSection === 'create') {
      return `${sectionNav}${renderWorkoutImport()}${renderPlanEditor()}`;
    }
    return `
      ${sectionNav}
      ${renderWorkoutImport()}
      <div class="panel">
        <p class="muted-text">Choose a saved plan to start your workout.</p>
        <div id="workoutPlanList" class="list">
          ${planCards || '<p class="muted-text">No workout plans yet. Choose Create Plan to build your first one.</p>'}
        </div>
      </div>
    `;
  }

  function renderExerciseRows() {
    return exerciseRows.map((row, index) => {
      const strengthMeasure = row.strengthMeasure || metricFor(row.metricId)?.strengthMeasure || 'reps';
      const duration = strengthMeasure === 'duration';
      const target = duration ? row.targetDurationSeconds ?? 30 : row.targetReps;
      return `
        <article class="panel workout-exercise-card" data-exercise-row="${index}">
          <h3>Exercise ${index + 1}</h3>
          ${pickerMarkup('exercise', index, row, 'Strength metric')}
          <div class="strength-grid">
            <label>Target sets<input type="number" min="1" step="1" data-target-sets="${index}" value="${escapeHtml(row.targetSets)}" required /></label>
            <label>Target ${duration ? 'hold (seconds)' : 'reps'}<input type="number" min="${duration ? '0.01' : '1'}" step="${duration ? 'any' : '1'}" data-target-value="${index}" value="${escapeHtml(target)}" required /></label>
          </div>
          <div class="workout-exercise-actions">
            <button type="button" class="secondary" data-exercise-move="up" data-row-index="${index}" ${index === 0 ? 'disabled' : ''}>Move up</button>
            <button type="button" class="secondary" data-exercise-move="down" data-row-index="${index}" ${index === exerciseRows.length - 1 ? 'disabled' : ''}>Move down</button>
            <button type="button" class="secondary" data-remove-exercise="${index}">Remove</button>
          </div>
        </article>
      `;
    }).join('');
  }

  function renderOutcomeRows() {
    return outcomeRows.map((row, index) => `
      <article class="panel workout-exercise-card" data-outcome-row="${index}">
        ${pickerMarkup('outcome', index, row, 'Outcome metric')}
        <label>
          Desired direction
          <select data-outcome-direction="${index}">
            <option value="increase" ${row.direction === 'increase' ? 'selected' : ''}>Increase</option>
            <option value="decrease" ${row.direction === 'decrease' ? 'selected' : ''}>Decrease</option>
          </select>
        </label>
        <button type="button" class="secondary" data-remove-outcome="${index}">Remove metric</button>
      </article>
    `).join('');
  }

  function renderPlanEditor() {
    return `
      <div class="panel">
        ${editingPlanId ? '<h2 class="workflow-card-heading">Edit workout plan</h2>' : ''}
        <form id="workoutPlanForm" class="stacked-form">
          <label>
            Plan name
            <input type="text" name="planName" value="${escapeHtml(planName)}" required />
          </label>
          <h3>Exercises in order</h3>
          <div id="workoutExerciseRows">${renderExerciseRows()}</div>
          <button type="button" class="secondary" data-add-exercise>Add exercise</button>
          <h3>Outcome metrics to review (optional)</h3>
          <div id="workoutOutcomeRows">${renderOutcomeRows()}</div>
          ${outcomeRows.length < 2 ? '<button type="button" class="secondary" data-add-outcome>Add outcome metric</button>' : ''}
          <div class="workout-exercise-actions">
            <button type="submit" class="primary">Save plan</button>
            <button type="button" class="secondary" data-cancel-plan>Cancel</button>
          </div>
        </form>
      </div>
    `;
  }

  function getSessionProgress() {
    const totalExercises = sessionPlan.exercises.length;
    const totalPlannedSets = sessionPlan.exercises.reduce(
      (total, exercise) => total + Number(exercise.targetSets),
      0
    );
    let recordedSets = 0;
    let skippedSets = 0;
    let accountedSets = 0;

    sessionPlan.exercises.forEach((exercise, index) => {
      const targetSets = Number(exercise.targetSets);
      const setCount = sessionSets[index]?.length || 0;
      const isCompleted = completedExercises[index];
      const isBeingEdited = editingExerciseIndex === index;
      recordedSets += setCount;
      if (isCompleted && !isBeingEdited) {
        skippedSets += Math.max(0, targetSets - setCount);
        accountedSets += targetSets;
      } else {
        accountedSets += Math.min(targetSets, setCount);
      }
    });

    return {
      totalExercises,
      completedExerciseCount: completedExercises.filter(Boolean).length,
      totalPlannedSets,
      recordedSets,
      skippedSets,
      accountedSets,
    };
  }

  function getHoldStopwatchElapsedMs() {
    return holdStopwatchElapsedMs
      + (holdStopwatchStartedAt === null ? 0 : Date.now() - holdStopwatchStartedAt);
  }

  function formatHoldStopwatch(elapsedMs) {
    const tenths = Math.floor(elapsedMs / 100) % 10;
    const totalSeconds = Math.floor(elapsedMs / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = String(totalSeconds % 60).padStart(2, '0');
    return `${String(minutes).padStart(2, '0')}:${seconds}.${tenths}`;
  }

  function updateHoldStopwatch() {
    if (holdStopwatchExerciseIndex === null) return;
    const elapsedMs = getHoldStopwatchElapsedMs();
    const stopwatch = root.querySelector(`[data-hold-stopwatch="${holdStopwatchExerciseIndex}"]`);
    const readout = stopwatch?.querySelector('.workout-hold-stopwatch-readout');
    const toggle = stopwatch?.querySelector('[data-hold-stopwatch-toggle]');
    const reset = stopwatch?.querySelector('[data-hold-stopwatch-reset]');
    const durationInput = root.querySelector(
      `[data-session-exercise="${holdStopwatchExerciseIndex}"] .workout-reps`
    );
    if (readout) readout.textContent = formatHoldStopwatch(elapsedMs);
    if (toggle) {
      toggle.textContent = holdStopwatchStartedAt === null ? 'Start' : 'Pause';
      toggle.setAttribute('aria-label', holdStopwatchStartedAt === null ? 'Start hold stopwatch' : 'Pause hold stopwatch');
    }
    if (reset) reset.disabled = elapsedMs === 0;
    if (durationInput && elapsedMs > 0) durationInput.value = (elapsedMs / 1000).toFixed(1);
  }

  function pauseHoldStopwatch() {
    if (holdStopwatchStartedAt === null) return;
    holdStopwatchElapsedMs = getHoldStopwatchElapsedMs();
    holdStopwatchStartedAt = null;
    clearInterval(holdStopwatchInterval);
    holdStopwatchInterval = null;
    updateHoldStopwatch();
  }

  function resetHoldStopwatch() {
    pauseHoldStopwatch();
    if (holdStopwatchExerciseIndex !== null) {
      const durationInput = root.querySelector(
        `[data-session-exercise="${holdStopwatchExerciseIndex}"] .workout-reps`
      );
      if (durationInput) durationInput.value = '';
    }
    holdStopwatchElapsedMs = 0;
    updateHoldStopwatch();
  }

  function clearHoldStopwatch() {
    clearInterval(holdStopwatchInterval);
    holdStopwatchInterval = null;
    holdStopwatchStartedAt = null;
    holdStopwatchElapsedMs = 0;
    holdStopwatchExerciseIndex = null;
  }

  function updateSessionProgress() {
    if (!sessionPlan) return;
    const progress = getSessionProgress();
    const progressElement = root.querySelector('#workoutSetProgress');
    if (progressElement) progressElement.value = progress.accountedSets;

    const activeIndex = editingExerciseIndex ?? activeExerciseIndex;
    const finishButton = root.querySelector('[data-finish-exercise], [data-finish-edit]');
    if (finishButton) finishButton.disabled = !sessionSets[activeIndex]?.length;

    const progressLabel = root.querySelector('[data-session-progress-label]');
    if (progressLabel) {
      progressLabel.textContent = `Sets ${progress.accountedSets}/${progress.totalPlannedSets} · `
        + `exercises ${progress.completedExerciseCount}/${progress.totalExercises}`;
    }
    if (progressElement) {
      progressElement.setAttribute(
        'aria-valuetext',
        `${progress.accountedSets} of ${progress.totalPlannedSets} planned sets accounted for; `
          + `${progress.completedExerciseCount} of ${progress.totalExercises} exercises finished.`
      );
    }
  }

  function focusSessionStep() {
    root.querySelector('[data-session-exercise] .workout-reps, #workoutSessionForm [type="submit"]')?.focus();
  }

  function updateSessionProgressPosition() {
    const placeholder = root.querySelector('.workout-session-progress-placeholder');
    const progress = placeholder?.querySelector('.workout-session-progress');
    if (!placeholder || !progress) return;

    const shouldPin = placeholder.getBoundingClientRect().bottom < 0;
    progress.classList.toggle('workout-session-progress--pinned', shouldPin);
    if (shouldPin) {
      const { left, width } = placeholder.getBoundingClientRect();
      progress.style.left = `${left}px`;
      progress.style.width = `${width}px`;
    } else {
      progress.style.left = '';
      progress.style.width = '';
    }
  }

  function renderSession() {
    const selectedPlan = sessionPlan;
    if (!selectedPlan) return '';
    const progress = getSessionProgress();
    const focusedIndex = editingExerciseIndex ?? activeExerciseIndex;
    const exerciseCards = selectedPlan.exercises.map((exercise, index) => {
      const metric = metricFor(exercise.metricId);
      const exerciseName = metric?.name || 'Archived exercise';
      const recordedSetCount = sessionSets[index]?.length || 0;
      const isEditing = editingExerciseIndex === index;

      if (completedExercises[index] && !isEditing) {
        const skipped = Math.max(0, Number(exercise.targetSets) - recordedSetCount);
        return `
          <article class="panel workout-exercise-card workout-exercise-card--completed">
            <div class="workout-exercise-completed-heading">
              <h3>${escapeHtml(exerciseName)}</h3>
              <span>Complete</span>
            </div>
            <p class="muted-text">${recordedSetCount} sets${skipped ? ` · ${skipped} skipped` : ''}</p>
            <button type="button" class="secondary" data-edit-session-exercise="${index}" ${editingExerciseIndex !== null ? 'disabled' : ''}>Edit exercise</button>
          </article>
        `;
      }

      if (index !== focusedIndex) return '';

      const loadUnit = metric?.unitName || 'kg';
      const strengthMeasure = exercise.strengthMeasure || metric?.strengthMeasure || 'reps';
      const duration = strengthMeasure === 'duration';
      const previous = entries
        .filter((entry) => entry.metricId === exercise.metricId)
        .sort((a, b) => new Date(b.recordedAt) - new Date(a.recordedAt))[0];
      const previousSets = previous?.sets || [];
      const previousHtml = previousSets.length
        ? `<p class="muted-text">Last: ${previousSets.map((set) => duration
          ? `${escapeHtml(set.durationSeconds)} sec hold${set.loadValue === undefined ? '' : ` · ${escapeHtml(set.loadValue)} ${escapeHtml(loadUnit)}`}`
          : `${Number(set.loadValue ?? set.loadKg ?? set.load_kg ?? 0)} ${escapeHtml(loadUnit)} × ${escapeHtml(set.reps)} reps`).join(' · ')}</p>`
        : '';
      const targetValue = duration
        ? exercise.targetDurationSeconds ?? 30
        : exercise.targetReps;
      const previousLoad = previous?.loadValue ?? previous?.loadKg
        ?? (duration ? '' : previous?.value ?? '');
      const actionButton = isEditing
        ? '<button type="button" class="primary" data-finish-edit>Done editing</button>'
        : '<button type="button" class="primary" data-finish-exercise>Finish exercise</button><p class="muted-text">Remaining sets are skipped.</p>';
      const loadLabel = `<label>Load (${escapeHtml(loadUnit)})${duration ? ' (optional)' : ''}<input type="number" class="workout-load" min="0" step="0.5" value="${escapeHtml(previousLoad)}" ${duration ? '' : 'required'} /></label>`;
      const measureLabel = `<label>${duration ? 'Hold (seconds)' : 'Reps'}<input type="number" class="workout-reps" min="${duration ? '0.01' : '1'}" step="${duration ? 'any' : '1'}" value="${targetValue}" required /></label>`;
      const stopwatch = duration ? `
        <div class="workout-hold-stopwatch" data-hold-stopwatch="${index}">
          <output class="workout-hold-stopwatch-readout" aria-live="off">${escapeHtml(formatHoldStopwatch(getHoldStopwatchElapsedMs()))}</output>
          <button type="button" class="secondary" data-hold-stopwatch-toggle aria-label="${holdStopwatchStartedAt === null ? 'Start' : 'Pause'} hold stopwatch">${holdStopwatchStartedAt === null ? 'Start' : 'Pause'}</button>
          <button type="button" class="secondary" data-hold-stopwatch-reset ${getHoldStopwatchElapsedMs() === 0 ? 'disabled' : ''}>Reset</button>
        </div>
      ` : '';
      return `
        <article class="panel workout-exercise-card workout-exercise-card--active" data-session-exercise="${index}">
          <h3>Exercise ${index + 1} of ${progress.totalExercises}: ${escapeHtml(exerciseName)}</h3>
          <p class="muted-text">Goal: ${exercise.targetSets} × ${targetValue} ${duration ? 'sec hold' : 'reps'}</p>
          ${previousHtml}
          <div class="strength-grid workout-strength-grid">
            ${duration ? `${measureLabel}${loadLabel}` : `${loadLabel}${measureLabel}`}
          </div>
          ${stopwatch}
          <button type="button" class="secondary workout-add-set">Add set</button>
          <div class="list workout-set-list"></div>
          ${actionButton}
        </article>
      `;
    }).join('');
    const nextExercise = editingExerciseIndex === null
      ? selectedPlan.exercises.find((exercise, index) => (
        index > activeExerciseIndex && !completedExercises[index]
      ))
      : null;
    const nextMetric = nextExercise ? metricFor(nextExercise.metricId) : null;
    const nextPrevious = nextExercise
      ? entries
        .filter((entry) => entry.metricId === nextExercise.metricId)
        .sort((a, b) => new Date(b.recordedAt) - new Date(a.recordedAt))[0]
      : null;
    const nextPreviousSets = nextPrevious?.sets || [];
    const lastNextSet = nextPreviousSets[nextPreviousSets.length - 1];
    const nextLoadValue = lastNextSet?.loadValue
      ?? lastNextSet?.loadKg
      ?? lastNextSet?.load_kg
      ?? nextPrevious?.loadValue
      ?? nextPrevious?.loadKg
      ?? nextPrevious?.value;
    const hasNextLoad = nextLoadValue !== null
      && nextLoadValue !== undefined
      && String(nextLoadValue).trim() !== ''
      && Number.isFinite(Number(nextLoadValue));
    const nextExercisePreview = nextExercise
      ? `<p class="workout-next-exercise-preview">${escapeHtml(metricFor(nextExercise.metricId)?.name || 'Archived exercise')}${hasNextLoad ? `: ${escapeHtml(Number(nextLoadValue))} ${escapeHtml(metricFor(nextExercise.metricId)?.unitName || 'kg')}` : ''}</p>`
      : '';
    const allExercisesComplete = completedExercises.every(Boolean) && editingExerciseIndex === null;
    return `
      <div class="panel workout-session-panel">
        <h2 class="workflow-card-heading">${escapeHtml(selectedPlan.name)}</h2>
        <div class="workout-session-progress-placeholder">
          <div class="workout-session-progress">
            <div class="workout-session-progress-track">
              <progress id="workoutSetProgress" max="${progress.totalPlannedSets}" value="${progress.accountedSets}" aria-label="Workout progress" aria-valuetext="${progress.accountedSets} of ${progress.totalPlannedSets} planned sets accounted for; ${progress.completedExerciseCount} of ${progress.totalExercises} exercises finished."></progress>
              <span data-session-progress-label aria-hidden="true">Sets ${progress.accountedSets}/${progress.totalPlannedSets} · exercises ${progress.completedExerciseCount}/${progress.totalExercises}</span>
            </div>
          </div>
        </div>
        <form id="workoutSessionForm" class="stacked-form workout-session-form">
          ${exerciseCards}
          ${nextExercisePreview}
          ${allExercisesComplete ? `
            <button type="submit" class="primary">Save workout</button>
          ` : ''}
          <button type="button" class="secondary" data-cancel-session>Cancel workout</button>
        </form>
      </div>
    `;
  }

  function renderHistory() {
    const entryMap = new Map(entries.map((entry) => [entry.id, entry]));
    const cards = [...sessions]
      .sort((a, b) => new Date(b.recordedAt) - new Date(a.recordedAt))
      .map((session) => `
        <article class="panel">
          <h3>${escapeHtml(session.planName)}</h3>
          <p class="muted-text">${escapeHtml(new Date(session.recordedAt).toLocaleString())}</p>
          ${Number.isFinite(session.durationSeconds)
            ? `<p class="muted-text">Duration: ${escapeHtml(formatWorkoutDuration(session.durationSeconds))}</p>`
            : ''}
          <ul>
            ${session.exercises.map((exercise) => {
              const entry = entryMap.get(exercise.entryId);
              const sets = entry?.sets || [];
              const strengthMeasure = exercise.strengthMeasure || metricFor(exercise.metricId)?.strengthMeasure || 'reps';
              const skippedSets = Number(exercise.skippedSets) || 0;
              const detail = sets.length
                ? sets.map((set) => strengthMeasure === 'duration'
                  ? `${set.durationSeconds} sec hold${set.loadValue === undefined ? '' : ` · ${set.loadValue} ${metricFor(exercise.metricId)?.unitName || 'kg'}`}`
                  : `${Number(set.loadValue ?? set.loadKg ?? set.load_kg ?? 0)} ${metricFor(exercise.metricId)?.unitName || 'kg'} × ${set.reps}`).join(' · ')
                : 'Entry no longer available';
              return `<li><strong>${escapeHtml(exercise.metricName)}</strong>: ${escapeHtml(detail)}${skippedSets ? ` · ${skippedSets} skipped` : ''}</li>`;
            }).join('')}
          </ul>
        </article>
      `).join('');
    return `
      <div class="panel">
        <h2 class="workflow-card-heading">Workout history</h2>
        <p class="muted-text">Each workout keeps its original plan and exercise sequence.</p>
      </div>
      <div class="list">${cards || '<p class="panel">No completed workouts yet.</p>'}</div>
    `;
  }

  function renderReview() {
    const planOptions = plans.map((plan) => `
      <option value="${escapeHtml(plan.id)}">${escapeHtml(plan.name)}</option>
    `).join('');
    const result = reviewResult ? `
      <div class="panel workout-review-result">
        <h3>${reviewResult.sessionsCompleted} workout${reviewResult.sessionsCompleted === 1 ? '' : 's'} completed</h3>
        <h4>Strength progress</h4>
        ${reviewResult.exerciseProgress.map((progress) => {
          const metric = metricFor(progress.metricId);
          const loadUnit = metric?.unitName || 'kg';
          let detail = 'Not enough sessions to compare.';
          if (progress.change !== null) {
            const sign = progress.change > 0 ? '+' : '';
            if (progress.strengthMeasure === 'duration') {
              detail = `Best hold: ${progress.firstValue} sec → ${progress.latestValue} sec (${sign}${progress.change} sec across ${progress.sessions} sessions).`;
            } else {
              detail = `Estimated 1RM: ${progress.firstValue.toFixed(1)} ${loadUnit} → ${progress.latestValue.toFixed(1)} ${loadUnit} (${sign}${progress.change.toFixed(1)} ${loadUnit} across ${progress.sessions} sessions).`;
            }
          }
          return `<p><strong>${escapeHtml(metric?.name || 'Archived exercise')}:</strong> ${escapeHtml(detail)}</p>`;
        }).join('')}
        ${reviewResult.outcomeProgress.length ? '<h4>Outcome metrics</h4>' : ''}
        ${reviewResult.outcomeProgress.map((progress) => {
          const metric = metricFor(progress.metricId);
          const unit = metric?.unitName ? ` ${metric.unitName}` : '';
          const label = {
            'toward-goal': 'Moved toward the chosen direction',
            'away-from-goal': 'Moved away from the chosen direction',
            unchanged: 'No change between first and last readings',
            'not-enough-data': 'Not enough readings in this block',
          }[progress.progress];
          const values = progress.firstValue === null || progress.latestValue === null
            ? ''
            : ` (${progress.firstValue}${unit} → ${progress.latestValue}${unit})`;
          return `<p><strong>${escapeHtml(progress.metricName)}:</strong> ${escapeHtml(label)}${escapeHtml(values)}</p>`;
        }).join('')}
        <p class="muted-text">These trends overlap in time; they do not show that the workout caused the changes.</p>
      </div>
    ` : '';
    return `
      <div class="panel">
        <h2 class="workflow-card-heading">Review a training block</h2>
        <p class="muted-text">Compare strength progress and linked metric trends for dates you choose.</p>
        <form id="workoutReviewForm" class="stacked-form">
          <label>Workout plan<select name="reviewPlan" required>${planOptions}</select></label>
          <div class="strength-grid">
            <label>Start date<input type="date" name="reviewStart" required /></label>
            <label>End date<input type="date" name="reviewEnd" required /></label>
          </div>
          <button type="submit" class="primary">Review block</button>
        </form>
      </div>
      ${result}
    `;
  }

  function capturePlanFormValues() {
    const form = root.querySelector('#workoutPlanForm');
    if (!form) return;
    planName = form.elements.planName.value;
    exerciseRows.forEach((row, index) => {
      row.targetSets = form.querySelector(`[data-target-sets="${index}"]`)?.value ?? row.targetSets;
      const value = form.querySelector(`[data-target-value="${index}"]`)?.value;
      if (value !== undefined) {
        if ((row.strengthMeasure || metricFor(row.metricId)?.strengthMeasure || 'reps') === 'duration') {
          row.targetDurationSeconds = value;
        } else {
          row.targetReps = value;
        }
      }
    });
    outcomeRows.forEach((row, index) => {
      row.direction = form.querySelector(`[data-outcome-direction="${index}"]`)?.value ?? row.direction;
    });
  }

  function refreshPicker(container, row, candidates, label) {
    const parts = getPickerParts(container);
    const selectedMetric = candidates.find((metric) => metric.id === row.metricId);
    renderMetricPicker({
      ...parts,
      metrics: candidates,
      categories,
      selectedMetric,
      isOpen: Boolean(row.isOpen),
    });
    const labelElement = container.querySelector('.search-label > label');
    if (labelElement) labelElement.textContent = label;
  }

  function renderPlanPickers() {
    root.querySelectorAll('.workout-metric-picker').forEach((container) => {
      const type = container.dataset.pickerType;
      const index = Number(container.dataset.pickerIndex);
      const row = type === 'exercise' ? exerciseRows[index] : outcomeRows[index];
      if (row) renderPicker(container, row, type === 'exercise' ? strengthMetrics() : outcomeMetrics(),
        type === 'exercise' ? 'Strength metric' : 'Outcome metric');
    });
  }

  function beginNewPlan() {
    planSection = 'create';
    editingPlanId = null;
    isEditingPlan = true;
    planName = '';
    exerciseRows = [{ metricId: '', targetSets: 3, targetReps: 8, strengthMeasure: 'reps', searchTerm: '', isOpen: false }];
    outcomeRows = [];
    render();
    root.querySelector('[name="planName"]')?.focus();
  }

  function beginEditPlan(plan) {
    planSection = 'create';
    editingPlanId = plan.id;
    isEditingPlan = true;
    planName = plan.name;
    exerciseRows = plan.exercises.map((exercise) => ({
      ...exercise,
      searchTerm: '',
      isOpen: false,
    }));
    outcomeRows = (plan.outcomeMetrics || []).map((outcome) => ({
      ...outcome,
      searchTerm: '',
      isOpen: false,
    }));
    mode = 'plans';
    render();
    root.querySelector('[name="planName"]')?.focus();
  }

  async function startPlan(plan) {
    sessionPlan = plan;
    sessionSets = plan.exercises.map(() => []);
    completedExercises = plan.exercises.map(() => false);
    sessionRecordedAt = null;
    activeExerciseIndex = 0;
    editingExerciseIndex = null;
    mode = 'session';
    reviewResult = null;
    await refreshData();
    render();
  }

  async function refreshData() {
    [metrics, categories, entries, plans, sessions] = await Promise.all([
      listMetrics(false),
      listCategories(),
      listEntries(),
      listWorkoutPlans({ includeArchived: true }),
      listWorkoutSessions(),
    ]);
  }

  function updateWorkoutImportReview() {
    const review = getWorkoutImportReview();
    const summary = root.querySelector('[data-workout-import-summary]');
    const warning = root.querySelector('[data-workout-import-warning]');
    const confirmButton = root.querySelector('[data-workout-import-confirm]');
    if (summary) summary.textContent = review.summary;
    if (warning) {
      warning.textContent = review.warning;
      warning.classList.toggle('muted-text', !review.invalid);
      warning.setAttribute('role', review.invalid ? 'alert' : 'status');
    }
    if (confirmButton) confirmButton.disabled = review.invalid;
  }

  async function readWorkoutImportFile(file) {
    capturePlanFormValues();
    workoutImportFileName = file.name;
    workoutImportError = '';
    try {
      workoutImportJson = await file.text();
      parseWorkoutImportText(workoutImportJson);
    } catch (error) {
      pendingWorkoutImport = null;
      workoutImportSelections = {};
      workoutImportError = error.message;
    }
    showWorkoutImport = true;
    render();
    root.querySelector('[data-workout-import-confirm], [data-workout-import-review]')?.focus();
  }

  function parseWorkoutImportText(text) {
    try {
      pendingWorkoutImport = parseWorkoutImportJson(text);
      workoutImportSelections = Object.fromEntries(pendingWorkoutImport.metrics.map((definition) => {
        const exactMatch = findWorkoutMetricMatches(definition, metrics)
          .find((match) => match.exact && match.compatible && !match.unitMismatch);
        return [definition.key, exactMatch?.metric.id || CREATE_IMPORTED_METRIC];
      }));
      workoutImportError = '';
    } catch (error) {
      pendingWorkoutImport = null;
      workoutImportSelections = {};
      workoutImportError = error.message;
    }
    render();
    root.querySelector('[data-workout-import-confirm], [data-workout-import-review]')?.focus();
  }

  async function confirmWorkoutImport() {
    if (!pendingWorkoutImport) return;
    const review = getWorkoutImportReview();
    if (review.invalid) return;
    try {
      const metricDecisions = pendingWorkoutImport.metrics.map((definition) => ({
        key: definition.key,
        definition,
        metricId: workoutImportSelections[definition.key] === CREATE_IMPORTED_METRIC
          ? null
          : workoutImportSelections[definition.key],
      }));
      const result = await saveWorkoutPlanImport({
        plan: pendingWorkoutImport.plan,
        metricDecisions,
      });
      const createdCount = result.createdMetrics.length;
      const reusedCount = metricDecisions.length - createdCount;
      const planName = result.plan.name;
      pendingWorkoutImport = null;
      workoutImportSelections = {};
      workoutImportFileName = '';
      workoutImportError = '';
      workoutImportJson = '';
      showWorkoutImport = false;
      planSection = 'select';
      await onDataChanged();
      window.alert(`Imported "${planName}". Created ${createdCount} metric${createdCount === 1 ? '' : 's'} and reused ${reusedCount}.`);
    } catch (error) {
      workoutImportError = error.message;
      showWorkoutImport = true;
      render();
    }
  }

  async function savePlan(event) {
    event.preventDefault();
    capturePlanFormValues();
    try {
      const validated = validateWorkoutPlan({
        name: planName,
        exercises: exerciseRows,
        outcomeMetrics: outcomeRows,
      });
      const editing = plans.find((plan) => plan.id === editingPlanId);
      await saveWorkoutPlan({
        ...editing,
        ...validated,
        id: editingPlanId || undefined,
      });
      editingPlanId = null;
      isEditingPlan = false;
      planName = '';
      exerciseRows = [];
      outcomeRows = [];
      planSection = 'select';
      await onDataChanged();
    } catch (error) {
      window.alert(error.message);
    }
  }

  async function saveSession(event) {
    event.preventDefault();
    try {
      if (!completedExercises.every(Boolean) || editingExerciseIndex !== null) {
        throw new Error('Finish or skip the remaining sets for every exercise before saving.');
      }
      if (!sessionSets.some((sets) => sets.length)) {
        throw new Error('Add at least one set before saving the workout.');
      }
      const recordedAt = new Date(sessionRecordedAt ?? Date.now()).toISOString();
      const exercises = sessionPlan.exercises.map((exercise, index) => ({
        metricId: exercise.metricId,
        metricName: metricFor(exercise.metricId)?.name || 'Archived exercise',
        sets: sessionSets[index],
        skippedSets: Math.max(0, Number(exercise.targetSets) - sessionSets[index].length),
      }));
      const saved = await saveWorkoutSession(sessionPlan, {
        recordedAt,
        exercises,
      });
      sessionPlan = null;
      sessionSets = [];
      completedExercises = [];
      sessionRecordedAt = null;
      activeExerciseIndex = 0;
      editingExerciseIndex = null;
      mode = 'history';
      await onDataChanged();
      root.querySelector('.workout-mode-switch [data-workout-mode="history"]')?.focus();
      return saved;
    } catch (error) {
      window.alert(error.message);
      return null;
    }
  }

  function saveReview(event) {
    event.preventDefault();
    const form = event.target;
    reviewPlanId = form.elements.reviewPlan.value;
    const plan = plans.find((item) => item.id === reviewPlanId);
    if (!plan) {
      window.alert('Choose a workout plan to review.');
      return;
    }
    try {
      reviewRange = {
        startAt: new Date(`${form.elements.reviewStart.value}T00:00:00`).toISOString(),
        endAt: new Date(`${form.elements.reviewEnd.value}T23:59:59.999`).toISOString(),
      };
      reviewResult = summarizeWorkoutBlock({
        plan,
        sessions,
        entries,
        metrics,
        ...reviewRange,
      });
      render();
    } catch (error) {
      window.alert(error.message);
    }
  }

  function mountSessionEditors() {
    root.querySelectorAll('[data-session-exercise]').forEach((card) => {
      const index = Number(card.dataset.sessionExercise);
      const exercise = sessionPlan.exercises[index];
      const loadInput = card.querySelector('.workout-load');
      const repsInput = card.querySelector('.workout-reps');
      const strengthMeasure = exercise.strengthMeasure || metricFor(exercise.metricId)?.strengthMeasure || 'reps';
      const editor = mountStrengthSetEditor({
        container: card.querySelector('.workout-set-list'),
        loadInput,
        repsInput,
        addButton: card.querySelector('.workout-add-set'),
        defaultReps: exercise.targetReps || 5,
        loadUnit: metricFor(exercise.metricId)?.unitName || 'kg',
        strengthMeasure,
        onChange: (sets) => {
          sessionSets[index] = sets;
          updateSessionProgress();
        },
      });
      editor.setMeasure(strengthMeasure, strengthMeasure === 'duration'
        ? exercise.targetDurationSeconds
        : exercise.targetReps);
      editor.replace(sessionSets[index] || []);
    });
  }

  function render() {
    if (!root) return;
    if (mode === 'session') {
      root.innerHTML = `${renderModes()}${renderSession()}`;
      mountSessionEditors();
      updateSessionProgressPosition();
      return;
    }
    const content = mode === 'plans'
      ? renderPlans()
      : mode === 'history'
        ? renderHistory()
        : renderReview();
    root.innerHTML = `${renderModes()}${content}`;
    if (mode === 'plans' && isEditingPlan) renderPlanPickers();
    if (mode === 'review') {
      const form = root.querySelector('#workoutReviewForm');
      if (form) {
        if (plans.some((plan) => plan.id === reviewPlanId)) {
          form.elements.reviewPlan.value = reviewPlanId;
        } else {
          reviewPlanId = form.elements.reviewPlan.value;
        }
        if (reviewRange) {
          form.elements.reviewStart.value = dateInputValue(reviewRange.startAt);
          form.elements.reviewEnd.value = dateInputValue(reviewRange.endAt);
        }
      }
    }
  }

  document.addEventListener('scroll', updateSessionProgressPosition, { capture: true, passive: true });
  window.addEventListener('resize', updateSessionProgressPosition, { passive: true });

  root.addEventListener('input', (event) => {
    const input = event.target;
    if (input.matches('[data-workout-import-json]')) {
      workoutImportJson = input.value;
      workoutImportFileName = '';
      pendingWorkoutImport = null;
      workoutImportSelections = {};
      workoutImportError = '';
      root.querySelector('[data-workout-import-preview]')?.remove();
      const error = root.querySelector('[data-workout-import-error]');
      if (error) {
        error.textContent = '';
        error.classList.add('hidden');
      }
      return;
    }
    const picker = input.closest('.workout-metric-picker');
    if (picker && input.matches('.search-field')) {
      const row = picker.dataset.pickerType === 'exercise'
        ? exerciseRows[Number(picker.dataset.pickerIndex)]
        : outcomeRows[Number(picker.dataset.pickerIndex)];
      if (!row) return;
      row.searchTerm = input.value;
      row.isOpen = true;
      refreshPicker(
        picker,
        row,
        picker.dataset.pickerType === 'exercise' ? strengthMetrics() : outcomeMetrics(),
        picker.dataset.pickerType === 'exercise' ? 'Strength metric' : 'Outcome metric'
      );
      picker.querySelector('.search-field').focus();
    }
  });

  root.addEventListener('change', async (event) => {
    if (event.target.matches('[data-workout-import-file]')) {
      const file = event.target.files?.[0];
      if (file) await readWorkoutImportFile(file);
      return;
    }
    if (event.target.matches('[data-workout-import-json]')) return;
    if (event.target.matches('[data-import-metric-key]')) {
      workoutImportSelections[event.target.dataset.importMetricKey] = event.target.value;
      workoutImportError = '';
      updateWorkoutImportReview();
      return;
    }
    if (event.target.matches('#workoutReviewForm [name="reviewPlan"]')) {
      reviewPlanId = event.target.value;
      return;
    }
  });

  root.addEventListener('keydown', (event) => {
    const input = event.target.closest('.workout-metric-picker .search-field');
    if (!input || event.key !== 'Escape') return;
    const picker = input.closest('.workout-metric-picker');
    const row = picker.dataset.pickerType === 'exercise'
      ? exerciseRows[Number(picker.dataset.pickerIndex)]
      : outcomeRows[Number(picker.dataset.pickerIndex)];
    row.isOpen = false;
    const parts = getPickerParts(picker);
    setMetricPickerOpen(false, parts.suggestionsContainer, parts.searchInput, parts.expandButton);
  });

  root.addEventListener('click', async (event) => {
    if (!event.target.closest('.workout-metric-picker')) {
      exerciseRows.forEach((row) => { row.isOpen = false; });
      outcomeRows.forEach((row) => { row.isOpen = false; });
      root.querySelectorAll('.workout-metric-picker').forEach((picker) => {
        const parts = getPickerParts(picker);
        setMetricPickerOpen(false, parts.suggestionsContainer, parts.searchInput, parts.expandButton);
      });
    }

    const sessionExerciseCard = event.target.closest('[data-session-exercise]');
    if (sessionExerciseCard) {
      const exerciseIndex = Number(sessionExerciseCard.dataset.sessionExercise);
      if (event.target.closest('[data-hold-stopwatch-toggle]')) {
        if (holdStopwatchExerciseIndex !== exerciseIndex) {
          resetHoldStopwatch();
          holdStopwatchExerciseIndex = exerciseIndex;
        }
        if (holdStopwatchStartedAt === null) {
          holdStopwatchStartedAt = Date.now();
          holdStopwatchInterval = setInterval(updateHoldStopwatch, 100);
        } else {
          pauseHoldStopwatch();
        }
        updateHoldStopwatch();
        return;
      }
      if (event.target.closest('[data-hold-stopwatch-reset]')) {
        resetHoldStopwatch();
        return;
      }
      const addSetButton = event.target.closest('.workout-add-set');
      if (addSetButton && sessionSets[exerciseIndex]?.length && sessionRecordedAt === null) {
        sessionRecordedAt = Date.now();
      }
    }

    const finishExerciseButton = event.target.closest('[data-finish-exercise]');
    if (finishExerciseButton) {
      pauseHoldStopwatch();
      if (!sessionSets[activeExerciseIndex]?.length) return;
      clearHoldStopwatch();
      completedExercises[activeExerciseIndex] = true;
      activeExerciseIndex = sessionPlan.exercises.findIndex(
        (_, index) => index > activeExerciseIndex && !completedExercises[index]
      );
      if (activeExerciseIndex < 0) {
        activeExerciseIndex = sessionPlan.exercises.length;
      }
      render();
      focusSessionStep();
      return;
    }

    const finishEditButton = event.target.closest('[data-finish-edit]');
    if (finishEditButton) {
      const editedSets = sessionSets[editingExerciseIndex] || [];
      if (!editedSets.length) return;
      pauseHoldStopwatch();
      clearHoldStopwatch();
      editingExerciseIndex = null;
      render();
      focusSessionStep();
      return;
    }

    const editExerciseButton = event.target.closest('[data-edit-session-exercise]');
    if (editExerciseButton && editingExerciseIndex === null) {
      editingExerciseIndex = Number(editExerciseButton.dataset.editSessionExercise);
      render();
      root.querySelector('[data-finish-edit]')?.focus();
      return;
    }

    const modeButton = event.target.closest('[data-workout-mode]');
    if (modeButton) {
      capturePlanFormValues();
      mode = modeButton.dataset.workoutMode;
      reviewResult = null;
      await refreshData();
      render();
      return;
    }

    if (event.target.closest('[data-new-workout-plan]')) {
      beginNewPlan();
      return;
    }
    if (event.target.closest('[data-workout-import-toggle]')) {
      capturePlanFormValues();
      showWorkoutImport = !showWorkoutImport;
      if (!showWorkoutImport) root.querySelector('[data-workout-prompt-dialog]')?.close();
      render();
      return;
    }
    if (event.target.closest('[data-workout-import-choose]')) {
      root.querySelector('[data-workout-import-file]')?.click();
      return;
    }
    if (event.target.closest('[data-workout-import-review]')) {
      parseWorkoutImportText(workoutImportJson);
      return;
    }
    if (event.target.closest('[data-workout-import-confirm]')) {
      await confirmWorkoutImport();
      return;
    }
    if (event.target.closest('[data-workout-import-cancel]')) {
      pendingWorkoutImport = null;
      workoutImportSelections = {};
      workoutImportFileName = '';
      workoutImportError = '';
      workoutImportJson = '';
      showWorkoutImport = false;
      render();
      return;
    }
    if (event.target.closest('[data-workout-prompt-open]')) {
      root.querySelector('[data-workout-prompt-dialog]')?.showModal();
      return;
    }
    if (event.target.closest('[data-workout-prompt-close]')) {
      root.querySelector('[data-workout-prompt-dialog]')?.close();
      return;
    }
    if (event.target.closest('[data-workout-prompt-copy]')) {
      const status = root.querySelector('[data-workout-prompt-status]');
      try {
        if (!navigator.clipboard?.writeText) throw new Error('Clipboard access is unavailable.');
        await navigator.clipboard.writeText(WORKOUT_CHATBOT_PROMPT);
        status.textContent = 'Prompt copied. Paste it into your chatbot.';
      } catch (error) {
        status.textContent = `Could not copy the prompt: ${error.message} Select the prompt above and copy it manually.`;
      }
      return;
    }
    const planSectionButton = event.target.closest('[data-plan-section]');
    if (planSectionButton) {
      capturePlanFormValues();
      showWorkoutImport = false;
      root.querySelector('[data-workout-prompt-dialog]')?.close();
      if (planSectionButton.dataset.planSection === 'create' && !isEditingPlan) {
        beginNewPlan();
      } else {
        planSection = planSectionButton.dataset.planSection;
        render();
      }
      return;
    }
    if (event.target.closest('[data-add-exercise]')) {
      capturePlanFormValues();
      exerciseRows.push({ metricId: '', targetSets: 3, targetReps: 8, searchTerm: '', isOpen: false });
      render();
      return;
    }
    if (event.target.closest('[data-add-outcome]')) {
      capturePlanFormValues();
      if (outcomeRows.length < 2) {
        outcomeRows.push({ metricId: '', direction: 'increase', searchTerm: '', isOpen: false });
        render();
      }
      return;
    }

    const removeExercise = event.target.closest('[data-remove-exercise]');
    if (removeExercise) {
      capturePlanFormValues();
      exerciseRows.splice(Number(removeExercise.dataset.removeExercise), 1);
      render();
      return;
    }
    const moveExercise = event.target.closest('[data-exercise-move]');
    if (moveExercise) {
      capturePlanFormValues();
      const index = Number(moveExercise.dataset.rowIndex);
      const target = moveExercise.dataset.exerciseMove === 'up' ? index - 1 : index + 1;
      [exerciseRows[index], exerciseRows[target]] = [exerciseRows[target], exerciseRows[index]];
      render();
      return;
    }
    const removeOutcome = event.target.closest('[data-remove-outcome]');
    if (removeOutcome) {
      capturePlanFormValues();
      outcomeRows.splice(Number(removeOutcome.dataset.removeOutcome), 1);
      render();
      return;
    }

    const metricButton = event.target.closest('.workout-metric-picker button[data-metric-id]');
    if (metricButton) {
      const picker = metricButton.closest('.workout-metric-picker');
      const row = picker.dataset.pickerType === 'exercise'
        ? exerciseRows[Number(picker.dataset.pickerIndex)]
        : outcomeRows[Number(picker.dataset.pickerIndex)];
      capturePlanFormValues();
      row.metricId = metricButton.dataset.metricId;
      if (picker.dataset.pickerType === 'exercise') {
        const selectedMetric = metricFor(row.metricId);
        const nextMeasure = selectedMetric?.strengthMeasure || 'reps';
        if ((row.strengthMeasure || 'reps') !== nextMeasure) {
          row.targetReps = nextMeasure === 'reps' ? 8 : undefined;
          row.targetDurationSeconds = nextMeasure === 'duration' ? 30 : undefined;
        }
        row.strengthMeasure = nextMeasure;
      }
      row.searchTerm = '';
      row.isOpen = false;
      render();
      return;
    }

    const clearButton = event.target.closest('.workout-metric-picker .search-dropdown-clear');
    const expandButton = event.target.closest('.workout-metric-picker .search-dropdown-expand');
    if (clearButton || expandButton) {
      const picker = event.target.closest('.workout-metric-picker');
      const row = picker.dataset.pickerType === 'exercise'
        ? exerciseRows[Number(picker.dataset.pickerIndex)]
        : outcomeRows[Number(picker.dataset.pickerIndex)];
      row.searchTerm = clearButton ? '' : row.searchTerm;
      row.isOpen = clearButton ? false : !row.isOpen;
      refreshPicker(
        picker,
        row,
        picker.dataset.pickerType === 'exercise' ? strengthMetrics() : outcomeMetrics(),
        picker.dataset.pickerType === 'exercise' ? 'Strength metric' : 'Outcome metric'
      );
      if (row.isOpen) picker.querySelector('.search-field').focus();
      return;
    }

    const planAction = event.target.closest('[data-plan-action]');
    if (planAction) {
      const plan = plans.find((item) => item.id === planAction.dataset.planId);
      if (!plan) return;
      if (planAction.dataset.planAction === 'start') {
        await startPlan(plan);
      } else if (planAction.dataset.planAction === 'edit') {
        beginEditPlan(plan);
      } else if (planAction.dataset.planAction === 'archive') {
        if (window.confirm(`Archive "${plan.name}"? Past workout history will be kept.`)) {
          await archiveWorkoutPlan(plan.id);
          await onDataChanged();
        }
      }
      return;
    }

    if (event.target.closest('[data-cancel-plan]')) {
      editingPlanId = null;
      isEditingPlan = false;
      exerciseRows = [];
      outcomeRows = [];
      planName = '';
      planSection = 'select';
      render();
      return;
    }
    if (event.target.closest('[data-cancel-session]')) {
      const hasSets = sessionSets.some((sets) => sets.length > 0);
      if (hasSets && !window.confirm('Discard the workout in progress?')) return;
      clearHoldStopwatch();
      sessionPlan = null;
      sessionSets = [];
      completedExercises = [];
      sessionRecordedAt = null;
      activeExerciseIndex = 0;
      editingExerciseIndex = null;
      mode = 'plans';
      planSection = 'select';
      render();
      return;
    }

    const form = event.target.closest('#workoutPlanForm');
    if (form) return;
  });

  root.addEventListener('submit', async (event) => {
    if (event.target.id === 'workoutPlanForm') await savePlan(event);
    else if (event.target.id === 'workoutSessionForm') await saveSession(event);
    else if (event.target.id === 'workoutReviewForm') saveReview(event);
  });

  return {
    async render() {
      if (mode === 'session' && root.querySelector('#workoutSessionForm')) return;
      capturePlanFormValues();
      await refreshData();
      render();
    },
  };
}
