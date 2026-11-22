# Agent instructions

## Testing

- For small changes, use focused checks while iterating rather than rerunning the full test suite after every tweak.
- Run the relevant full test suite once before finishing.
- Avoid repeating tests when no code has changed.
- Run the focused mutation pilot with `npm run test:mutation`. Treat its current 67.6% score as a baseline, not a CI threshold; review surviving mutants for meaningful gaps and do not chase equivalent mutants. Aim for 70–80% on important logic before considering a score gate.
