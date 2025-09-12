import json

from aider import models
from aider.coders.base_coder import Coder
from ..handler import MutableContextHandler
from .main_model_decider_prompts import MainModelDeciderPrompts
from aider.utils import format_messages


class MainModelDeciderHandler(MutableContextHandler):
    """
    A handler that uses a model to decide which model is best
    suited to handle the user's request.
    """

    handler_name = "main_model_decider"
    entrypoints = ["decide"]
    gpt_prompts = MainModelDeciderPrompts()

    def __init__(self, main_coder, **kwargs):
        self.main_coder = main_coder

        if main_coder.main_model.weak_model:
            self.handler_model = main_coder.main_model.weak_model
        else:
            self.handler_model = main_coder.main_model

        model_name = kwargs.get("model")
        if model_name:
            self.handler_model = models.Model(model_name)

    def handle(self, messages) -> bool:
        """
        Analyzes the user's request and decides which model to use.
        """
        io = self.main_coder.io
        io.tool_output(f"{self.handler_name}: deciding which model to use...")

        # Formulate messages for the decider model
        handler_messages = [
            {"role": "system", "content": self.gpt_prompts.main_system},
            {"role": "user", "content": format_messages(messages)},
        ]

        try:
            _, response = self.handler_model.send_completion(
                handler_messages,
                None,
                stream=False,
            )
            if not response or not response.choices:
                io.tool_warning("Decider model returned empty response.")
                return False

            content = response.choices[0].message.content

            # Strip markdown fences if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            scores = json.loads(content)
            io.tool_output(f"Decider scores: {scores}")

        except json.JSONDecodeError:
            io.tool_warning("Decider model did not return valid JSON.")
            return False
        except Exception as e:
            io.tool_error(f"Error with decider model: {e}")
            return False

        # Simple matrix to select model
        use_strong_model = (
            scores.get("precision", 3) < 4
            or scores.get("vague_error", False)
            or not scores.get("change_existing", True)
        )

        strong_model = self.main_coder.main_model
        fast_model = self.main_coder.main_model.weak_model

        if not fast_model:
            return False

        target_model = strong_model if use_strong_model else fast_model

        if target_model.name != self.main_coder.main_model.name:
            io.tool_output(f"Decider: Switching to {target_model.name}")
            new_coder = Coder.create(
                from_coder=self.main_coder,
                main_model=target_model,
                agent=self.main_coder.agent,
            )
            self.main_coder.agent.coder = new_coder
            return True

        io.tool_output(f"Decider: Sticking with {self.main_coder.main_model.name}")
        return False
