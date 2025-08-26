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
    gpt_prompts = ControllerPrompts()

    def __init__(self, main_coder, controller_model):
        self.main_coder = main_coder
        self.io = main_coder.io
        self.controller_model = controller_model
        self.num_reflections = 0

    def handle(self, messages, main_coder) -> bool:
        self.io.tool_output("▼ Controller Model Analysis")
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
            if self.main_coder.show_pretty():
                spinner = WaitingSpinner("Waiting for controller model")
                spinner.start()

            content = None
            try:
                _, response = self.controller_model.send_completion(
                    current_messages,
                    None,
                    stream=False,
                )

                if spinner:
                    spinner.stop()

                if response and response.choices:
                    content = response.choices[0].message.content
                else:
                    self.io.tool_warning("Controller model returned empty response.")

            except Exception as e:
                if spinner:
                    spinner.stop()
                self.io.tool_error(f"Error with controller model: {e}")
                return False

            if not content:
                return False

            self.io.tool_output(content)

            mentioned_rel_fnames = self.main_coder.get_file_mentions(content)
            new_mentions = mentioned_rel_fnames - self.main_coder.ignore_mentions

            reflected_message = None
            if new_mentions:
                added_fnames = []
                group = ConfirmGroup(new_mentions)
                for rel_fname in sorted(new_mentions):
                    if self.io.confirm_ask(
                        "Add file to the chat?", subject=rel_fname, group=group, allow_never=True
                    ):
                        self.main_coder.add_rel_fname(rel_fname)
                        added_fnames.append(rel_fname)
                    else:
                        self.main_coder.ignore_mentions.add(rel_fname)

                if added_fnames:
                    reflected_message = self.gpt_prompts.files_added
                    modified = True

            if not reflected_message:
                break

            if self.num_reflections >= self.main_coder.max_reflections:
                self.io.tool_warning(
                    f"Only {self.main_coder.max_reflections} reflections allowed, stopping."
                )
                break

            self.num_reflections += 1
            controller_messages.append(dict(role="assistant", content=content))
            controller_messages.append(dict(role="user", content=reflected_message))

            main_coder_messages = self.main_coder.format_messages().all_messages()
        return modified


class Controller:
    def __init__(self, main_coder, controller_model, handlers=None):
        self.main_coder = main_coder
        self.controller_model = controller_model
        if handlers:
            self.handlers = handlers
        else:
            self.handlers = [FileAdderHandler(main_coder, controller_model)]

    def run(self, messages):
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
