# Controller Architecture Design

This document outlines the proposed architecture for the controller and its handlers in Aider.

## Core Principles

1.  **Optional and Off by Default**: The controller is an advanced, optional feature. It should be disabled by default to avoid unexpected behavior, latency, or costs for users.
2.  **Explicit Activation**: The controller is activated only when a user explicitly provides a `controller-model`. This serves as a clear, single switch to enable the feature, avoiding the need for extra flags like `--use-controller`.
3.  **Modular and Extensible**: The architecture should allow for easy addition of new handlers, both by the core developers and potentially by users or extensions in the future.

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

1.  **Command-Line Argument**: Handlers can be specified using one or more `--handlers` arguments. For simple handlers without configuration, you can provide them as a comma-separated list.
    ```bash
    aider --controller-model gpt-4o --handlers file-adder,code-linter,test-runner
    ```
    For handlers that require configuration, it is best to use a separate `--handlers` argument for each handler to avoid issues with shell quoting. Each argument can be a simple handler name or a quoted dictionary string for configuration.
    ```bash
    aider --controller-model gpt-4o \
      --handlers file-adder \
      --handlers "{'name': 'test-runner', 'config': {'command': 'pytest'}}"
    ```
2.  **YAML Configuration (`.aider.conf.yml`)**: For persistent and more complex configurations, users can define handlers and their configurations in the config file. Handlers can be configured with an arbitrarily nested YAML map under a `config` key.
    ```yaml
    controller-model: gpt-4o
    handlers:
      - name: file-adder
        config:
          reflections: 0
      - name: code-linter
        config:
          command: "flake8 {fname}"
      - name: test-runner
        config:
          command: "pytest"
    ```

The execution phase for a handler (e.g., pre, post) is not defined in the configuration but is an inherent property of the handler's implementation. A handler can be designed to run at one or more phases of the Aider workflow.

Command-line arguments will override settings from the configuration file.

#### Internal Architecture

Handlers are loaded dynamically to support extensibility.

1.  **Dynamic Discovery and Loading**: Handlers are not statically registered. Instead, they are discovered and loaded at runtime from the `aider/extensions/handlers/` directory. When a handler is specified by its name (e.g., via `--handlers file-adder`), Aider uses a convention-based approach to find and import the corresponding Python module. It then inspects the module to find a class that implements the handler logic.

2.  **Controller Initialization**: The `Controller.__init__` method:
    -   Checks if a `controller_model` is provided.
    -   If so, it processes the `handlers` configuration from the CLI and YAML file.
    -   For each requested handler, it dynamically loads and instantiates the handler class, passing in the `controller_model` and any handler-specific configuration from the `config` block.

3.  **Future Runtime Management**: This dynamic architecture is designed to support future commands for managing handlers within an interactive chat session:
    -   `/extension-load <handler-name>`: To dynamically load and activate a new handler.
    -   `/extension-remove <handler-name>`: To deactivate and unload an active handler.

### Handler Execution Flow

Each handler implementation declares which execution phases it supports by defining an `entrypoints` property, which is a list of strings (e.g., `["pre", "post"]`). At each phase of the Aider workflow, the controller iterates through all registered handlers and executes those that have registered for the current phase.

This design allows handlers to run at different stages to prepare context, act as tools for the main model, or review the main model's output. The initial implementation will support pre and post handlers, and we can categorize the potential execution points into three phases:

1.  **Pre (Before Main Model Request)**:
    -   Handlers in this phase run after the user has entered their prompt but before the request is sent to the main coding LLM.
    -   **Purpose**: To enrich the context provided to the main model.
    -   **Examples**:
        -   A linter that runs on the current files and adds the linting errors to the prompt.
        -   A handler that analyzes the user's request and suggests adding other relevant files to the chat.

2.  **In (During Main Model Request - Tool Use)**:
    -   Handlers in this phase act as tools that the main LLM can choose to call during its reasoning process. This requires a model that supports tool use (function calling).
    -   **Purpose**: To provide the main model with the ability to interact with the user's environment and gather information.
    -   **Examples**:
        -   `read_file`: Allows the LLM to read a file that wasn't initially added to the chat.
        -   `list_files`: Allows the LLM to explore the directory structure.
        -   `execute_bash_command`: Allows the LLM to run commands to understand the state of the system.

3.  **Post (After Main Model Response)**:
    -   Handlers in this phase run after the main LLM has generated a response (e.g., a code change).
    -   **Purpose**: To validate, refine, or supplement the main model's output.
    -   **Examples**:
        -   A code formatter that automatically formats the generated code.
        -   A test runner that executes tests against the proposed changes and reports back failures.
        -   A commit message generator that drafts a commit message based on the applied diff.

### Default Behavior

If a `controller_model` is provided but the user does not specify any handlers, no handlers will be activated by default. Handlers must be explicitly configured using the `--handlers` command-line argument or in the `.aider.conf.yml` configuration file.
