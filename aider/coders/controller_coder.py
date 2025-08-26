#!/usr/bin/env python

import importlib.util
import os

from .controller_handler import (
    ControllerHandler,
    ImmutableContextHandler,
    MutableContextHandler,
)


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
        :param handlers: An optional list of handlers to use. If None,
                         handlers are loaded from the plugins/handlers directory.
        """
        self.main_coder = main_coder
        self.controller_model = controller_model
        if handlers:
            self.handlers = handlers
        else:
            self.handlers = self.load_handlers()

    def load_handlers(self):
        """
        Load controller handlers from the plugins/handlers directory.
        """
        handlers = []
        current_dir = os.path.dirname(os.path.abspath(__file__))
        handlers_dir = os.path.join(current_dir, "plugins", "handlers")

        if not os.path.isdir(handlers_dir):
            return handlers

        for filename in sorted(os.listdir(handlers_dir)):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                module_path = os.path.join(handlers_dir, filename)

                try:
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    for item in dir(module):
                        obj = getattr(module, item)
                        if (
                            isinstance(obj, type)
                            and issubclass(obj, ControllerHandler)
                            and obj
                            not in [
                                ControllerHandler,
                                MutableContextHandler,
                                ImmutableContextHandler,
                            ]
                        ):
                            handlers.append(obj(self.main_coder, self.controller_model))
                except Exception as e:
                    self.main_coder.io.tool_warning(
                        f"Failed to load handler from {filename}: {e}"
                    )
        return handlers

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
