from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommitHistoryMetrics:
    repo_full_name: str
    num_developers: int
    total_commits: int
    first_commit_date: str | None
    last_commit_date: str | None
