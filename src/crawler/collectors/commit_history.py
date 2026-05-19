from __future__ import annotations

from datetime import datetime
import logging

from crawler.client import GitHubClient
from crawler.models import CommitHistoryMetrics


logger = logging.getLogger(__name__)


def collect_commit_history(client: GitHubClient, repo_full_name: str) -> CommitHistoryMetrics:
    total_commits, first_commit, last_commit = client.get_commit_count_and_boundary_commits(repo_full_name)
    num_developers = client.count_visible_contributors(repo_full_name)
    first_commit_date = _commit_datetime(first_commit)
    last_commit_date = _commit_datetime(last_commit)

    logger.info(
        "Collected %s: commits=%s developers=%s first=%s last=%s",
        repo_full_name,
        total_commits,
        num_developers,
        _to_iso(first_commit_date),
        _to_iso(last_commit_date),
    )

    return CommitHistoryMetrics(
        repo_full_name=repo_full_name,
        num_developers=num_developers,
        total_commits=total_commits,
        first_commit_date=_to_iso(first_commit_date),
        last_commit_date=_to_iso(last_commit_date),
    )


def _commit_datetime(commit: dict[str, object] | None) -> datetime | None:
    if commit is None:
        return None
    commit_block = commit.get("commit")
    if not isinstance(commit_block, dict):
        return None
    author_block = commit_block.get("author")
    if not isinstance(author_block, dict):
        return None
    raw_date = author_block.get("date")
    if not isinstance(raw_date, str) or not raw_date:
        return None
    return datetime.fromisoformat(raw_date.replace("Z", "+00:00"))


def _to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
