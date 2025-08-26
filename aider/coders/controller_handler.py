from abc import ABC, abstractmethod


class ControllerHandler(ABC):
    """
    Base class for controller handlers.
    """

    @abstractmethod
    def handle(self, messages, main_coder):
        """
        Handle the given messages and coder.
        """
        pass


class MutableContextHandler(ControllerHandler):
    """
    A handler that can modify the chat context.
    """

    @abstractmethod
    def handle(self, messages, main_coder) -> bool:
        """
        Handle the messages and return True if context was modified.
        """
        pass


class ImmutableContextHandler(ControllerHandler):
    """
    A handler that can inspect the context but not modify it.
    """

    @abstractmethod
    def handle(self, messages, main_coder):
        """
        Handle the messages.
        """
        pass
