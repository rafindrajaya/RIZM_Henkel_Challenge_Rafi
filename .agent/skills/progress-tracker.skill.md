---
name: progress-tracker
description: Monitors project progress and automatically updates the implementation plan and task tracker documents. Triggered when the user says "update progress" or when a new plan or feature is created.
---

# Progress Tracker Skill

This skill defines the instructions and steps for tracking project progress and updating the workspace documentation files (`docs/task.md` and `docs/implementation_plan.md`) along with active chat artifacts.

## Triggers
Activate this skill whenever:
1. The user prompts with "update progress", "status update", "what is left?", or similar.
2. A new plan, feature, or phase is designed or added to the project.
3. Code modifications are successfully implemented, requiring task tracking updates.

## Core Directives

### 1. Identify Progress
- Look at the active workspace changes and git status to see what has been built.
- Scan the code in `src/` to verify if components, APIs, or scripts described in `docs/implementation_plan.md` have been implemented.
- Check if tests run successfully to confirm completion.

### 2. Update Documentation Files
Ensure the following files are kept in sync:
- **Task Tracker:** [docs/task.md](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/aka_ai/docs/task.md)
  - Mark completed tasks with `[x]`.
  - Add new tasks under appropriate phases if new plans or features are created.
- **Implementation Plan:** [docs/implementation_plan.md](file:///Users/mrafiindrajaya/Desktop/Github%20Projects/aka_ai/docs/implementation_plan.md)
  - Mark phases or files with `[x]` or update status descriptions.
  - Document new features or layout modifications under the `Proposed Changes` section.

### 3. Sync Active Chat Artifacts
If an artifact is active in the current chat:
- Update the active chat's `task.md` and `implementation_plan.md` artifacts.
- Keep their contents exactly matching the workspace files.

### 4. Summary Output
- Provide a brief, bulleted list of what was updated (e.g., "Marked Phase 5: pvlib integration as complete in docs/task.md").
- Do not dump the entire content of the updated plans in the response.

## Step-by-Step Update Workflow
1. **Analyze Current Code State**: Inspect files in `src/` to determine actual completion of features.
2. **Read Current Task/Plan**: Read the existing `docs/task.md` and `docs/implementation_plan.md` to see the current checklist.
3. **Resolve Diff**: Identify which checklist items match the completed features.
4. **Update Files**: Modify the files using edit/write tools.
5. **Report to User**: Let the user know the progress has been successfully updated.
