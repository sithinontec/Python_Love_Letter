"""Love Letter — a digital implementation of the card game."""

__all__ = ["App"]


def __getattr__(name):
    if name == "App":
        from .app import App
        return App
    raise AttributeError(name)
