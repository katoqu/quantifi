export default {
  testRunner: 'command',
  commandRunner: {
    command: 'node --test pwa/workout-model.test.js pwa/workout-import.test.js pwa/strength.test.js',
  },
  mutate: [
    'pwa/workout-model.js',
    'pwa/workout-import.js',
    'pwa/strength.js',
  ],
  coverageAnalysis: 'off',
  reporters: ['clear-text', 'progress', 'html'],
  htmlReporter: {
    fileName: 'reports/mutation/mutation.html',
  },
};
