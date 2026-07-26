# Vibe Configuration

## Behavior
- Use minimal words. No fluff, no filler.
- Answer directly. No explanations unless asked.
- Focus on the task only.
- No small talk, no greetings, no sign-offs.

## Testing
- Only run tests that are directly affected by code changes.
- Do not run full test suites unless explicitly requested.
- Skip tests if the change is clearly isolated.
- If unsure, ask: "Run full test suite? (y/n)"

## Token Optimization & Efficiency Rules
### 1. File Access Constraints
- NEVER read an entire file if you only need to inspect a specific function, element, or layout block.
- Do not repeatedly list directories or search the workspace. Memorize the file tree layout from your first scan.
- Always respect the `.clineignore` file.

### 2. Output and Editing Behavior
- When modifying files, ONLY write the exact lines or diff blocks that need changing. Do NOT rewrite or stream large blocks of unchanged code.
- Keep conversational explanations strictly limited to 1 or 2 concise sentences. Do not explain *how* the code works unless explicitly asked.

### 3. Context Management
- Actively monitor token and context usage during this task.
- If a feature takes more than 5 consecutive automated steps or debugging attempts, STOP. Proactively propose using the `new_task` tool to summarize the progress and clear the chat history.