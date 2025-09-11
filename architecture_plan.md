# Aider Architecture Refactoring Plan

This document outlines a plan to refactor the Aider architecture to improve separation of concerns, making the system more modular and maintainable.

## Core Components and Their Roles

### 1. Agent: The Orchestrator

The `Agent` will be the central orchestrator of the chat loop. Its primary responsibilities will be:

-   **Main Loop**: Managing the primary loop of receiving user input, processing it, and generating a response.
-   **LLM Communication**: Centralizing all communication with LLMs. It will contain the core logic for `send_completion`, including retry mechanisms, error handling, and streaming.
-   **Model Management**: Managing different model configurations and selecting the appropriate model for various tasks (e.g., main chat vs. reflection).
-   **Lifecycle Management**: Managing the lifecycle of other components like the `SessionManager`, `PromptBuilder`, and `Coder`.
-   **RepoMap Lifecycle**: Managing the repository map, including when to refresh it.

### 2. SessionManager: The State Keeper

The `SessionManager` will be responsible for managing the state of the chat session. Its key roles will be:

-   **Message History**: Managing `cur_messages` and `done_messages`, including summarization logic.
-   **File Context**: Keeping track of `abs_fnames` (editable files) and `abs_read_only_fnames`. This centralizes the knowledge of what is "in the chat."

### 3. PromptBuilder: The Context Formatter

The `PromptBuilder` will be dedicated to constructing the prompts sent to the LLM. It will:

-   **Consume State**: Query the `SessionManager` for message history and file context.
-   **Tailor Prompts**: Use information from the active `Coder` to format prompts according to the required `edit_format`.
-   **Inject Context**: Incorporate context from the `RepoMap`.

### 4. Coder: The Edit Format Specialist

The `Coder`'s role will be significantly more focused. It will act as the implementation of a *strategy pattern* for handling different LLM response formats.

-   **Parsing LLM Responses**: Its primary responsibility will be to parse the raw string response from the LLM and translate it into a structured list of edits based on the `edit_format` (e.g., diff, udiff, whole file).
-   **Providing Configuration**: It will still hold model-specific configuration, like the `edit_format` name, which the `PromptBuilder` will use.
-   **Stateless Logic**: The `Coder` will become largely stateless, focusing on the logic of its specific edit format.

### 5. Handlers: The Action Executors

Handlers will execute specific actions based on the LLM's response or other triggers in the chat loop.

-   **`EditCommitHandler`**: This handler will take the structured edits parsed by the `Coder` and be responsible for applying them to the files and committing them to the repository.
-   **Other Handlers**: Handlers like `FileAdderHandler` and `McpHandler` will continue to perform their specialized tasks, but they will be updated to use the `Agent`'s centralized `send_completion` method for any LLM interactions.

## Evaluation

The proposed architecture is a solid plan for improving modularity and separation of concerns. The breakdown of responsibilities among the `Agent`, `SessionManager`, `PromptBuilder`, `Coder`, and `Handlers` is logical and clear.

To address the goal of minimizing changes to individual `Coder` subclasses and to ensure a smooth, incremental transition, the implementation order is crucial. The original list of priorities is good, but can be reordered to be more incremental. A step-by-step approach where new components are introduced and integrated before undertaking the largest changes to `BaseCoder` will reduce risk and make the process more manageable.

## Refactoring Priorities

The refactoring should be done incrementally to minimize disruption. Here is a proposed order of operations:

1.  **Implement `SessionManager` and Centralize State**: Create the `SessionManager` to handle chat state (`cur_messages`, `done_messages`) and file context (`abs_fnames`, `abs_read_only_fnames`). `BaseCoder` will be updated to delegate state management to an instance of `SessionManager`. This is a preparatory refactoring to isolate state.

2.  **Centralize LLM Communication in `Agent`**: Create the `Agent` and move the `send_completion` logic into it. `BaseCoder` will then call `agent.send_completion`. This isolates LLM communication.

3.  **Implement `PromptBuilder` and Centralize Prompt Logic**: Create the `PromptBuilder` and move prompt formatting logic like `format_messages` into it. `BaseCoder` will delegate prompt construction to the `PromptBuilder`.

4.  **Move Orchestration from `Coder` to `Agent`**: This is the core of the refactoring. The main loop and orchestration logic from `BaseCoder.run` and `BaseCoder.send_message` will be moved into the `Agent`. The `Agent` will become the central orchestrator, using the `PromptBuilder`, `SessionManager`, and `Coder` as needed.

5.  **Refactor `Coder` as a Stateless Parser**: With orchestration moved to the `Agent`, `BaseCoder` and its subclasses can be simplified. Their primary role will be to act as a stateless strategy for parsing LLM responses.

6.  **Update Handlers**: Finally, update all handlers to use the new centralized services provided by the `Agent` for any LLM interactions or state access.

This refactoring will result in a more robust and flexible architecture where each component has a clear and distinct responsibility.
