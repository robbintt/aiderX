#!/usr/bin/env python


from .controller_handler import (
    ControllerHandler,
    ImmutableContextHandler,
    MutableContextHandler,
)
from aider.plugins.handlers.file_adder_handler import FileAdderHandler

HANDLER_REGISTRY = {
    FileAdderHandler.handler_name: FileAdderHandler,
}


class Controller:
    """
    The Controller orchestrates the use of a controller model to analyze and
    potentially modify the chat context before it is sent to the main coder.

    It uses a series of handlers to perform specific tasks, such as adding
    files to the chat.
    """

    def __init__(self, main_coder, controller_model, handlers=None):
        """
        Initialize the Controller.

        :param main_coder: The main coder instance.
        :param controller_model: The model to use for controller tasks.
        :param handlers: An optional list of handlers to use, from user config.
                         If None, a default set of handlers will be used.
        """
        self.main_coder = main_coder
        self.controller_model = controller_model
        self.handlers = []

        if not self.controller_model:
            return

        if not handlers:
            # Default handlers if none are specified
            handlers = ["file-adder"]

        self._load_handlers(handlers)

    def _load_handlers(self, handlers_config):
        """
        Load controller handlers based on the provided configuration.
        """
        for handler_config in handlers_config:
            if isinstance(handler_config, str):
                handler_name = handler_config
                config = {}
            elif isinstance(handler_config, dict):
                handler_name = handler_config.get("name")
                config = handler_config
            else:
                self.main_coder.io.tool_warning(
                    f"Invalid handler configuration: {handler_config}"
                )
                continue

            if not handler_name:
                self.main_coder.io.tool_warning(
                    f"Handler configuration missing name: {handler_config}"
                )
                continue

            handler_class = HANDLER_REGISTRY.get(handler_name)
            if handler_class:
                try:
                    handler_instance = handler_class(
                        self.main_coder, self.controller_model, **config
                    )
                    self.handlers.append(handler_instance)
                except Exception as e:
                    self.main_coder.io.tool_warning(
                        f"Failed to instantiate handler {handler_name}: {e}"
                    )
            else:
                self.main_coder.io.tool_warning(f"Unknown handler: {handler_name}")

    def run(self, messages):
        """
        Execute the controller logic by running its handlers.

        This method iterates through its handlers, allowing each to process and
        potentially modify the chat context. If a handler modifies the
        context, the message history is updated for subsequent handlers.

        :param messages: The current list of messages in the chat.
        """
        current_messages = messages
        for handler in self.handlers:
            modified = handler.handle(current_messages)
            if modified:
                chunks = self.main_coder.format_messages()
                current_messages = chunks.all_messages()


ControllerCoder = Controller
