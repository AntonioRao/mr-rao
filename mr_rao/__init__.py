"""Mr. Rao — offline document-to-Markdown converter."""
from config import APP_NAME, APP_VERSION

__all__ = ["APP_NAME", "APP_VERSION", "create_app"]


def create_app():
    """Application factory (lazy import to keep CLI light)."""
    from mr_rao.app_factory import create_app as _create

    return _create()
