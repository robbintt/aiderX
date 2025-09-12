import hashlib
import json
import os

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

        # Load model manifests
        manifest_path = os.path.join(
            os.path.dirname(__file__), "main_model_decider_manifest.json"
        )
        try:
            with open(manifest_path, "r") as f:
                self.model_manifests = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.main_coder.io.tool_error(f"Error loading model manifest: {e}")
            self.model_manifests = []

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

    def _decide_model(self, scores):
        """
        Decides which model to use based on the request characteristics and model manifests.
        Uses a filter and rank algorithm.
        """
        # Step 1: Filtering
        eligible_models = []
        for manifest in self.model_manifests:
            # Hard rule: filter out models with insufficient intelligence for demanding tasks
            required_intelligence_for_alg = 7
            required_intelligence_for_scope = 6 # Slightly lower for large scope/refactoring

            if scores.get("high_complexity_algorithmic"):
                if manifest.get("intelligence", 0) < required_intelligence_for_alg:
                    continue
                if "algorithmic_thinking" not in manifest.get("strengths", []):
                    continue

            if scores.get("scope_of_change", 1) >= 4: # Large scope implies a need for intelligence
                if manifest.get("intelligence", 0) < required_intelligence_for_scope:
                    continue
                if "refactoring" not in manifest.get("strengths", []):
                    # If it's a large scope change and not a refactoring model, filter it
                    if not scores.get("high_complexity_algorithmic"): # unless it's an algorithmic task
                        continue

            # Hard rule: filter out models not suited for high multi-file impact
            if scores.get("multi_file_impact", 1) >= 4 and "multi_file" not in manifest.get(
                "strengths", []
            ):
                continue

            # Context window check could be added here if we had token count of conversation

            eligible_models.append(manifest)

        if not eligible_models:
            return None  # No models are suitable

        # Step 2: Ranking
        ranked_models = []
        for model_manifest in eligible_models:
            score = 0

            # Intelligence Match: Higher intelligence is always better
            if scores.get("high_complexity_algorithmic"):
                score += model_manifest.get("intelligence", 0) * 3  # Stronger boost for algorithmic
            elif scores.get("scope_of_change", 1) >= 3: # Boost for general complex tasks
                 score += model_manifest.get("intelligence", 0) * 1.5
            else:
                score += model_manifest.get("intelligence", 0) * 1 # Base intelligence contribution

            # Speed Preference
            if scores.get("explicit_speed_preference"):
                score += model_manifest.get("speed", 0) * 2 # Increased multiplier for explicit speed
            else:
                score += model_manifest.get("speed", 0) * 0.5 # Reduced impact of speed when not explicitly preferred

            # Simple Correction preference
            if scores.get("simple_correction") and "simple_correction" in model_manifest.get("strengths", []):
                score += 5 # Strong bonus for simple corrections

            # Bug Fix Preference
            if scores.get("simple_bug_fix") and "bug_fix" in model_manifest.get("strengths", []):
                score += 4 # Increased bonus for simple bug fixes

            # Multi-file impact bonus for moderate to high changes
            if scores.get("multi_file_impact", 1) >= 2 and "multi_file" in model_manifest.get("strengths", []):
                score += scores.get("multi_file_impact", 1) * 1.5 # Scales with impact

            # Scope Match (Refactoring)
            if scores.get("scope_of_change", 1) >= 3 and "refactoring" in model_manifest.get(
                "strengths", []
            ):
                score += scores.get("scope_of_change", 1) * 2 # Scales with scope intensity

            # Cost-Effectiveness
            # Current cost_rating is 0 for all, so this gives a base +10 to all
            score += 10 - model_manifest.get("cost_rating", 10)

            # Penalties
            # Stronger penalty for high unchecked_file_risk if model is not strong in multi_file
            if (
                scores.get("unchecked_file_risk", 1) >= 3
                and "multi_file" not in model_manifest.get("strengths", [])
            ):
                score -= scores.get("unchecked_file_risk", 1) * 3 # Increased penalty

            ranked_models.append({"name": model_manifest["name"], "score": score})

        if not ranked_models:
            return None

        # Step 3: Selection
        best_model = max(ranked_models, key=lambda x: x["score"])
        return models.Model(best_model["name"])

    def handle(self, messages) -> bool:
        """
        Analyzes the user's request and decides which model to use.
        """
        # Find last user message
        last_user_message = None
        for message in reversed(messages):
            if message.get("role") == "user":
                last_user_message = message.get("content")
                break

        if not last_user_message:
            return False  # No user message, nothing to do

        current_user_message_hash = hashlib.sha256(last_user_message.encode("utf-8")).hexdigest()

        if (
            getattr(self.main_coder.agent, "ran_main_model_decider_for_message_hash", None)
            == current_user_message_hash
        ):
            self.main_coder.io.tool_output(
                f"{self.handler_name}: already ran for this message, skipping."
            )
            return False

        self.main_coder.agent.ran_main_model_decider_for_message_hash = current_user_message_hash

        io = self.main_coder.io
        original_user_message = messages[-1]["content"]  # Capture original user message

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
        if scores.get("high_complexity_algorithmic"):
            characteristics.append("High Algorithmic Complexity")
        if scores.get("multi_file_impact", 1) > 3:
            characteristics.append("High Multi-File Impact")
        if scores.get("explicit_speed_preference"):
            characteristics.append("Speed Preferred by User")
        if scores.get("scope_of_change", 1) > 3:
            characteristics.append("Large Scope of Change (Refactoring)")
        if scores.get("unchecked_file_risk", 1) > 3:
            characteristics.append("Risk of Affecting Unseen Files")
        if not characteristics:
            characteristics.append("General/Simple Task")

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
