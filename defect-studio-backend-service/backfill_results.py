#!/usr/bin/env python3
"""Index generated images that are in object storage but not in the database.

Manual on purpose. A generation indexes itself when the agent announces the
upload, and again when the run completes; this is for what those two missed —
images from before that hook existed, or a run the BFF was down for from start
to finish. At twenty-six threads, a scheduled job would spend most of its life
listing prefixes that have not changed. When that stops being true, this is
what the job should call.

Usage:
    python backfill_results.py --dry-run          # count what would be scanned
    python backfill_results.py
    python backfill_results.py --thread <uuid>
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid

import src.container.database.entities  # noqa: F401 — completes the mapper registry
from src.container.database.engine import SessionLocal
from src.container.infrastructure import get_storage
from src.plan.infrastructure.adapters.repositories.plan_repository_adapter import PlanRepositoryAdapter
from src.plan.infrastructure.repositories.plan_repository_impl import PlanRepositoryImpl
from src.result.application.services import ResultArtifactRegistrar, ResultBackfill
from src.result.infrastructure.adapters.repositories.result_artifact_repository_adapter import (
    ResultArtifactRepositoryAdapter,
)
from src.result.infrastructure.repositories.result_artifact_repository_impl import (
    ResultArtifactRepositoryImpl,
)
from src.run.domain.services import EventProcessor
from src.run.infrastructure.adapters.repositories.run_event_repository_adapter import (
    RunEventRepositoryAdapter,
)
from src.run.infrastructure.adapters.repositories.run_repository_adapter import RunRepositoryAdapter
from src.run.infrastructure.repositories.run_event_repository_impl import RunEventRepositoryImpl
from src.run.infrastructure.repositories.run_repository_impl import RunRepositoryImpl
from src.thread.infrastructure.adapters.repositories.thread_repository_adapter import ThreadRepositoryAdapter
from src.thread.infrastructure.entity.thread_entity import ThreadEntity
from src.thread.infrastructure.mappers import ThreadMapper
from src.thread.infrastructure.repositories.thread_repository_impl import ThreadRepositoryImpl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Count, do not write")
    parser.add_argument("--thread", help="Only this thread id")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    db = SessionLocal()
    try:
        query = db.query(ThreadEntity)
        if args.thread:
            query = query.filter(ThreadEntity.id == uuid.UUID(args.thread))
        threads = [ThreadMapper.to_domain(e) for e in query.all()]
        if not threads:
            print("No threads to scan.")
            return 0

        backfill = ResultBackfill(
            PlanRepositoryAdapter(PlanRepositoryImpl(db)),
            RunRepositoryAdapter(RunRepositoryImpl(db)),
            RunEventRepositoryAdapter(RunEventRepositoryImpl(db)),
            ResultArtifactRegistrar(
                ThreadRepositoryAdapter(ThreadRepositoryImpl(db)),
                ResultArtifactRepositoryAdapter(ResultArtifactRepositoryImpl(db)),
                get_storage(),
            ),
            EventProcessor(),
        )

        print(f"Scanning {len(threads)} thread(s){' (dry run)' if args.dry_run else ''}...")
        report = backfill.run(threads, dry_run=args.dry_run)

        print(f"\n  plans scanned      {report.plans_scanned}")
        print(f"  images registered  {report.images_registered}")
        if report.plans_without_a_run:
            # Recovered, but listed without times — no run means no start or end.
            print(f"  recovered without a run  {report.plans_without_a_run} plan(s)")
        if report.failures:
            print(f"  plans that failed  {report.failures}  (see the log above)")
        return 1 if report.failures else 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
