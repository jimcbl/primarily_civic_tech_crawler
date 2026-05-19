from __future__ import annotations

import argparse
import logging

from crawler.client import GitHubClient
from crawler.collectors.commit_history import collect_commit_history
from crawler.config import load_config
from crawler.output import read_commit_metrics_json, write_commit_metrics_csv, write_commit_metrics_json


logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl commit metrics for GitHub repositories")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--token", default=None, help="GitHub token override")
    parser.add_argument("--output-dir", default=None, help="Override output directory")
    parser.add_argument("--repos", default=None, help="Comma-separated repository list override")
    parser.add_argument("--log-level", default="INFO", help="Logging level: DEBUG, INFO, WARNING, ERROR")
    parser.add_argument("--refresh", action="store_true", help="Ignore cached output and crawl all repositories")
    return parser.parse_args()


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), None)
    if not isinstance(level, int):
        raise ValueError(f"Invalid log level: {level_name}")
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)

    logger.info("Loading config from %s", args.config)
    repos_override = args.repos.split(",") if args.repos else None
    config = load_config(
        config_path=args.config,
        token_override=args.token,
        repos_override=repos_override,
        output_dir_override=args.output_dir,
    )
    logger.info(
        "Configured %s repositories; output_dir=%s; token=%s",
        len(config.repositories),
        config.output_dir,
        "yes" if config.github_token else "no",
    )

    cached_metrics = {} if args.refresh else read_commit_metrics_json(config.output_dir)
    if cached_metrics:
        logger.info("Loaded %s cached repository metrics", len(cached_metrics))
    elif args.refresh:
        logger.info("Ignoring cached metrics because --refresh was provided")

    metrics = []
    missing_repos = [repo for repo in config.repositories if repo not in cached_metrics]

    for repo in config.repositories:
        if repo in cached_metrics:
            logger.info("Using cached metrics for %s", repo)
            metrics.append(cached_metrics[repo])

    if missing_repos:
        client = GitHubClient(
            token=config.github_token,
            max_retries=config.max_retries,
            retry_delay=config.retry_delay,
            rate_limit_buffer=config.rate_limit_buffer,
        )

        try:
            for index, repo in enumerate(missing_repos, start=1):
                logger.info("Collecting %s (%s/%s uncached)", repo, index, len(missing_repos))
                metric = collect_commit_history(client, repo)
                cached_metrics[repo] = metric
        finally:
            client.close()

    metrics = [cached_metrics[repo] for repo in config.repositories]

    logger.info("Writing output files")
    json_path = write_commit_metrics_json(metrics, config.output_dir)
    csv_path = write_commit_metrics_csv(metrics, config.output_dir)

    for metric in metrics:
        print(
            f"{metric.repo_full_name}: developers={metric.num_developers}, "
            f"commits={metric.total_commits}, first={metric.first_commit_date}, last={metric.last_commit_date}"
        )

    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
