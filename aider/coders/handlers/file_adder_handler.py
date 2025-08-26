from ..controller_handler import MutableContextHandler


class FileAdderHandler(MutableContextHandler):
    """
    A handler that adds files to the chat.
    This is a placeholder implementation.
    """

    handler_name = "file-adder"

    def __init__(self, main_coder, controller_model, **kwargs):
        self.main_coder = main_coder
        self.controller_model = controller_model
        # kwargs could contain handler-specific config

    def handle(self, messages):
        # Placeholder implementation
        # In a real implementation, this would call the controller model
        # to determine if any files should be added.
        self.main_coder.io.tool_output(f"Controller: Running {self.handler_name}")
        return False  # did not modify context
