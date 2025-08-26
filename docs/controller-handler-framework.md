### 1. The Controller Framework

The core `Controller` class will act as a simple orchestrator. It won't contain any specific logic like reflection or prompt assembly. Its sole responsibility is to manage and execute a sequence of "handlers."

*   **Initialization**: The `Controller` is initialized with a list of `ControllerHandler` instances.
*   **Execution Flow**: When invoked, it passes the main model's current message context to the first handler. If a handler modifies the context (e.g., by adding a file to the chat), the `Controller` will regenerate the message context to reflect that change before passing the *new* context to the next handler in the sequence.

### 2. The `ControllerHandler` Interfaces

We will define a clear contract for plugins with a base class and two specialized interfaces.

*   **`ControllerHandler` (Base Class)**: Defines a single method, `handle(messages, main_coder)`, which receives the full message context and a reference to the main coder instance. This gives the handler access to everything it needs to perform its function, including I/O and file system access.

*   **`ImmutableContextHandler`**: This type of handler is for analysis, logging, or providing feedback to the user. It can inspect the context but is not permitted to alter the chat state. Its `handle` method returns nothing.

*   **`MutableContextHandler`**: This handler is designed for actions that modify the chat state. Its `handle` method can add files, modify messages, or perform other stateful operations. It must return a boolean indicating whether it made a change. This signal tells the `Controller` framework that the context needs to be updated.

### 3. The `FileAdderHandler` Plugin

The existing file-suggestion logic will be refactored into our first plugin, the `FileAdderHandler`, which will be a `MutableContextHandler`.

*   **Self-Contained Logic**: This handler will be entirely responsible for its own operation. It is not limited to using an LLM; it could just as easily use programmatic tools like `ripgrep` to find relevant files.
*   **Example Implementation (using an LLM)**:
    1.  The `handle` method receives the current message context.
    2.  It constructs its own specific prompt and makes a call to a controller LLM to analyze the context and suggest files.
    3.  It parses the LLM's response.
    4.  It uses the `main_coder.io` instance to ask the user for confirmation.
    5.  Upon user approval, it calls `main_coder.add_rel_fname()` to modify the chat state.
    6.  Finally, it returns `True` to the `Controller`, signaling that the context has changed and needs to be regenerated.

This design decouples the control flow from the action logic, creating a flexible framework where complex behaviors can be composed by registering different handlers in sequence.
