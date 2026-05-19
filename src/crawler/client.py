from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from time import sleep
from urllib.parse import parse_qs, urlparse

import requests


logger = logging.getLogger(__name__)


class GitHubAPIError(RuntimeError):
    pass


@dataclass
class GitHubClient:
    token: str | None
    max_retries: int = 5
    retry_delay: int = 3
    rate_limit_buffer: int = 1

    def __post_init__(self) -> None:
        self._session = requests.Session()

    def close(self) -> None:
        self._session.close()

    def get_commit_count_and_boundary_commits(
        self,
        repo_full_name: str,
    ) -> tuple[int, dict[str, object] | None, dict[str, object] | None]:
        logger.info("Fetching commit count and latest commit for %s", repo_full_name)
        response, latest_payload = self._request_json_with_response(
            "GET",
            f"/repos/{repo_full_name}/commits",
            params={"per_page": 1, "page": 1},
        )
        total_commits = _last_page_number(response) or len(latest_payload)
        latest_commit = latest_payload[0] if latest_payload else None

        first_commit = latest_commit
        if total_commits > 1:
            logger.info("Fetching first commit for %s from page %s", repo_full_name, total_commits)
            first_payload = self._request_json(
                "GET",
                f"/repos/{repo_full_name}/commits",
                params={"per_page": 1, "page": total_commits},
            )
            first_commit = first_payload[0] if first_payload else None

        return total_commits, first_commit, latest_commit

    def count_visible_contributors(self, repo_full_name: str) -> int:
        logger.info("Fetching GitHub-visible contributor count for %s", repo_full_name)
        response, payload = self._request_json_with_response(
            "GET",
            f"/repos/{repo_full_name}/contributors",
            params={"per_page": 1, "page": 1},
        )
        return _last_page_number(response) or len(payload)

    def _request_json(self, method: str, path: str, params: dict[str, object] | None = None) -> list[dict[str, object]]:
        _, data = self._request_json_with_response(method, path, params=params)
        return data

    def _request_json_with_response(
        self,
        method: str,
        path: str,
        params: dict[str, object] | None = None,
    ) -> tuple[requests.Response, list[dict[str, object]]]:
        response = self._request(method, path, params=params)
        data = response.json()
        if not isinstance(data, list):
            raise GitHubAPIError(f"Expected list response from {path}")
        return response, [item for item in data if isinstance(item, dict)]

    def _request(self, method: str, path: str, params: dict[str, object] | None = None) -> requests.Response:
        url = f"https://api.github.com{path}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "primarily-civic-tech-crawler",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        for attempt in range(self.max_retries + 1):
            logger.debug("GitHub request %s %s params=%s attempt=%s", method, path, params, attempt + 1)
            response = self._session.request(method, url, params=params, headers=headers, timeout=60)

            if response.ok:
                remaining = response.headers.get("X-RateLimit-Remaining")
                reset_at = response.headers.get("X-RateLimit-Reset")
                logger.debug(
                    "GitHub response %s %s status=%s rate_limit_remaining=%s",
                    method,
                    path,
                    response.status_code,
                    remaining,
                )
                if remaining is not None and reset_at is not None:
                    try:
                        if int(remaining) <= self.rate_limit_buffer:
                            wait_seconds = max(0, int(reset_at) - int(time.time())) + 1
                            logger.warning(
                                "GitHub rate limit remaining=%s is at or below buffer=%s; sleeping %s seconds",
                                remaining,
                                self.rate_limit_buffer,
                                wait_seconds,
                            )
                            sleep(wait_seconds)
                    except ValueError:
                        logger.debug(
                            "Could not parse GitHub rate limit headers: remaining=%s reset=%s",
                            remaining,
                            reset_at,
                        )
                        pass
                return response

            if response.status_code in {403, 429, 500, 502, 503, 504} and attempt < self.max_retries:
                logger.warning(
                    "GitHub request failed with status=%s for %s; retrying in %s seconds (%s/%s)",
                    response.status_code,
                    path,
                    self.retry_delay,
                    attempt + 1,
                    self.max_retries,
                )
                sleep(self.retry_delay)
                continue

            raise GitHubAPIError(
                f"GitHub request failed ({response.status_code}) for {path}: {response.text.strip()}"
            )

        raise GitHubAPIError(f"GitHub request failed after retries for {path}")


def _last_page_number(response: requests.Response) -> int | None:
    last_link = response.links.get("last", {})
    url = last_link.get("url")
    if not url:
        return None

    page_values = parse_qs(urlparse(url).query).get("page")
    if not page_values:
        return None

    try:
        return int(page_values[0])
    except ValueError:
        return None
