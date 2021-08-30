# Copyright 2021 John Reese, Tim Hatch
# Licensed under the MIT license

import logging
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import partial
from multiprocessing import get_context
from pathlib import Path
from typing import List, Optional

from black import (
    decode_bytes,
    format_file_contents,
    Mode,
    NothingChanged,
    parse_pyproject_toml,
    find_pyproject_toml,
)
from moreorless.click import unified_diff
from trailrunner import walk_and_run
from usort.config import Config as UsortConfig
from usort.sorting import usort_string

LOG = logging.getLogger(__name__)

CONTEXT = get_context("spawn")
EXECUTOR = ProcessPoolExecutor


@dataclass
class Result:
    path: Path
    changed: bool = False
    written: bool = False
    diff: Optional[str] = None


def ufmt_string(
    path: Path,
    content: str,
    usort_config: UsortConfig,
    black_config: Optional[Mode] = None,
) -> str:
    content = usort_string(content, usort_config, path)

    try:
        content = format_file_contents(content, fast=False, mode=black_config or Mode())
    except NothingChanged:
        pass

    return content


def _make_black_config(path: Path) -> Mode:
    config_file = find_pyproject_toml((str(path),))
    if not config_file:
        return Mode()

    config = parse_pyproject_toml(config_file)

    # manually patch options that do not have a 1-to-1 match in Mode arguments
    config["target_versions"] = set(config.pop("target_version", []))
    config["string_normalization"] = (
        not config.pop("skip_string_normalization", False),
    )
    config["magic_trailing_comma"] = (
        not config.pop("skip_magic_trailing_comma", False),
    )

    names = {
        field.name
        for field in Mode.__dataclass_fields__.values()  # type: ignore[attr-defined]
    }
    config = {name: value for name, value in config.items() if name in names}

    return Mode(**config)


def ufmt_file(path: Path, dry_run: bool = False, diff: bool = False) -> Result:
    usort_config = UsortConfig.find(path)
    black_config = _make_black_config(path)

    LOG.debug(f"Checking {path}")

    with open(path, "rb") as buf:
        src_contents, encoding, newline = decode_bytes(buf.read())

    dst_contents = ufmt_string(path, src_contents, usort_config, black_config)

    result = Result(path)

    if src_contents != dst_contents:
        result.changed = True

        if diff:
            result.diff = unified_diff(src_contents, dst_contents, path.as_posix())

        if not dry_run:
            LOG.debug(f"Formatted {path}")
            with open(path, "w", encoding=encoding, newline=newline) as f:
                f.write(dst_contents)
            result.written = True

    return result


def ufmt_paths(
    paths: List[Path], dry_run: bool = False, diff: bool = False
) -> List[Result]:
    fn = partial(ufmt_file, dry_run=dry_run, diff=diff)
    results = list(walk_and_run(paths, fn).values())

    return results
