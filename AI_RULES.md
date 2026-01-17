# Codex Development Rules

## Project Context
See [CLAUDE.md](CLAUDE.md) for full architecture, scoring logic, classification rules, and deployment workflows.

---

## 1. Discovery & Planning Phase
- **FIRST**: Read and understand the codebase structure
- **Map dependencies**: Identify all files/modules that relate to the task
- **Create detailed plan**: Write to `tasks/todo.md` with:
  - Clear, atomic tasks (each task = 1 specific change)
  - Estimated risk level (low/medium/high) for each task
  - Files that will be modified for each task
  - Dependencies between tasks
- **Checkpoint**: Wait for human approval before proceeding

## 2. Task Breakdown Standards
Each todo item must be:
- [x] Completable in isolation
- [x] Testable independently
- [x] Reversible if needed
- [x] Clear success criteria

Use checkboxes: `- [ ]` for pending, `- [x]` for complete

## 3. Execution Principles

### Simplicity First (CRITICAL)
- **Minimum viable change**: Touch the fewest lines possible
- **Single responsibility**: Each commit/change does ONE thing
- **Avoid refactoring**: Unless explicitly required for the task
- **Prefer composition over modification**: Add new code rather than changing working code when possible

### Communication Standards
- **After each task**: Provide HIGH-LEVEL summary only
  - What changed (1-2 sentences)
  - Which file(s) were modified
  - NO code dumps unless specifically requested
- **Progressive updates**: Check off tasks in `tasks/todo.md` as completed
- **Flag blockers immediately**: If stuck, explain why and ask for guidance

## 4. Quality Standards

### Zero Tolerance for Laziness
- **Root cause analysis**: Always find and fix the underlying issue
- **No temporary fixes**: No "quick hacks" or "will fix later"
- **No commenting out code**: Either fix it or remove it
- **Complete error handling**: Every edge case must be handled
- **Senior-level standards**: Code should be production-ready, not prototype-quality

### Testing Requirements
- [x] Verify after each change: Test that the specific change works
- [x] Regression check: Ensure existing functionality still works
- [x] Document test steps: In `tasks/todo.md`, note how you verified each change

## 5. Code Change Philosophy

### Surgical Precision
- **Scope**: Only touch code directly related to the task
- **Side effects**: Avoid changing function signatures, interfaces, or contracts
- **Backwards compatibility**: Maintain unless explicitly instructed otherwise
- **Import statements**: Only add what's needed, remove unused imports

### Before Writing Code, Ask:
1. Is this the simplest possible solution?
2. Am I changing the minimum amount of code?
3. Could this break anything else?
4. Is there a way to do this with NO changes to existing code?

## 6. Documentation & Review

### During Development
- Keep `tasks/todo.md` updated in real-time
- Mark completed: `- [x] Task description [DONE]`
- Mark blocked: `- [ ] Task description [BLOCKED: reason]`

### After Completion -> Add to `tasks/todo.md`:
```markdown
## Review Summary
### Changes Made
- File 1: What changed and why
- File 2: What changed and why

### Testing Performed
- Test 1 result
- Test 2 result

### Risk Assessment
- Low/Medium/High risk changes
- Potential issues to watch

### Follow-up Items
- Any technical debt created
- Future improvements needed
```

## 7. Error Handling Protocol
When something doesn't work:
1. **Read error messages completely** - don't guess
2. **Trace the stack** - find exact failure point
3. **Understand the cause** - not just the symptom
4. **Fix properly** - address root cause
5. **Prevent recurrence** - add safeguards if needed

## 8. Anti-Patterns to Avoid
- X Making multiple changes at once
- X Refactoring while fixing bugs
- X Adding features while fixing issues
- X Changing code you don't understand
- X Copying code without understanding it
- X Leaving debug code in place
- X "It works on my machine" mentality

## 9. Pre-Commit Checklist
Before marking any task complete:
- [ ] Code does exactly what task requires, nothing more
- [ ] No unrelated changes included
- [ ] Error handling is complete
- [ ] No temporary/debug code remains
- [ ] Tested in isolation
- [ ] Tested with existing features
- [ ] `tasks/todo.md` updated

## 10. Communication Red Flags
If you catch yourself saying:
- "This should work..." -> **TEST IT**
- "Probably just..." -> **VERIFY IT**
- "Quick fix..." -> **DO IT PROPERLY**
- "I'll come back to..." -> **FIX IT NOW**
- "Not sure why but..." -> **UNDERSTAND IT FIRST**

---

## Key Improvements Over Basic Rules
1. [x] More specific task breakdown guidance
2. [x] Explicit anti-patterns
3. [x] Pre-commit checklist
4. [x] Risk assessment framework
5. [x] Mandatory testing requirements
6. [x] Communication red flags
7. [x] Systematic debugging approach
8. [x] Structured review format
