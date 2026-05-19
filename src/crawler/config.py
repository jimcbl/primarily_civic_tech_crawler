from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os

import yaml


@dataclass(frozen=True)
class AppConfig:
    github_token: str | None
    max_retries: int
    retry_delay: int
    rate_limit_buffer: int
    repositories: list[str]
    output_dir: Path


def load_config(
    config_path: str | Path = "config.yaml",
    token_override: str | None = None,
    repos_override: list[str] | None = None,
    output_dir_override: str | Path | None = None,
) -> AppConfig:
    path = Path(config_path)
    if not path.exists():
        raise ValueError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    github = _as_mapping(raw.get("github"), "github")
    output = _as_mapping(raw.get("output"), "output")

    repositories = repos_override if repos_override is not None else list(raw.get("repositories") or [])
    repositories = [repo.strip() for repo in repositories if repo and repo.strip()]
    if not repositories:
        raise ValueError("No repositories configured")

    github_token = token_override or os.getenv("GITHUB_TOKEN")
    output_dir_value = output_dir_override or output.get("directory", "./output")

    return AppConfig(
        github_token=github_token,
        max_retries=int(github.get("max_retries", 5)),
        retry_delay=int(github.get("retry_delay", 3)),
        rate_limit_buffer=int(github.get("rate_limit_buffer", 1)),
        repositories=repositories,
        output_dir=Path(output_dir_value),
    )


def _as_mapping(value: Any, section_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected {section_name} section to be a mapping")
    return value
