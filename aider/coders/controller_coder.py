#!/usr/bin/env python

from .controller_handler import (
    ImmutableContextHandler,
    MutableContextHandler,
)
from .controller_prompts import ControllerPrompts
from ..io import ConfirmGroup
from ..utils import format_messages
from ..waiting import WaitingSpinner


class FileAdderHandler(MutableContextHandler):
    """
    A controller handler that uses a model to identify files mentioned in the
    user's request and adds them to the chat context if confirmed by the user.
    """

    gpt_prompts = ControllerPrompts()

    def __init__(self, controller_model):
        """
        Initialize the FileAdderHandler with a controller model.

        :param controller_model: The model to use for analyzing the request.
        """
        self.controller_model = controller_model
        self.num_reflections = 0

    def handle(self, messages, main_coder) -> bool:
        """
        Analyzes the user's request to find mentioned files and adds them to the chat.

        This method sends the current chat context to the controller model, which
        is prompted to identify any files that should be added to the chat for the
        main coder to have enough context. It then asks the user for confirmation
        before adding each file.

        The process may involve multiple "reflections" where the model re-evaluates
        the context after new files have been added.

        :param messages: The current list of messages in the chat.
        :param main_coder: The main coder instance, used to add files and access IO.
        :return: True if files were added to the context, False otherwise.
        """
        io = main_coder.io
        io.tool_output("▼ Controller Model Analysis")
        self.num_reflections = 0

        fence_name = "AIDER_MESSAGES"
        fence_start = f"<<<<<<< {fence_name}"
        fence_end = f">>>>>>> {fence_name}"

        system_prompt = self.gpt_prompts.main_system.format(
            fence_start=fence_start, fence_end=fence_end
        )

        main_coder_messages = messages
        controller_messages = []

        modified = False

        while True:
            formatted_messages = format_messages(main_coder_messages)
            fenced_messages = f"{fence_start}\n{formatted_messages}\n{fence_end}"

            if not controller_messages:
                controller_messages = [
                    dict(role="system", content=system_prompt),
                    dict(role="user", content=fenced_messages),
                ]
            else:
                # This is a reflection. Update the fenced message.
                # The second message is the user message with fenced content.
                controller_messages[1]["content"] = fenced_messages

            current_messages = list(controller_messages)
            final_reminder = self.gpt_prompts.final_reminder
            reminder_mode = getattr(self.controller_model, "reminder", "sys")
            if reminder_mode == "sys":
                current_messages.append(dict(role="system", content=final_reminder))
            elif reminder_mode == "user" and current_messages[-1]["role"] == "user":
                current_messages[-1]["content"] += "\n\n" + final_reminder

            spinner = None
            if main_coder.show_pretty():
                spinner = WaitingSpinner("Waiting for controller model")
                spinner.start()

            content = None
            try:
                _, response = self.controller_model.send_completion(
                    current_messages,
                    None,
                    stream=False,
                )

                if response and response.choices:
                    content = response.choices[0].message.content
                else:
                    io.tool_warning("Controller model returned empty response.")

            except KeyboardInterrupt:
                raise
            except Exception as e:
                io.tool_error(f"Error with controller model: {e}")
                return False
            finally:
                if spinner:
                    spinner.stop()

            if not content:
                return False

            io.tool_output(content)

            mentioned_rel_fnames = main_coder.get_file_mentions(content)
            new_mentions = mentioned_rel_fnames - main_coder.ignore_mentions

            reflected_message = None
            if new_mentions:
                added_fnames = []
                group = ConfirmGroup(new_mentions)
                for rel_fname in sorted(new_mentions):
                    if io.confirm_ask(
                        "Add file to the chat?", subject=rel_fname, group=group, allow_never=True
                    ):
                        main_coder.add_rel_fname(rel_fname)
                        added_fnames.append(rel_fname)
                    else:
                        main_coder.ignore_mentions.add(rel_fname)

                if added_fnames:
                    reflected_message = self.gpt_prompts.files_added
                    modified = True

            if not reflected_message:
                break

            if self.num_reflections >= main_coder.max_reflections:
                io.tool_warning(
                    f"Only {main_coder.max_reflections} reflections allowed, stopping."
                )
                break

            self.num_reflections += 1
            controller_messages.append(dict(role="assistant", content=content))
            controller_messages.append(dict(role="user", content=reflected_message))

            main_coder_messages = main_coder.format_messages().all_messages()
        return modified


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
                         a default FileAdderHandler is created.
        """
        self.main_coder = main_coder
        self.controller_model = controller_model
        if handlers:
            self.handlers = handlers
        else:
            self.handlers = [FileAdderHandler(controller_model)]

    def run(self, messages):
        """
        Execute the controller logic by running its handlers.

        This method iterates through its handlers, allowing each to process and
        potentially modify the chat context. If a mutable handler modifies the
        context, the message history is updated for subsequent handlers.

        :param messages: The current list of messages in the chat.
        """
        current_messages = messages
        for handler in self.handlers:
            if isinstance(handler, MutableContextHandler):
                modified = handler.handle(current_messages, self.main_coder)
                if modified:
                    chunks = self.main_coder.format_messages()
                    current_messages = chunks.all_messages()
            elif isinstance(handler, ImmutableContextHandler):
                handler.handle(current_messages, self.main_coder)


ControllerCoder = Controller
