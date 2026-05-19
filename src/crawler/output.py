from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from crawler.models import CommitHistoryMetrics


CACHE_VERSION = 2
CACHE_METADATA_FILENAME = "commit_metrics_cache.json"


def read_commit_metrics_json(output_dir: str | Path) -> dict[str, CommitHistoryMetrics]:
    path = Path(output_dir)
    if not _is_current_cache(path):
        return {}

    output_path = path / "commit_metrics.json"
    if not output_path.exists():
        return {}

    with output_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, list):
        raise ValueError(f"Expected list in cached metrics file: {output_path}")

    metrics: dict[str, CommitHistoryMetrics] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        metric = _metric_from_mapping(item)
        metrics[metric.repo_full_name] = metric
    return metrics


def write_commit_metrics_json(metrics: list[CommitHistoryMetrics], output_dir: str | Path) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    output_path = path / "commit_metrics.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump([metric.__dict__ for metric in metrics], handle, indent=2, sort_keys=True)
        handle.write("\n")
    _write_cache_metadata(path)
    return output_path


def write_commit_metrics_csv(metrics: list[CommitHistoryMetrics], output_dir: str | Path) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    output_path = path / "commit_metrics.csv"
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "repo_full_name",
                "num_developers",
                "total_commits",
                "first_commit_date",
                "last_commit_date",
            ],
        )
        writer.writeheader()
        for metric in metrics:
            writer.writerow(metric.__dict__)
    return output_path


def _metric_from_mapping(item: dict[str, Any]) -> CommitHistoryMetrics:
    return CommitHistoryMetrics(
        repo_full_name=str(item["repo_full_name"]),
        num_developers=int(item["num_developers"]),
        total_commits=int(item["total_commits"]),
        first_commit_date=_optional_str(item.get("first_commit_date")),
        last_commit_date=_optional_str(item.get("last_commit_date")),
    )


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _is_current_cache(output_dir: Path) -> bool:
    metadata_path = output_dir / CACHE_METADATA_FILENAME
    if not metadata_path.exists():
        return False

    with metadata_path.open("r", encoding="utf-8") as handle:
        metadata = json.load(handle)
    if not isinstance(metadata, dict):
        return False
    return metadata.get("cache_version") == CACHE_VERSION


def _write_cache_metadata(output_dir: Path) -> None:
    metadata_path = output_dir / CACHE_METADATA_FILENAME
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "cache_version": CACHE_VERSION,
                "num_developers_source": "github_visible_contributors",
            },
            handle,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")
