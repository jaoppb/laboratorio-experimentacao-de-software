"""End-to-end async pipeline orchestrator for Lab03 DORA metrics mining.

Orchestrates candidate selection, CI validation, release collection,
commit comparisons, workflow run extractions, DORA metric computations,
and hybrid Parquet + CSV exports with Token Rotation and concurrent workers.
"""

from __future__ import annotations

import asyncio
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from metricas.dora import (
    calculate_deployment_frequency,
    evaluate_repository_dora,
)
from metricas.lead_time import calculate_lead_time
from metricas.schemas import _parse_datetime
from metricas.stability import (
    calculate_cfr_a,
    calculate_recovery_time,
)
from pipeline.commits import collect_release_commits
from pipeline.funnel import FunnelTracker
from pipeline.http_client import GitHubClient
from pipeline.metadata import fetch_repository_metadata
from pipeline.releases import fetch_releases, filter_window
from pipeline.repo_selector import iter_candidates_by_stars
from pipeline.workflow_runs import collect_workflow_runs, save_runs_to_parquet

logger = logging.getLogger(__name__)

SCHEMA_REPOSITORIOS = pa.schema(
    [
        ("owner", pa.string()),
        ("name", pa.string()),
        ("full_name", pa.string()),
        ("stars", pa.int64()),
        ("language", pa.string()),
        ("default_branch", pa.string()),
        ("created_at", pa.string()),
        ("contributors_count", pa.int64()),
        ("releases_count_window", pa.int64()),
        ("total_releases", pa.int64()),
        ("workflow_runs_count_window", pa.int64()),
        ("total_workflow_runs", pa.int64()),
        ("deployment_frequency", pa.float64()),
        ("deployment_tier", pa.string()),
        ("lead_time_a_hours", pa.float64()),
        ("lead_time_b_hours", pa.float64()),
        ("lead_time_tier", pa.string()),
        ("cfr_a", pa.float64()),
        ("cfr_tier", pa.string()),
        ("recovery_hours", pa.float64()),
        ("recovery_tier", pa.string()),
        ("censored_episodes_ratio", pa.float64()),
        ("overall_dora_score", pa.int64()),
        ("overall_dora_tier", pa.string()),
    ]
)


def save_repositories_dataset(
    records: list[dict[str, Any]],
    parquet_path: str | Path,
    csv_path: str | Path | None = None,
) -> None:
    """Save repository records to Parquet and optionally export to CSV atomically."""
    p_path = Path(parquet_path)
    p_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_parquet = p_path.with_suffix(".parquet.tmp")

    arrays = []
    for field in SCHEMA_REPOSITORIOS:
        name = field.name
        vals = [r.get(name) for r in records]
        arrays.append(pa.array(vals, type=field.type))

    table = pa.Table.from_arrays(arrays, schema=SCHEMA_REPOSITORIOS)
    pq.write_table(table, tmp_parquet, compression="snappy")
    tmp_parquet.replace(p_path)

    if csv_path:
        c_path = Path(csv_path)
        c_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_csv = c_path.with_suffix(".csv.tmp")
        fieldnames = [field.name for field in SCHEMA_REPOSITORIOS]
        with open(tmp_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in records:
                writer.writerow(r)
        tmp_csv.replace(c_path)


def load_repositories_dataset(parquet_path: str | Path) -> list[dict[str, Any]]:
    """Load existing repository dataset records from a Parquet file."""
    p_path = Path(parquet_path)
    if not p_path.is_file():
        return []

    try:
        table = pq.read_table(p_path)
        pydict = table.to_pydict()
        if not pydict or "full_name" not in pydict:
            return []

        total = len(pydict["full_name"])
        records: list[dict[str, Any]] = []
        fieldnames = [f.name for f in SCHEMA_REPOSITORIOS]
        for i in range(total):
            rec = {name: pydict[name][i] for name in fieldnames}
            records.append(rec)
        return records
    except Exception as exc:
        logger.warning("Could not read existing dataset %s: %s", p_path, exc)
        return []


def export_funnel_summary(
    funnel_path: str | Path,
    total_evaluated: int,
    discarded_no_actions: int,
    discarded_low_releases: int,
    discarded_low_runs: int,
    accepted_count: int,
    min_releases: int = 5,
    min_workflow_runs: int = 50,
) -> Path:
    """Construct and export selection funnel CSV adhering to Table T4 specifications."""
    funnel = FunnelTracker()
    remaining = total_evaluated
    funnel.record_stage(
        etapa="Busca inicial por estrelas (Search API)",
        quantidade_restante=remaining,
        descartados=0,
        motivo_descarte="-",
    )
    remaining = max(0, remaining - discarded_no_actions)
    funnel.record_stage(
        etapa="Filtro de uso de CI/CD (GitHub Actions)",
        quantidade_restante=remaining,
        descartados=discarded_no_actions,
        motivo_descarte="total_count de workflows == 0 ou erro de acesso",
    )
    remaining = max(0, remaining - discarded_low_releases)
    funnel.record_stage(
        etapa=f"Filtro de releases na janela (>= {min_releases})",
        quantidade_restante=remaining,
        descartados=discarded_low_releases,
        motivo_descarte=f"Menos de {min_releases} releases publicadas na janela",
    )
    remaining = max(0, remaining - discarded_low_runs)
    funnel.record_stage(
        etapa=f"Filtro de workflow runs na janela (>= {min_workflow_runs})",
        quantidade_restante=remaining,
        descartados=discarded_low_runs,
        motivo_descarte=f"Menos de {min_workflow_runs} runs válidos no default branch",
    )
    funnel.record_stage(
        etapa="Amostra final selecionada",
        quantidade_restante=accepted_count,
        descartados=0,
        motivo_descarte="-",
    )
    return funnel.export_csv(funnel_path)


class PipelineOrchestrator:
    """Executes the Lab03 end-to-end data mining and DORA metrics pipeline asynchronously."""

    def __init__(
        self,
        config: dict[str, Any],
        client: GitHubClient | None = None,
        limit: int | None = None,
        num_workers: int = 4,
    ) -> None:
        self.config = config
        self.client = client
        self.num_workers = num_workers

        janela = config.get("janela", {})
        amostra = config.get("amostra", {})
        dirs = config.get("diretorios", {})
        busca = config.get("busca", {})

        self.window_start: datetime = _parse_datetime(
            janela.get("inicio", "2025-10-01")
        ) or datetime(2025, 10, 1)
        self.window_end: datetime = _parse_datetime(
            janela.get("fim", "2026-09-30")
        ) or datetime(2026, 9, 30)

        config_limit = amostra.get("tamanho_final", 100)
        self.target_size: int = limit if limit is not None else config_limit
        self.min_releases: int = amostra.get("min_releases", 5)
        self.min_workflow_runs: int = amostra.get("min_workflow_runs", 50)

        self.star_ranges: list[str] = busca.get(
            "star_ranges",
            [">10000", "5001..10000", "2501..5000", "1501..2500", "1000..1500"],
        )

        self.dados_dir = Path(dirs.get("dados", "dados"))
        self.runs_dir = self.dados_dir / "runs"
        self.cache_dir = Path(dirs.get("cache", "cache"))

        self.dataset_parquet = self.dados_dir / "repositorios.parquet"
        self.dataset_csv = self.dados_dir / "repositorios.csv"
        self.funil_csv = self.dados_dir / "funil.csv"
        self.state_file = self.dados_dir / ".pipeline_state.json"

        self._lock = asyncio.Lock()

    def _ensure_directories(self) -> None:
        self.dados_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> dict[str, Any]:
        if self.state_file.is_file():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Could not read state file %s: %s", self.state_file, e)
        return {
            "total_evaluated": 0,
            "discarded_no_actions": 0,
            "discarded_low_releases": 0,
            "discarded_low_runs": 0,
            "evaluated_names": [],
        }

    def _save_state(self, state: dict[str, Any]) -> None:
        tmp_state = self.state_file.with_suffix(".json.tmp")
        with open(tmp_state, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        tmp_state.replace(self.state_file)

    async def evaluate_candidate(
        self,
        client: GitHubClient,
        candidate: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Evaluate a single candidate repository through the filtering stages asynchronously."""
        full_name = candidate.get("full_name", "")
        if "/" not in full_name:
            return None, "invalid_name"
        owner, repo = full_name.split("/", 1)

        # Stage 1: Check Actions active
        try:
            wf_resp = await client.get(f"/repos/{owner}/{repo}/actions/workflows")
            wf_data = wf_resp.json()
            total_workflows = wf_data.get("total_count", 0)
            if total_workflows == 0:
                logger.debug("Discarding %s: no active workflows", full_name)
                return None, "no_actions"
        except Exception as exc:
            logger.warning("Error querying workflows for %s: %s", full_name, exc)
            return None, "no_actions"

        # Stage 2: Fetch and filter releases in observation window
        try:
            releases = await fetch_releases(
                client=client,
                owner=owner,
                repo=repo,
                window_start=self.window_start,
            )
            window_releases = filter_window(
                releases=releases,
                window_start=self.window_start,
                window_end=self.window_end,
            )
            if window_releases.count < self.min_releases:
                logger.debug(
                    "Discarding %s: %d releases in window (expected >= %d)",
                    full_name,
                    window_releases.count,
                    self.min_releases,
                )
                return None, "low_releases"
        except Exception as exc:
            logger.warning("Error fetching releases for %s: %s", full_name, exc)
            return None, "low_releases"

        # Fetch metadata for default branch and repo attributes
        try:
            meta = await fetch_repository_metadata(
                client=client,
                owner=owner,
                repo=repo,
                cached_info=candidate,
            )
            default_branch = meta.default_branch or "main"
        except Exception as exc:
            logger.warning("Error fetching metadata for %s: %s", full_name, exc)
            return None, "metadata_error"

        # Stage 3: Collect workflow runs on default branch (parallel monthly queries)
        try:
            runs_result = await collect_workflow_runs(
                owner=owner,
                repo=repo,
                client=client,
                start_date=self.window_start,
                end_date=self.window_end,
                branch=default_branch,
                save_to_parquet=False,
            )
            if runs_result.valid_runs_count < self.min_workflow_runs:
                logger.debug(
                    "Discarding %s: %d valid runs in window (expected >= %d)",
                    full_name,
                    runs_result.valid_runs_count,
                    self.min_workflow_runs,
                )
                return None, "low_runs"
        except Exception as exc:
            logger.warning("Error fetching runs for %s: %s", full_name, exc)
            return None, "low_runs"

        # Candidate passed all criteria! Save runs to Parquet
        runs_path = self.runs_dir / f"{owner}__{repo}.parquet"
        save_runs_to_parquet(
            runs_result.runs, owner=owner, repo=repo, output_path=runs_path
        )

        # Collect commits between releases in parallel
        try:
            release_commits = await collect_release_commits(
                client=client,
                owner=owner,
                repo=repo,
                window=window_releases,
            )
            lead_time_result = calculate_lead_time(
                [(rc.release, rc.commits_or_none) for rc in release_commits]
            )
        except Exception as exc:
            logger.warning("Error calculating lead time for %s: %s", full_name, exc)
            lead_time_result = calculate_lead_time([])

        # Calculate DORA Metrics
        dep_freq = calculate_deployment_frequency(
            releases=releases,
            window_weeks=52.1,
            start_date=self.window_start,
            end_date=self.window_end,
        )
        cfr_a = calculate_cfr_a(runs_result.runs)
        recovery_result = calculate_recovery_time(runs_result.runs)

        lead_time_a = lead_time_result.median_a_hours
        lead_time_b = lead_time_result.median_b_hours
        lead_time_days = (lead_time_a / 24.0) if lead_time_a is not None else None

        dora_eval = evaluate_repository_dora(
            deployment_frequency=dep_freq,
            lead_time_days=lead_time_days,
            cfr=cfr_a,
            recovery_hours=recovery_result.median_hours,
        )

        record = {
            "owner": owner,
            "name": repo,
            "full_name": full_name,
            "stars": meta.stars,
            "language": meta.language,
            "default_branch": default_branch,
            "created_at": (
                meta.created_at.isoformat()
                if hasattr(meta.created_at, "isoformat")
                else str(meta.created_at)
                if meta.created_at
                else None
            ),
            "contributors_count": meta.contributors_count,
            "releases_count_window": window_releases.count,
            "total_releases": len(releases),
            "workflow_runs_count_window": runs_result.valid_runs_count,
            "total_workflow_runs": runs_result.total_runs,
            "deployment_frequency": dep_freq,
            "deployment_tier": dora_eval.deployment_tier.value,
            "lead_time_a_hours": lead_time_a,
            "lead_time_b_hours": lead_time_b,
            "lead_time_tier": dora_eval.lead_time_tier.value,
            "cfr_a": cfr_a,
            "cfr_tier": dora_eval.cfr_tier.value,
            "recovery_hours": recovery_result.median_hours,
            "recovery_tier": dora_eval.recovery_tier.value,
            "censored_episodes_ratio": recovery_result.censored_ratio,
            "overall_dora_score": dora_eval.overall_score,
            "overall_dora_tier": dora_eval.overall_tier.value,
        }

        return record, None

    async def run_async(self) -> dict[str, Any]:
        """Execute the asynchronous pipeline with concurrent candidate workers."""
        self._ensure_directories()

        owns_client = False
        client = self.client
        if client is None:
            client = GitHubClient(cache_path=self.cache_dir / "http_cache.sqlite")
            owns_client = True

        try:
            accepted_records = load_repositories_dataset(self.dataset_parquet)
            accepted_names = {r["full_name"] for r in accepted_records}

            state = self._load_state()
            evaluated_names = set(state.get("evaluated_names", []))
            evaluated_names.update(accepted_names)

            stats = {
                "total_evaluated": state.get("total_evaluated", len(evaluated_names)),
                "discarded_no_actions": state.get("discarded_no_actions", 0),
                "discarded_low_releases": state.get("discarded_low_releases", 0),
                "discarded_low_runs": state.get("discarded_low_runs", 0),
            }

            logger.info(
                "Starting async pipeline: target %d repos (currently %d accepted)",
                self.target_size,
                len(accepted_records),
            )

            if len(accepted_records) >= self.target_size:
                logger.info("Target size %d already satisfied.", self.target_size)
                save_repositories_dataset(
                    records=accepted_records[: self.target_size],
                    parquet_path=self.dataset_parquet,
                    csv_path=self.dataset_csv,
                )
                export_funnel_summary(
                    funnel_path=self.funil_csv,
                    total_evaluated=stats["total_evaluated"],
                    discarded_no_actions=stats["discarded_no_actions"],
                    discarded_low_releases=stats["discarded_low_releases"],
                    discarded_low_runs=stats["discarded_low_runs"],
                    accepted_count=len(accepted_records),
                    min_releases=self.min_releases,
                    min_workflow_runs=self.min_workflow_runs,
                )
                return {
                    "total_evaluated": stats["total_evaluated"],
                    "accepted_count": len(accepted_records),
                    "parquet_path": self.dataset_parquet,
                    "csv_path": self.dataset_csv,
                    "funil_csv": self.funil_csv,
                }

            stop_event = asyncio.Event()
            candidate_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
            in_flight: set[str] = set()

            # Worker coroutine
            async def worker():
                while not stop_event.is_set():
                    try:
                        candidate = await asyncio.wait_for(candidate_queue.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        if stop_event.is_set():
                            break
                        continue

                    if candidate is None:
                        candidate_queue.task_done()
                        break

                    full_name = candidate.get("full_name")
                    if not full_name:
                        candidate_queue.task_done()
                        continue

                    async with self._lock:
                        if (
                            full_name in evaluated_names
                            or full_name in in_flight
                            or stop_event.is_set()
                        ):
                            candidate_queue.task_done()
                            continue
                        in_flight.add(full_name)

                    record, reason = await self.evaluate_candidate(client, candidate)

                    async with self._lock:
                        in_flight.discard(full_name)

                        if record is not None:
                            if len(accepted_records) < self.target_size:
                                accepted_records.append(record)
                                accepted_names.add(full_name)
                                evaluated_names.add(full_name)
                                stats["total_evaluated"] += 1
                                logger.info(
                                    "Accepted repository [%d/%d]: %s (stars: %d, tier: %s)",
                                    len(accepted_records),
                                    self.target_size,
                                    full_name,
                                    record["stars"],
                                    record["overall_dora_tier"],
                                    )
                                save_repositories_dataset(
                                    records=accepted_records,
                                    parquet_path=self.dataset_parquet,
                                    csv_path=self.dataset_csv,
                                )
                                if len(accepted_records) >= self.target_size:
                                    stop_event.set()
                            else:
                                # Target reached before this valid repo finished; leave it
                                # un-evaluated so a future run with higher limit can pick it up.
                                candidate_queue.task_done()
                                continue
                        else:
                            # Discarded repository
                            evaluated_names.add(full_name)
                            stats["total_evaluated"] += 1
                            if reason == "no_actions":
                                stats["discarded_no_actions"] += 1
                            elif reason == "low_releases":
                                stats["discarded_low_releases"] += 1
                            elif reason == "low_runs":
                                stats["discarded_low_runs"] += 1

                        # Save state & funnel atomically
                        self._save_state({
                            **stats,
                            "evaluated_names": list(evaluated_names),
                        })
                        export_funnel_summary(
                            funnel_path=self.funil_csv,
                            total_evaluated=stats["total_evaluated"],
                            discarded_no_actions=stats["discarded_no_actions"],
                            discarded_low_releases=stats["discarded_low_releases"],
                            discarded_low_runs=stats["discarded_low_runs"],
                            accepted_count=len(accepted_records),
                            min_releases=self.min_releases,
                            min_workflow_runs=self.min_workflow_runs,
                        )

                    candidate_queue.task_done()

            # Start worker pool
            workers = [asyncio.create_task(worker()) for _ in range(self.num_workers)]

            # Producer: stream candidate repos
            try:
                async for cand in iter_candidates_by_stars(
                    client=client, star_ranges=self.star_ranges
                ):
                    if stop_event.is_set():
                        break
                    await candidate_queue.put(cand)
            finally:
                # Signal workers to shut down
                for _ in range(self.num_workers):
                    await candidate_queue.put(None)
                await asyncio.gather(*workers, return_exceptions=True)

            # Final state persistence after workers have joined
            self._save_state({
                **stats,
                "evaluated_names": list(evaluated_names),
            })
            export_funnel_summary(
                funnel_path=self.funil_csv,
                total_evaluated=stats["total_evaluated"],
                discarded_no_actions=stats["discarded_no_actions"],
                discarded_low_releases=stats["discarded_low_releases"],
                discarded_low_runs=stats["discarded_low_runs"],
                accepted_count=len(accepted_records),
                min_releases=self.min_releases,
                min_workflow_runs=self.min_workflow_runs,
            )

            return {
                "total_evaluated": stats["total_evaluated"],
                "accepted_count": len(accepted_records),
                "parquet_path": self.dataset_parquet,
                "csv_path": self.dataset_csv,
                "funil_csv": self.funil_csv,
            }

        finally:
            if owns_client:
                await client.close()

    def run(self) -> dict[str, Any]:
        """Synchronous wrapper to execute the async pipeline."""
        return asyncio.run(self.run_async())


async def run_pipeline_async(
    config_path: str | Path = "config.yaml",
    limit: int | None = None,
    client: GitHubClient | None = None,
    num_workers: int = 4,
) -> dict[str, Any]:
    """Execute the pipeline asynchronously from a config file."""
    import yaml

    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    orchestrator = PipelineOrchestrator(
        config=config, client=client, limit=limit, num_workers=num_workers
    )
    return await orchestrator.run_async()


def run_pipeline(
    config_path: str | Path = "config.yaml",
    limit: int | None = None,
    client: GitHubClient | None = None,
    num_workers: int = 4,
) -> dict[str, Any]:
    """Execute the pipeline from configuration."""
    return asyncio.run(
        run_pipeline_async(
            config_path=config_path, limit=limit, client=client, num_workers=num_workers
        )
    )
