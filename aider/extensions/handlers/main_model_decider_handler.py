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

        smartest_model_name = kwargs.get("smartest_model")
        if smartest_model_name:
            self.smartest_model = models.Model(smartest_model_name)
        else:
            self.smartest_model = main_coder.main_model.weak_model

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
        # A higher score indicates an "easier" task, pushing towards a faster/weaker model.
        # Conversely, not incrementing for a "harder" characteristic keeps it with the smarter model.

        # High precision means easier to handle, add points for a faster model.
        if scores.get("precision", 3) >= 4:
            score += 1

        # Not a vague error means easier to handle, add points.
        if not scores.get("vague_error", False):
            score += 1

        # Single file change and simple bug fix is an easy task.
        if scores.get("single_file_change", False) and scores.get("simple_bug_fix", False):
            score += 1

        # Simple correction is an easy task.
        if scores.get("simple_correction", False):
            score += 1

        # Explicit speed preference means user is fine with a faster model.
        if scores.get("explicit_speed_preference", False):
            score += 1

        # If user expects to refine, a faster model might be okay.
        if scores.get("user_refinement_expected", False):
            score += 1

        # Low multi-file impact means easier.
        if scores.get("multi_file_impact", 3) <= 2:
            score += 1

        # Not high complexity algorithmic means easier.
        if not scores.get("high_complexity_algorithmic", False):
            score += 1

        return score

    def _map_score_to_model(self, score, model_map):
        """
        Maps a score to a model using a model_map.
        It finds the highest score in the map that is less than or equal to the given score.
        """
        # Find the best key to use from the model_map
        best_key = -1
        for key in model_map.keys():
            if key <= score and key > best_key:
                best_key = key

        if best_key != -1:
            return model_map[best_key]

        return None

    def _decide_model(self, scores):
        """
        Decides which model to use based on the scores.
        """
        score = self._score_input(scores)

        model_map = {
            0: self.smartest_model,  # Scores 0, 1, 2 default to smartest
            3: self.fast_model,      # Scores 3+ will use the fast model
        }

        return self._map_score_to_model(score, model_map)

    def handle(self, messages) -> bool:
        """
        Analyzes the user's request and decides which model to use.
        """
        io = self.main_coder.io
        original_user_message = messages[-1]["content"] # Capture original user message

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

        # Prepare a message explaining the model choice to the user
        model_decision_message = "Aider's Model Decider analyzed your request and determined:\n"
        model_decision_message += "  - Key characteristics identified: "
        characteristics = []
        if scores.get("precision", 3) >= 4: characteristics.append("High Precision Request")
        if not scores.get("vague_error", False): characteristics.append("Clear Error (if any)")
        if scores.get("single_file_change", False): characteristics.append("Single File Change Likely")
        if scores.get("simple_bug_fix", False): characteristics.append("Simple Bug Fix Likely")
        if scores.get("simple_correction", False): characteristics.append("Minor Correction/Typo")
        if scores.get("explicit_speed_preference", False): characteristics.append("Speed Preferred by User")
        if scores.get("user_refinement_expected", False): characteristics.append("User Expects to Refine")
        if scores.get("multi_file_impact", 3) <= 2: characteristics.append("Low Multi-File Impact")
        if not scores.get("high_complexity_algorithmic", False): characteristics.append("Non-Complex Algorithm")
        if not characteristics: characteristics.append("General/Complex Task")
        model_decision_message += ", ".join(characteristics) + "\n"
        model_decision_message += f"  - Recommended model for this task: {target_model.name}"
        io.tool_output(model_decision_message)

        # Ask the user if they want to revise their question
        if target_model.name != self.main_coder.main_model.name and io.confirm_ask(
            "Would you like to proceed with the selected model? (ctrl+c to go back to the the prompt)",
            default="y"
        ):
            # User wants to proceed or explicitly confirmed the model switch
            io.tool_output(f"Decider: Proposing switch to {target_model.name}")
            # Schedule the model switch, which will trigger the confirmation prompt in BaseAgent.
            # The actual coder switch will happen after the current message is processed.
            self.main_coder.agent.schedule_switch_coder(
                main_model=target_model,
                from_coder=self.main_coder,
                agent=self.main_coder.agent,
            )
            return True
        else:
            io.tool_output(f"Decider: Sticking with {self.main_coder.main_model.name}")
            return False
