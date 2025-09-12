import json

from aider import models
from aider.coders.base_coder import Coder
from ..handler import MutableContextHandler
from .main_model_decider_prompts import MainModelDeciderPrompts
from aider.utils import format_messages
from aider.waiting import WaitingSpinner


class MainModelDeciderHandler(MutableContextHandler):
    """
    A handler that uses a model to decide which model is best
    suited to handle the user's request.
    """

    handler_name = "main_model_decider"
    entrypoints = ["pre"]
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

        fast_model_name = kwargs.get("fast_model")
        if fast_model_name:
            self.fast_model = models.Model(fast_model_name)
        else:
            self.fast_model = main_coder.main_model.weak_model

    def _clean_and_decode_json(self, content):
        """
        Cleans markdown fences from a string and decodes it as JSON.
        """
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        return json.loads(content)

    def _score_input(self, scores):
        """
        Scores input for model selection
        """
        score = 0

        if scores.get("precision", 3) < 4:
            score += 1
        if scores.get("vague_error", False):
            score += 1
        if scores.get("change_existing", False):
            score += 1

        return score

    def _map_score_to_model(self, score, model_map):
        pass

    def _decide_model(self, scores):
        """
        Decides which model to use based on the scores.
        """
        score = self._score_input(scores)

        model_map = {
            0: self.main_coder.main_model,
            1: self.fast_model,
        }

        return _map_score_to_model(score, model_map)

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
            spinner = None
            if self.main_coder.show_pretty():
                spinner = WaitingSpinner(
                    f"{self.handler_name}: Waiting for {self.handler_model.name}"
                )
                spinner.start()

            try:
                _, response = self.handler_model.send_completion(
                    handler_messages,
                    None,
                    stream=False,
                )
                if not response or not response.choices:
                    io.tool_warning("Decider model returned empty response.")
                    return False
            finally:
                if spinner:
                    spinner.stop()

            content = response.choices[0].message.content
            scores = self._clean_and_decode_json(content)
            io.tool_output(f"Decider scores: {scores}")

        except json.JSONDecodeError:
            io.tool_warning("Decider model did not return valid JSON.")
            return False
        except Exception as e:
            io.tool_error(f"Error with decider model: {e}")
            return False

        target_model = self._decide_model(scores)

        if not target_model:
            return False

        if target_model.name != self.main_coder.main_model.name:
            io.tool_output(f"Decider: Proposing switch to {target_model.name}")
            # Schedule the model switch, which will trigger the confirmation prompt in BaseAgent.
            # The actual coder switch will happen after the current message is processed.
            self.main_coder.agent.schedule_switch_coder(
                main_model=target_model,
                from_coder=self.main_coder,
                agent=self.main_coder.agent,
            )
            return True

        io.tool_output(f"Decider: Sticking with {self.main_coder.main_model.name}")
        return False
