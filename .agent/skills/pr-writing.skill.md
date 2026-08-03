---
name: pr-writing
description: Guides the generation of high-quality, informative Pull Request descriptions.
---

# PR Description Writing Skill

When creating a Pull Request, the description must be comprehensive enough for a reviewer to understand the context, logic, and impact without immediately reading the code. 

## Required Structure

### 1. Title
Format: `<Type>: <Brief description> (e.g., "feat: implement physics engine for electrolyzer")`

### 2. What was changed?
- High-level summary of the new feature, bug fix, or refactor.
- List specific components, modules, or APIs that were added or modified.

### 3. Why was it changed?
- Link to the original issue or ticket.
- Explain the business value or technical necessity (e.g., "The previous model lacked thermal loss calculations, leading to inaccurate twin predictions").

### 4. Where was it changed?
- Briefly list the key files or directories affected. (e.g., `src/physics/electrolyzer.py`, `tests/test_physics.py`).

### 5. Implementation Logic / Pseudocode
- Explain the core logic of the change.
- Provide a brief pseudocode or flowchart description if the algorithm is complex.
- Example:
  ```
  1. Fetch real-time sensor data
  2. Normalize inputs (temp, pressure)
  3. Calculate theoretical efficiency based on Nernst equation
  4. Apply degradation factor
  5. Return predicted output
  ```

### 6. Testing & Validation
- How was this tested? (Unit tests added, manual testing, metrics tracked).
- Provide instructions for the reviewer to verify the change locally if needed.
