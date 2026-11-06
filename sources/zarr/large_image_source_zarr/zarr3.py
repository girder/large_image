"""
Helpers for zarr >= 3, which no longer includes a SQLite store or a function to
copy stores.
"""

from zarr.core.buffer import default_buffer_prototype
from zarr.core.sync import sync
from zarr_sqlite import SQLiteStore


class LegacySQLiteStore(SQLiteStore):
    """
    A zarr-sqlite store that can also read the files written by the
    SQLiteStore in zarr 2.  Those files only have a ``zarr`` table with the
    same key and value columns, but lack the metadata table and application
    id that zarr-sqlite requires.
    """

    def __init__(self, database, *, read_only=False, journal_mode='DELETE', **kwargs):
        # Don't leave written files in WAL mode; they are meant to be
        # distributed as a single file.
        super().__init__(database, read_only=read_only, journal_mode=journal_mode, **kwargs)

    async def _validate_schema(self):
        if self.read_only:
            rows = await self._conn.fetchall(
                'SELECT name FROM sqlite_master WHERE type = ? AND name = ?',
                ('table', 'zarr_sqlitestore_metadata'))
            if not rows:
                rows = await self._conn.fetchall('PRAGMA table_info(zarr)')
                if not rows:
                    msg = 'Not a zarr SQLite file'
                    raise ValueError(msg)
                return None
        return await super()._validate_schema()

    def with_read_only(self, read_only=False):
        return type(self)(self.database, read_only=read_only)


async def _copy_store(src, dst, excludes):
    prototype = default_buffer_prototype()
    async for key in src.list():
        if key not in excludes:
            await dst.set(key, await src.get(key, prototype=prototype))


def copy_store(src, dst, excludes=()):
    """
    Copy all keys from one zarr store to another.

    :param src: the source store.
    :param dst: the destination store.
    :param excludes: keys that should not be copied.
    """
    sync(_copy_store(src, dst, excludes))


__all__ = ['LegacySQLiteStore', 'copy_store']
