"""
Ingestion pipeline orchestrator.

Runs pipeline stages in order. Use --stage to run a single stage or
omit it to run all stages sequentially.

Usage:
    python run_pipeline.py --stage download
    python run_pipeline.py --stage extract
    python run_pipeline.py           # runs all stages
"""

from __future__ import annotations

import argparse
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("run_pipeline")

STAGES = ["download", "extract", "classify", "chunk", "embed", "store"]


async def run_stage(stage: str) -> None:
    if stage == "download":
        from download import run_download

        results = await run_download()
        for r in results:
            detail = r.file_hash or r.error or ""
            logger.info("[%s] %s — %s", r.status.value.upper(), r.source_filename, detail)
    elif stage == "extract":
        logger.info("Extract stage not yet wired to orchestrator — run extract.py directly")
    else:
        logger.warning("Stage '%s' not yet implemented", stage)


async def main(stages: list[str]) -> None:
    for stage in stages:
        logger.info("=== Stage: %s ===", stage)
        await run_stage(stage)
    logger.info("Pipeline complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EPSCAxplor ingestion pipeline")
    parser.add_argument(
        "--stage",
        choices=STAGES,
        default=None,
        help="Run a single stage (default: run all stages)",
    )
    args = parser.parse_args()
    selected = [args.stage] if args.stage else STAGES
    asyncio.run(main(selected))
