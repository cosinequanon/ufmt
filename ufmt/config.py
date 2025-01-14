# Copyright 2022 Amethyst Reese
# Licensed under the MIT license
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

import tomlkit
from trailrunner import project_root

LOG = logging.getLogger(__name__)


@dataclass
class UfmtConfig:
    project_root: Optional[Path] = None
    pyproject_path: Optional[Path] = None
    excludes: List[str] = field(default_factory=list)


def ufmt_config(path: Optional[Path] = None) -> UfmtConfig:
    path = path or Path.cwd()
    root = project_root(path)
    config_path = root / "pyproject.toml"
    if config_path.is_file():
        pyproject = tomlkit.loads(config_path.read_text())
        config = pyproject.get("tool", {}).get("ufmt", {})
        if not isinstance(config, dict):
            LOG.warning("%s: tool.ufmt is not a mapping, ignoring", config_path)
            config = {}

        config_excludes = config.pop("excludes", [])
        if isinstance(config_excludes, Sequence) and not isinstance(
            config_excludes, str
        ):
            excludes = [str(x) for x in config_excludes]
        else:
            raise ValueError(f"{config_path}: excludes must be a list of strings")

        if config:
            LOG.warning("%s: unknown values ignored: %r", config_path, sorted(config))

        return UfmtConfig(
            project_root=root,
            pyproject_path=config_path,
            excludes=excludes,
        )

    return UfmtConfig()
