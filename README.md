# primarily_civic_tech_crawler

GitHub commit-metrics crawler for the repositories listed in [config.yaml](config.yaml).

It collects these fields for each configured repository:

- `num_developers`, using GitHub's visible contributor count
- `total_commits`
- `first_commit_date`
- `last_commit_date`

## Requirements

- Python 3.13+
- `uv`
- A GitHub personal access token for private repositories or to avoid low unauthenticated API limits

## Setup

From the project root:

```bash
uv sync
```

That creates the local `.venv` and installs the dependencies from `pyproject.toml`.

## Configure repositories

Edit [config.yaml](config.yaml) and list the repositories you want to crawl:

```yaml
repositories:
	- DemocracyClub/UK-Polling-Stations
```

The config file also supports:

- `github.max_retries`
- `github.retry_delay`
- `github.rate_limit_buffer`
- `output.directory`

## Run

Use the `uv` environment to run the CLI:

```bash
uv run python src/main.py
```

Optional overrides:

```bash
uv run python src/main.py --config config.yaml
uv run python src/main.py --token "$GITHUB_TOKEN"
uv run python src/main.py --output-dir ./output
uv run python src/main.py --repos owner/repo1,owner/repo2
uv run python src/main.py --log-level DEBUG
uv run python src/main.py --refresh
```

By default, the CLI reuses existing repository metrics from `commit_metrics.json` in the output directory.
Use `--refresh` when you want to ignore that cache and crawl GitHub again.

If you prefer, you can also export the token first:

```bash
export GITHUB_TOKEN="your-token-here"
uv run python src/main.py
```

## Output

The crawler writes these files into the configured output directory:

- `commit_metrics.json`
- `commit_metrics.csv`

Each row or record includes the repository name plus the four commit-history metrics above.

## Notes

- `num_developers` is counted from GitHub's visible contributors API, matching the count shown in the repository sidebar more closely than raw commit author emails.
- The crawler does not fetch every commit page. It uses GitHub pagination metadata to count commits, fetches only the first and latest commit, and separately counts visible contributors.
- The CLI prints a one-line summary for each repository and the paths of the generated output files.
