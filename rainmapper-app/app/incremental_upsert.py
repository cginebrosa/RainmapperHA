"""Compatibility wrapper for the shared incremental upsert implementation."""

from rainmapper_core.incremental_upsert import DEFAULT_INCREMENTAL_KEY, upsert_incremental


__all__ = ['DEFAULT_INCREMENTAL_KEY', 'upsert_incremental']
