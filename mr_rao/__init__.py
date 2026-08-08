"""Mr. Rao — offline document-to-Markdown converter.

Copyright (C) 2026 Antonio Andrea Rao

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.  Distributed WITHOUT ANY WARRANTY; see the licence for details.

You should have received a copy of the GNU Affero General Public License along
with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from config import APP_NAME, APP_VERSION

__all__ = ["APP_NAME", "APP_VERSION", "create_app"]


def create_app():
    """Application factory (lazy import to keep CLI light)."""
    from mr_rao.app_factory import create_app as _create

    return _create()
