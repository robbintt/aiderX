# Controller Architecture Design

This document outlines the proposed architecture for the controller and its handlers in Aider.

## Core Principles

1.  **Optional and Off by Default**: The controller is an advanced, optional feature. It should be disabled by default to avoid unexpected behavior, latency, or costs for users.
2.  **Explicit Activation**: The controller is activated only when a user explicitly provides a `controller-model`. This serves as a clear, single switch to enable the feature, avoiding the need for extra flags like `--use-controller`.
3.  **Modular and Extensible**: The architecture should allow for easy addition of new handlers, both by the core developers and potentially by users or plugins in the future.

## Implementation Details

### Controller Activation

The `Controller` class in `aider/coders/controller_coder.py` will be the central point for this logic.

-   The `Controller.__init__` method will accept an optional `controller_model` argument, defaulting to `None`.
-   If `controller_model` is `None`, the controller will remain inactive. Its `run()` method will effectively be a no-op, and no handlers will be instantiated.
-   This keeps the controller logic self-contained and avoids the need for conditional checks in other parts of the codebase.

### Handler Registration and Configuration

To make the controller extensible, users will be able to register and configure handlers.

#### User Experience

Users can specify which handlers to use via two methods:

1.  **Command-Line Argument**: A `--controller-handlers` argument will accept a comma-separated list of handler names for ad-hoc use.
    ```bash
    aider --controller-model gpt-4o --controller-handlers file-adder,code-linter
    ```
2.  **YAML Configuration (`.aider.conf.yml`)**: For persistent and more complex configurations, users can define handlers in their config file.
    ```yaml
    controller-model: gpt-4o
    controller-handlers:
      - file-adder
      - name: code-linter
        lint-command: "flake8 {fname}"
    ```

Command-line arguments will override settings from the configuration file.

#### Internal Architecture

A handler registry will be implemented to support this dynamic loading:

1.  **Handler Registry**: A global registry (e.g., a dictionary) will map handler names (strings) to their corresponding handler classes. Handlers are located in the `aider/plugins/handlers/` directory. Each handler class will be responsible for registering itself.
2.  **Controller Initialization**: The `Controller.__init__` method will:
    -   Check if a `controller_model` is provided.
    -   If so, it will look at the `controller-handlers` configuration from the CLI and YAML file.
    -   It will iterate through the requested handler names, look up the class in the registry, and instantiate it, passing the `controller_model` and any handler-specific configuration.

### Handler Execution Flow

To provide maximum flexibility, handlers can be designed to run at different stages of the Aider workflow. This allows them to prepare context, act as tools for the main model, or review the main model's output. While the initial implementation will focus on Pre-Generation handlers, we can categorize the potential execution points into three phases:

1.  **Pre-Generation (Before Main Model Request)**:
    -   Handlers in this phase run after the user has entered their prompt but before the request is sent to the main coding LLM.
    -   **Purpose**: To enrich the context provided to the main model.
    -   **Examples**:
        -   A linter that runs on the current files and adds the linting errors to the prompt.
        -   A handler that analyzes the user's request and suggests adding other relevant files to the chat.

2.  **In-Generation (During Main Model Request - Tool Use)**:
    -   Handlers in this phase act as tools that the main LLM can choose to call during its reasoning process. This requires a model that supports tool use (function calling).
    -   **Purpose**: To provide the main model with the ability to interact with the user's environment and gather information.
    -   **Examples**:
        -   `read_file`: Allows the LLM to read a file that wasn't initially added to the chat.
        -   `list_files`: Allows the LLM to explore the directory structure.
        -   `execute_bash_command`: Allows the LLM to run commands to understand the state of the system.

3.  **Post-Generation (After Main Model Response)**:
    -   Handlers in this phase run after the main LLM has generated a response (e.g., a code change).
    -   **Purpose**: To validate, refine, or supplement the main model's output.
    -   **Examples**:
        -   A code formatter that automatically formats the generated code.
        -   A test runner that executes tests against the proposed changes and reports back failures.
        -   A commit message generator that drafts a commit message based on the applied diff.

### Default Behavior

If a `controller_model` is provided but the user does not specify any handlers, a default set of safe and useful handlers will be activated. The `FileAdderHandler` is a good candidate for being a default handler. This provides a sensible out-of-the-box experience for users who enable the controller.
