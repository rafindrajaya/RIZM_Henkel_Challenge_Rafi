---
name: python-best-practices
description: Applies state-of-the-art Python best practices for code structure, documentation, and maintainability.
---

# Python Best Practices Skill

When writing or refactoring Python code, strictly adhere to the following best practices:

## 1. Code Structure & Style
- **Linter & Formatter**: Assume the use of `ruff` for linting and formatting. Adhere to PEP 8 standards.
- **Type Hinting**: All functions, methods, and classes must have complete type hints (PEP 484). Use modern syntax (e.g., `list[str]` instead of `List[str]`, `|` instead of `Union`).
- **Data Structures**: Use `dataclasses` or `pydantic` models for structured data and configuration, rather than raw dictionaries.
- **Project Layout**: Follow a `src/` layout (e.g., `src/my_package/`). Tests should live in a separate `tests/` directory at the root level.
- **Dependency Management**: Use modern tools like `poetry`, `uv`, or `pip-tools`. Pin dependencies in production.

## 2. Documentation
- **Docstrings**: Use Google-style or NumPy-style docstrings for every module, class, and public function.
- **Contents**: Include a brief description, `Args:`, `Returns:`, and `Raises:` sections where applicable.
- **Inline Comments**: Keep them sparse. Code should be self-documenting. Use inline comments only to explain "why" complex algorithms or non-obvious business logic exist, not "what" they do.

## 3. Error Handling
- Never use bare `except:` blocks. Always catch specific exceptions.
- Use custom exception classes for domain-specific errors (e.g., `ElectrolyzerConvergenceError`).
- Prefer returning `None` or using `Optional` types for expected absence of data, rather than raising exceptions for normal control flow.

## 4. Testing & Reliability
- Design code to be testable (Dependency Injection).
- Write tests using `pytest`. Use `fixtures` extensively for setup and teardown.
- Aim for high test coverage on core mathematical and logical functions.
