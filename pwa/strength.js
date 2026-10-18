export function computeStrengthValue(entry, aggType) {
  const sets = entry.sets || [];
  if (!Array.isArray(sets) || sets.length === 0) {
    const baseValue = Number(entry.value ?? entry.loadValue ?? entry.loadKg ?? 0);
    if (aggType === 'Total Volume') {
      return baseValue * 10 * 3;
    } else if (aggType === 'Max e1RM') {
      return baseValue * (1 + 30 / 30);
    }
    return baseValue;
  }

  const setData = sets.map((s) => ({
    load: Number(s.loadValue ?? s.loadKg ?? s.load_kg ?? 0),
    reps: Number(s.reps ?? 10),
  }));

  if (aggType === 'Total Volume') {
    return setData.reduce((sum, s) => sum + s.load * s.reps, 0);
  } else if (aggType === 'Max Load') {
    return Math.max(...setData.map((s) => s.load));
  } else if (aggType === 'Average Load') {
    return setData.reduce((sum, s) => sum + s.load, 0) / setData.length;
  } else if (aggType === 'Max e1RM') {
    const e1rms = setData.map((s) => s.load * (1 + s.reps / 30));
    return Math.max(...e1rms);
  }
  return setData.reduce((sum, s) => sum + s.load, 0);
}

export function formatStrengthSession(entry, loadUnit = 'kg') {
  if (!entry) return '—';
  const sets = entry.sets || [];
  if (!Array.isArray(sets) || sets.length === 0) {
    return entry.value !== null && entry.value !== undefined ? `${Number(entry.value).toFixed(1)} ${loadUnit}` : '—';
  }
  const summaryLoad = Number(
    entry.loadValue
      ?? entry.loadKg
      ?? entry.value
      ?? sets[0].loadValue
      ?? sets[0].loadKg
      ?? sets[0].load_kg
      ?? 0
  ).toFixed(1);
  const repsSeries = sets.map((s) => s.reps).join('/');
  return `${summaryLoad} ${loadUnit} × ${repsSeries} reps × ${sets.length} sets`;
}

export function getLastStrengthSet(entry) {
  const sets = Array.isArray(entry.sets) ? entry.sets : [];
  if (sets.length > 0) {
    const lastSet = sets[sets.length - 1];
    return {
      loadValue: Number(lastSet.loadValue ?? lastSet.loadKg ?? lastSet.load_kg ?? 0),
      reps: Number(lastSet.reps ?? 0),
    };
  }
  return {
    loadValue: Number(entry.loadValue ?? entry.loadKg ?? entry.value ?? 0),
    reps: Number(entry.reps ?? 0),
  };
}

function roundIncrementToWeightStep(increment) {
  const steps = [0.5, 1, 1.25, 2.5, 5];
  return steps.reduce((best, step) => {
    return Math.abs(step - increment) < Math.abs(best - increment) ? step : best;
  }, steps[0]);
}

export function buildStrengthProgressRecommendation(entries, loadUnit = 'kg') {
  if (!entries || entries.length === 0) return null;
  const latest = entries[0];
  const latestSet = getLastStrengthSet(latest);

  if (latestSet.reps === 12) {
    const desiredIncrease = latestSet.loadValue * 0.05;
    const increment = roundIncrementToWeightStep(desiredIncrease);
    return `Try increasing your last set by +${increment.toFixed(2).replace(/\.00$/, '')} ${loadUnit} (about 5%).`;
  }

  const lastFour = entries.slice(0, 4);
  const unchangedCount = lastFour.filter((entry) => {
    const set = getLastStrengthSet(entry);
    return set.loadValue === latestSet.loadValue && set.reps === latestSet.reps;
  }).length;

  if (unchangedCount === 4) {
    return 'Your last set load and reps have been the same for 4 sessions. Try adding 2 more reps to the last set.';
  }

  return null;
}
