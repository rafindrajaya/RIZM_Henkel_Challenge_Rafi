---
name: code-review
description: Comprehensive review of code changes for bugs, style issues, security, performance, and best practices.
---

# Code Review Skill

When reviewing Pull Requests or code snippets, perform a deep, structured analysis using the following checklist. Provide actionable, constructive feedback.

## 1. Correctness & Logic
- Does the code fulfill the functional requirements?
- Are there any logical flaws, race conditions, or mathematical errors?
- Does it introduce breaking changes to existing APIs?

## 2. Edge Cases & Error Handling
- Are null values, empty lists, out-of-bounds metrics, or unexpected inputs handled gracefully?
- Are errors properly logged with sufficient context?
- Are appropriate exceptions caught and raised?

## 3. Design & Architecture
- Does the code adhere to SOLID principles?
- Is there unnecessary duplication (DRY principle violated)?
- Are components loosely coupled and highly cohesive?

## 4. Performance & Scalability
- Are there expensive operations inside loops? (e.g., database queries, heavy matrix multiplications in training loops).
- Are appropriate data structures used? (e.g., sets for `in` checks instead of lists).
- Are memory leaks possible? (e.g., unclosed files, unreleased tensors).

## 5. Security
- Is user input sanitized and validated to prevent injection attacks?
- Are secrets or API keys hardcoded?
- Is sensitive data logged improperly?

## 6. Style & Readability
- Does the code follow the project's style guide and naming conventions?
- Are variable and function names descriptive?
- Is the code self-documenting? Are complex blocks explained with comments?

## How to Provide Feedback
- **Be specific:** Highlight the exact lines that need changing.
- **Explain *why*:** Don't just say "Change this to X". Say "Change this to X because Y improves performance."
- **Provide alternatives:** Write pseudocode or standard code snippets showing the suggested improvement.
- **Tone:** Remain objective, positive, and collaborative.
