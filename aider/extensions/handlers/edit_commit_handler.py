from ..handler import MutableContextHandler


class EditCommitHandler(MutableContextHandler):
    """
    A handler to apply edits from the LLM and commit them.
    """

    entrypoints = ["llm_response"]

    def __init__(self, main_coder, **kwargs):
        self.main_coder = main_coder

    def handle(self, messages):
        """
        Apply edits and commit them.
        This is a core part of aider's workflow.
        """
        # This logic is extracted from base_coder.py
        edited = self.main_coder.apply_updates()

        if not edited:
            return False

        self.main_coder.aider_edited_files.update(edited)
        saved_message = self.main_coder.auto_commit(edited)

        if not saved_message and hasattr(
            self.main_coder.gpt_prompts, "files_content_gpt_edits_no_repo"
        ):
            saved_message = self.main_coder.gpt_prompts.files_content_gpt_edits_no_repo

        self.main_coder.move_back_cur_messages(saved_message)

        return True
