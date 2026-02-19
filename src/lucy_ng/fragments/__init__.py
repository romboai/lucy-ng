"""Fragment library module for lucy-ng.

Provides the storage foundation for the v5.0 Fragment Library:

- :class:`SSCRecord` — Pydantic model for a substructure-subspectrum correlation
- :class:`SSCMatch` — Pydantic model for a fragment search result
- :class:`FragmentDatabaseManager` — SQLite manager for ``lucy-ng-fragments.db``

Example usage::

    from lucy_ng.fragments import FragmentDatabaseManager, SSCRecord

    with FragmentDatabaseManager("data/reference/lucy-ng-fragments.db") as db:
        db.create_tables()
        count = db.get_ssc_count()
"""

from __future__ import annotations

from lucy_ng.fragments.db import FragmentDatabaseManager
from lucy_ng.fragments.models import SSCMatch, SSCRecord

__all__ = ["FragmentDatabaseManager", "SSCMatch", "SSCRecord"]
