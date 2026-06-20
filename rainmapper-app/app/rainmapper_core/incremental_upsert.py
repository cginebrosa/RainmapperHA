"""Utilities for preserving Rainmapper incremental CSV history.

The incremental CSV files are not append-only logs. A source can resend the
same station/day later with corrected values, so the update operation must
behave like an upsert keyed by station and local date. Fresh non-null values
win, while fresh NaN values keep older useful fields such as Meteocat
temperature and humidity.
"""

import pandas as pd


DEFAULT_INCREMENTAL_KEY = ['Codi Estació', 'Data Local']


def _validate_key_columns(df: pd.DataFrame, key_columns):
    """Fail fast if a dataframe cannot be matched by the incremental key."""
    missing_columns = [column for column in key_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f'Missing incremental key column(s): {", ".join(missing_columns)}')


def _collapse_duplicate_keys(df: pd.DataFrame, key_columns):
    """Reduce existing duplicate station/day rows before applying a fresh upsert."""
    if df.empty:
        return df.copy()

    _validate_key_columns(df, key_columns)

    # If duplicated keys already exist, keep one logical row per station/day.
    # Later rows win, but their NaN values are filled from previous non-null
    # values so partial source responses do not erase useful historical fields.
    collapsed = df.copy()
    value_columns = [column for column in collapsed.columns if column not in key_columns]
    if value_columns:
        collapsed[value_columns] = (
            collapsed.groupby(key_columns, sort=False, dropna=False)[value_columns]
            .ffill()
            .infer_objects(copy=False)
        )
    return collapsed.drop_duplicates(subset=key_columns, keep='last').reset_index(drop=True)


def upsert_incremental(current_df: pd.DataFrame, old_df: pd.DataFrame, key_columns=None):
    """Merge current source rows into historical rows without creating key duplicates.

    The returned dataframe contains at most one row per key. Values from
    current_df take precedence when they are not null; null current values keep
    the previous historical value if one exists.
    """
    key_columns = key_columns or DEFAULT_INCREMENTAL_KEY

    current = current_df.copy()
    old = old_df.copy()

    _validate_key_columns(current, key_columns)
    _validate_key_columns(old, key_columns)

    columns = list(old.columns)
    for column in current.columns:
        if column not in columns:
            columns.append(column)

    old = _collapse_duplicate_keys(old.reindex(columns=columns), key_columns)
    current = _collapse_duplicate_keys(current.reindex(columns=columns), key_columns)

    if old.empty:
        return current.reset_index(drop=True)
    if current.empty:
        return old.reset_index(drop=True)

    old_indexed = old.set_index(key_columns, drop=False)
    current_indexed = current.set_index(key_columns, drop=False)

    combined = old_indexed.copy()
    current_indexed = current_indexed.copy()

    # Source readers do not always produce identical pandas dtypes for the same
    # logical column. Cast only mismatched columns to object before update so
    # pandas does not warn or fail when a fresh value replaces an older one.
    for column in combined.columns.intersection(current_indexed.columns):
        if combined[column].dtype != current_indexed[column].dtype:
            combined[column] = combined[column].astype('object')
            current_indexed[column] = current_indexed[column].astype('object')

    # pandas.DataFrame.update overwrites with non-NaN values only. That gives
    # the desired incremental behavior: fresh source values win, while NaN in
    # the fresh response keeps the older useful value.
    combined.update(current_indexed)

    new_keys = current_indexed.index.difference(combined.index)
    if len(new_keys) > 0:
        combined = pd.concat([combined, current_indexed.loc[new_keys]], axis=0)

    return combined.reset_index(drop=True)
