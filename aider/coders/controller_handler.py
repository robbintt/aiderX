from abc import ABC, abstractmethod


class ControllerHandler(ABC):
    """
    Base class for controller handlers.
    """

    @abstractmethod
    def handle(self, messages):
        """
        Handle the given messages.
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

    @abstractmethod
    def handle(self, messages):
        """
        Handle the messages.
        """
        pass
