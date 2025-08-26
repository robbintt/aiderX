# Controller Handler Ideas

This document lists potential ideas for controller handlers to extend Aider's capabilities.

## Code Quality & Maintenance

1.  **Linter**: Runs a linter (e.g., flake8, eslint) on modified code and suggests fixes.
2.  **Code Formatter**: Runs a formatter (e.g., black, prettier) on the generated code.
3.  **Docstring Generator**: Adds or updates docstrings for functions and classes.
4.  **Type Hint Adder**: Adds type hints to Python code.
5.  **API Key Checker**: Warns if it sees what looks like a hardcoded API key.
6.  **TODO/FIXME Tracker**: Scans for `TODO` or `FIXME` comments and reminds the user about them.
7.  **Security Vulnerability Scanner**: Runs a basic security scanner (e.g., bandit) on the code.
8.  **Code Complexity Analyzer**: Calculates cyclomatic complexity and warns if a function is too complex.
9.  **Refactoring Suggester**: Identifies code smells (e.g., long methods, duplicate code) and suggests refactorings.
10. **Language Feature Suggester**: Suggests using newer language features where applicable (e.g., Python's walrus operator).
11. **Magic Number Replacer**: Detects magic numbers and suggests replacing them with named constants.
12. **Environment Variable Checker**: Detects use of `os.environ` and checks if a `.env` file or similar is being used.
13. **Code Commenter**: Adds explanatory comments to complex parts of the code.
14. **Dead Code Detector**: Identifies and suggests removing unused variables, imports, or functions.
15. **Regex Validator**: When a regular expression is written, it explains what it does and suggests test cases.

## Testing & Verification

16. **Test Generator**: Suggests generating unit tests for new or modified code.
17. **Test Runner**: Runs existing tests to check for regressions after code changes.

## Project & Context Management

18. **File Adder**: Suggests adding relevant files to the chat context. (already exists)
19. **Dependency Manager**: Detects new imports and suggests adding them to `requirements.txt` or `package.json`.
20. **Large File Warner**: Warns if a very large file is added to chat, suggesting to use repo map instead.
21. **Repo Map Updater**: If repo map is enabled, suggests updating it after significant changes.
22. **Error Log Analyzer**: If the user pastes an error log, it analyzes it and suggests files to look at.
23. **Framework Best Practices Advisor**: For known frameworks (e.g., Django, React), suggests adhering to best practices.
24. **Image Optimizer**: If an image is added to a project, suggests optimizing it.
25. **Shell Command Validator**: Before suggesting a shell command, validates its syntax and warns about potentially dangerous operations
(e.g., `rm -rf /`).

## Git & Documentation

26. **Git Branch Suggester**: Suggests a conventional branch name for the current task.
27. **Commit Message Generator**: Drafts a conventional commit message based on the changes.
28. **Changelog Updater**: Drafts an entry for `CHANGELOG.md` based on the changes.
29. **README Updater**: Suggests updating the README if new features or configuration are added.
30. **Code Documenter (MkDocs/Sphinx)**: If the project uses a doc generator, suggests updating the documentation files.
