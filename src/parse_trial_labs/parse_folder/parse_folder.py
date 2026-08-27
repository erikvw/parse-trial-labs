from __future__ import annotations

from .files_to_dataframe import FilesToDataFrame


def parse_folder(*args, **kwargs):
    return FilesToDataFrame(*args, **kwargs).dataframe
