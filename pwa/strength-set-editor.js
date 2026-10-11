export function normalizeStrengthSet(loadValue, repsValue) {
  const loadKg = Number(loadValue);
  const reps = Number(repsValue);
  if (String(loadValue).trim() === '' || !Number.isFinite(loadKg) || loadKg < 0) {
    throw new Error('Enter a valid load for the set.');
  }
  if (String(repsValue).trim() === '' || !Number.isInteger(reps) || reps < 1) {
    throw new Error('Enter a whole-number rep count greater than zero.');
  }
  return { loadKg, reps };
}

export function mountStrengthSetEditor({
  container,
  loadInput,
  repsInput,
  addButton,
  onChange,
  defaultReps = 5,
}) {
  let sets = [];
  let editingIndex = null;

  const emitChange = () => onChange?.(sets.map((set) => ({ ...set })));

  const render = () => {
    container.innerHTML = sets.length
      ? sets.map((set, index) => {
        if (editingIndex === index) {
          return `
            <div class="item edit-mode">
              <strong>Set ${index + 1} (Editing)</strong>
              <div class="strength-grid" style="margin: 0.5rem 0;">
                <label>
                  Load (kg)
                  <input type="number" class="strength-set-edit-load" step="0.5" min="0" value="${set.loadKg}" />
                </label>
                <label>
                  Reps
                  <input type="number" class="strength-set-edit-reps" step="1" min="1" value="${set.reps}" />
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
            <div>${set.loadKg.toFixed(1)} kg × ${set.reps} reps</div>
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
    const set = normalizeStrengthSet(loadInput.value, repsInput.value);
    sets.push(set);
    render();
    loadInput.value = set.loadKg;
    repsInput.value = defaultReps;
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
        const reps = container.querySelector('.strength-set-edit-reps');
        sets[editingIndex] = normalizeStrengthSet(load.value, reps.value);
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
    replace(nextSets) {
      sets = nextSets.map((set) => normalizeStrengthSet(set.loadKg ?? set.load_kg, set.reps));
      editingIndex = null;
      render();
      emitChange();
    },
  };
}
