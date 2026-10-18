import { renderMetricPicker, setMetricPickerOpen } from './metric-picker.js';
import { mountStrengthSetEditor } from './strength-set-editor.js';
import { summarizeWorkoutBlock, validateWorkoutPlan } from './workout-model.js';

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

export function mountWorkoutsView(root, {
  listMetrics,
  listCategories,
  listEntries,
  listWorkoutPlans,
  listWorkoutSessions,
  saveWorkoutPlan,
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
  let editingPlanId = null;
  let isEditingPlan = false;
  let planName = '';
  let exerciseRows = [];
  let outcomeRows = [];
  let sessionPlan = null;
  let sessionSets = [];
  let reviewResult = null;
  let reviewRange = null;
  let setEditors = [];

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

  function renderPlans() {
    const planCards = plans.filter((plan) => !plan.isArchived).map((plan) => {
      const canStart = plan.exercises.every((exercise) => metricFor(exercise.metricId));
      const exerciseLabels = plan.exercises.map((exercise) => {
        const metric = metricFor(exercise.metricId);
        return `<li>${escapeHtml(metric?.name || 'Archived exercise')} — ${exercise.targetSets} × ${exercise.targetReps}</li>`;
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
    return `
      <div class="panel">
        <h2 class="workflow-card-heading">Workout plans</h2>
        <p class="muted-text">Build a reusable exercise sequence, then record the sets you complete.</p>
        <button type="button" class="primary" data-new-workout-plan>Create plan</button>
      </div>
      <div id="workoutPlanList" class="list">
        ${planCards || '<p class="panel">No plans yet. Create one to get started.</p>'}
      </div>
      ${isEditingPlan ? renderPlanEditor() : ''}
    `;
  }

  function renderExerciseRows() {
    return exerciseRows.map((row, index) => `
      <article class="panel workout-exercise-card" data-exercise-row="${index}">
        <h3>Exercise ${index + 1}</h3>
        ${pickerMarkup('exercise', index, row, 'Strength metric')}
        <div class="strength-grid">
          <label>Target sets<input type="number" min="1" step="1" data-target-sets="${index}" value="${escapeHtml(row.targetSets)}" required /></label>
          <label>Target reps<input type="number" min="1" step="1" data-target-reps="${index}" value="${escapeHtml(row.targetReps)}" required /></label>
        </div>
        <div class="workout-exercise-actions">
          <button type="button" class="secondary" data-exercise-move="up" data-row-index="${index}" ${index === 0 ? 'disabled' : ''}>Move up</button>
          <button type="button" class="secondary" data-exercise-move="down" data-row-index="${index}" ${index === exerciseRows.length - 1 ? 'disabled' : ''}>Move down</button>
          <button type="button" class="secondary" data-remove-exercise="${index}">Remove</button>
        </div>
      </article>
    `).join('');
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
        <h2 class="workflow-card-heading">${editingPlanId ? 'Edit workout plan' : 'Create workout plan'}</h2>
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

  function renderSession() {
    const selectedPlan = sessionPlan;
    if (!selectedPlan) return '';
    const exerciseCards = selectedPlan.exercises.map((exercise, index) => {
      const metric = metricFor(exercise.metricId);
      const loadUnit = metric?.unitName || 'kg';
      const previous = entries
        .filter((entry) => entry.metricId === exercise.metricId)
        .sort((a, b) => new Date(b.recordedAt) - new Date(a.recordedAt))[0];
      const previousSets = previous?.sets || [];
      const previousHtml = previousSets.length
        ? `<p class="muted-text">Previous: ${previousSets.map((set) => `${Number(set.loadValue ?? set.loadKg ?? set.load_kg ?? 0)} ${escapeHtml(loadUnit)} × ${escapeHtml(set.reps)} reps`).join(' · ')}</p>`
        : '';
      return `
        <article class="panel workout-exercise-card" data-session-exercise="${index}">
          <h3>${escapeHtml(metric?.name || 'Archived exercise')}</h3>
          <p class="muted-text">Target: ${exercise.targetSets} sets × ${exercise.targetReps} reps</p>
          ${previousHtml}
          <div class="strength-grid">
            <label>Load (${escapeHtml(loadUnit)})<input type="number" class="workout-load" min="0" step="0.5" value="${escapeHtml(previous?.loadValue ?? previous?.loadKg ?? previous?.value ?? '')}" /></label>
            <label>Reps<input type="number" class="workout-reps" min="1" step="1" value="${exercise.targetReps}" /></label>
          </div>
          <button type="button" class="secondary workout-add-set">Add set</button>
          <div class="list workout-set-list"></div>
        </article>
      `;
    }).join('');
    return `
      <div class="panel">
        <h2 class="workflow-card-heading">${escapeHtml(selectedPlan.name)}</h2>
        <form id="workoutSessionForm" class="stacked-form">
          <div class="strength-grid">
            <label>Date<input type="date" name="workoutDate" value="${dateInputValue(new Date())}" required /></label>
            <label>Time<input type="time" name="workoutTime" value="${new Date().toTimeString().slice(0, 5)}" required /></label>
          </div>
          ${exerciseCards}
          <button type="submit" class="primary">Save workout</button>
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
          <ul>
            ${session.exercises.map((exercise) => {
              const entry = entryMap.get(exercise.entryId);
              const sets = entry?.sets || [];
              const detail = sets.length
                ? sets.map((set) => `${Number(set.loadValue ?? set.loadKg ?? set.load_kg ?? 0)} ${metricFor(exercise.metricId)?.unitName || 'kg'} × ${set.reps}`).join(' · ')
                : 'Entry no longer available';
              return `<li><strong>${escapeHtml(exercise.metricName)}</strong>: ${escapeHtml(detail)}</li>`;
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
            detail = `Estimated 1RM: ${progress.firstEstimatedOneRepMax.toFixed(1)} ${loadUnit} → ${progress.latestEstimatedOneRepMax.toFixed(1)} ${loadUnit} (${sign}${progress.change.toFixed(1)} ${loadUnit} across ${progress.sessions} sessions).`;
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
      row.targetReps = form.querySelector(`[data-target-reps="${index}"]`)?.value ?? row.targetReps;
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
    editingPlanId = null;
    isEditingPlan = true;
    planName = '';
    exerciseRows = [{ metricId: '', targetSets: 3, targetReps: 8, searchTerm: '', isOpen: false }];
    outcomeRows = [];
    render();
    root.querySelector('[name="planName"]')?.focus();
  }

  function beginEditPlan(plan) {
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
      await onDataChanged();
    } catch (error) {
      window.alert(error.message);
    }
  }

  async function saveSession(event) {
    event.preventDefault();
    const form = event.target;
    try {
      const date = form.elements.workoutDate.value;
      const time = form.elements.workoutTime.value;
      const recordedAt = new Date(`${date}T${time}`).toISOString();
      const exercises = sessionPlan.exercises.map((exercise, index) => ({
        metricId: exercise.metricId,
        metricName: metricFor(exercise.metricId)?.name || 'Archived exercise',
        sets: setEditors[index].getSets(),
      }));
      const saved = await saveWorkoutSession(sessionPlan, { recordedAt, exercises });
      sessionPlan = null;
      sessionSets = [];
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
    const plan = plans.find((item) => item.id === form.elements.reviewPlan.value);
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
    setEditors = Array.from(root.querySelectorAll('[data-session-exercise]')).map((card, index) => {
      const exercise = sessionPlan.exercises[index];
      const loadInput = card.querySelector('.workout-load');
      const repsInput = card.querySelector('.workout-reps');
      const editor = mountStrengthSetEditor({
        container: card.querySelector('.workout-set-list'),
        loadInput,
        repsInput,
        addButton: card.querySelector('.workout-add-set'),
        defaultReps: exercise.targetReps,
        loadUnit: metricFor(exercise.metricId)?.unitName || 'kg',
        onChange: (sets) => { sessionSets[index] = sets; },
      });
      editor.replace(sessionSets[index] || []);
      return editor;
    });
  }

  function render() {
    if (!root) return;
    if (mode === 'session') {
      root.innerHTML = `${renderModes()}${renderSession()}`;
      mountSessionEditors();
      return;
    }
    const content = mode === 'plans'
      ? renderPlans()
      : mode === 'history'
        ? renderHistory()
        : renderReview();
    root.innerHTML = `${renderModes()}${content}`;
    if (mode === 'plans' && isEditingPlan) renderPlanPickers();
    if (mode === 'review' && reviewRange) {
      const form = root.querySelector('#workoutReviewForm');
      if (form) {
        form.elements.reviewStart.value = dateInputValue(reviewRange.startAt);
        form.elements.reviewEnd.value = dateInputValue(reviewRange.endAt);
      }
    }
  }

  root.addEventListener('input', (event) => {
    const input = event.target;
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
      render();
      return;
    }
    if (event.target.closest('[data-cancel-session]')) {
      const hasSets = setEditors.some((editor) => editor.getSets().length > 0);
      if (hasSets && !window.confirm('Discard the workout in progress?')) return;
      sessionPlan = null;
      sessionSets = [];
      mode = 'plans';
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
