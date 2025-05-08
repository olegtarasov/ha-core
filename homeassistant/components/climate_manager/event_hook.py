"""Event hook module."""


class EventHook(object):
    """Manages event handlers for triggering actions."""

    def __init__(self):
        """Initialize an empty list to store event handlers."""
        self.__handlers = []

    def __iadd__(self, handler):
        """Add a handler to the list of event handlers."""
        self.__handlers.append(handler)
        return self

    def __isub__(self, handler):
        """Remove a handler from the list of event handlers."""
        self.__handlers.remove(handler)
        return self

    def __call__(self, *args, **kwargs):
        """Trigger all registered handlers with the provided arguments."""
        for handler in self.__handlers:
            handler(*args, **kwargs)
