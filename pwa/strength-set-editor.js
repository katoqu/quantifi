export function normalizeStrengthSet(loadValue, measureValue, strengthMeasure = 'reps') {
  const load = String(loadValue ?? '').trim() === '' ? null : Number(loadValue);
  if (load !== null && (!Number.isFinite(load) || load < 0)) {
    throw new Error('Enter a valid load for the set.');
  }
  if (strengthMeasure === 'duration') {
    const durationSeconds = Number(measureValue);
    if (String(measureValue).trim() === '' || !Number.isFinite(durationSeconds) || durationSeconds <= 0) {
      throw new Error('Enter a duration greater than zero seconds.');
    }
    return { ...(load === null ? {} : { loadValue: load }), durationSeconds };
  }
  const reps = Number(measureValue);
  if (load === null) throw new Error('Enter a valid load for the set.');
  if (String(measureValue).trim() === '' || !Number.isInteger(reps) || reps < 1) {
    throw new Error('Enter a whole-number rep count greater than zero.');
  }
  return { loadValue: load, reps };
}

export function mountStrengthSetEditor({
  container,
  loadInput,
  repsInput,
  addButton,
  onChange,
  defaultReps = 5,
  loadUnit = 'kg',
  strengthMeasure = 'reps',
}) {
  let sets = [];
  let editingIndex = null;
  let currentLoadUnit = loadUnit;
  let currentMeasure = strengthMeasure;
  let currentMeasureValue = strengthMeasure === 'duration' ? 30 : defaultReps;

  const emitChange = () => onChange?.(sets.map((set) => ({ ...set })));

  const render = () => {
    container.innerHTML = sets.length
      ? sets.map((set, index) => {
        const measureValue = currentMeasure === 'duration' ? set.durationSeconds : set.reps;
        const measureLabel = currentMeasure === 'duration' ? 'Hold (seconds)' : 'Reps';
        const setDescription = currentMeasure === 'duration'
          ? `${set.durationSeconds} sec${set.loadValue === undefined ? '' : ` · ${set.loadValue} ${currentLoadUnit}`}`
          : `${set.loadValue.toFixed(1)} ${currentLoadUnit} × ${set.reps} reps`;
        if (editingIndex === index) {
          return `
            <div class="item edit-mode">
              <strong>Set ${index + 1} (Editing)</strong>
              <div class="strength-grid" style="margin: 0.5rem 0;">
                <label>
                  Load (${currentLoadUnit})${currentMeasure === 'duration' ? ' (optional)' : ''}
                  <input type="number" class="strength-set-edit-load" step="0.5" min="0" value="${set.loadValue ?? ''}" ${currentMeasure === 'duration' ? '' : 'required'} />
                </label>
                <label>
                  ${measureLabel}
                  <input type="number" class="strength-set-edit-measure" step="${currentMeasure === 'duration' ? 'any' : '1'}" min="${currentMeasure === 'duration' ? '0.01' : '1'}" value="${measureValue}" required />
                </label>
              </div>
              <div style="display: flex; gap: 0.5rem; width: 100%;">
                <button type="button" data-save-strength-set class="primary" style="flex: 1;">Save</button>
                <button type="button" data-cancel-strength-set class="secondary" style="flex: 1;">Cancel</button>
              </div>
            </div>
          `;
        }
        return `
          <div class="item">
            <strong>Set ${index + 1}</strong>
            <div>${setDescription}</div>
            <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
              <button type="button" data-edit-strength-set="${index}" class="secondary">Edit</button>
              <button type="button" data-remove-strength-set="${index}" class="secondary">Remove</button>
            </div>
          </div>
        `;
      }).join('')
      : '<p>No sets yet.</p>';
  };

  const addCurrentSet = () => {
    const set = normalizeStrengthSet(loadInput.value, repsInput.value, currentMeasure);
    sets.push(set);
    render();
    if (set.loadValue !== undefined) loadInput.value = set.loadValue;
    repsInput.value = currentMeasure === 'duration' ? currentMeasureValue : defaultReps;
    emitChange();
  };

  addButton.addEventListener('click', () => {
    try {
      addCurrentSet();
    } catch (error) {
      window.alert(error.message);
      (loadInput.value.trim() ? repsInput : loadInput).focus();
    }
  });

  container.addEventListener('click', (event) => {
    const removeButton = event.target.closest('[data-remove-strength-set]');
    if (removeButton) {
      const index = Number(removeButton.dataset.removeStrengthSet);
      sets.splice(index, 1);
      if (editingIndex === index) editingIndex = null;
      else if (editingIndex > index) editingIndex -= 1;
      render();
      emitChange();
      return;
    }

    const editButton = event.target.closest('[data-edit-strength-set]');
    if (editButton) {
      editingIndex = Number(editButton.dataset.editStrengthSet);
      render();
      return;
    }

    if (event.target.closest('[data-save-strength-set]')) {
      try {
        const load = container.querySelector('.strength-set-edit-load');
        const measureValue = container.querySelector('.strength-set-edit-measure');
        sets[editingIndex] = normalizeStrengthSet(load.value, measureValue.value, currentMeasure);
        editingIndex = null;
        render();
        emitChange();
      } catch (error) {
        window.alert(error.message);
      }
      return;
    }

    if (event.target.closest('[data-cancel-strength-set]')) {
      editingIndex = null;
      render();
    }
  });

  return {
    addCurrentSet,
    clear() {
      sets = [];
      editingIndex = null;
      render();
      emitChange();
    },
    getSets() {
      return sets.map((set) => ({ ...set }));
    },
    render,
    setLoadUnit(unit) {
      currentLoadUnit = unit || 'kg';
      render();
    },
    setMeasure(measure, defaultValue) {
      currentMeasure = measure === 'duration' ? 'duration' : 'reps';
      currentMeasureValue = defaultValue ?? (currentMeasure === 'duration' ? 30 : defaultReps);
      render();
    },
    replace(nextSets) {
      sets = nextSets.map((set) => normalizeStrengthSet(
        set.loadValue ?? set.loadKg ?? set.load_kg,
        currentMeasure === 'duration' ? set.durationSeconds : set.reps,
        currentMeasure
      ));
      editingIndex = null;
      render();
      emitChange();
    },
  };
}
