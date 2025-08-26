from abc import ABC, abstractmethod


class ControllerHandler(ABC):
    """
    Base class for controller handlers.
    """

    @abstractmethod
    def handle(self, messages) -> bool:
        """
        Handle the given messages.
        Return True if context was modified, False otherwise.
        """
        pass


class MutableContextHandler(ControllerHandler):
    """
    A handler that can modify the chat context.
    """

    @abstractmethod
    def handle(self, messages) -> bool:
        """
        Handle the messages and return True if context was modified.
        """
        pass


class ImmutableContextHandler(ControllerHandler):
    """
    A handler that can inspect the context but not modify it.
    """

    def handle(self, messages) -> bool:
        """
        Handle the messages and return False, as context is not modified.
        """
        self._handle(messages)
        return False

    @abstractmethod
    def _handle(self, messages):
        """
        Process the messages.
        """
        pass
