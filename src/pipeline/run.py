"""Main pipeline runner. Ties together extract, transform, and load stages."""

import argparse
import logging
from datetime import date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_extract(game_date: date) -> None:
    """Extract game data from NHL API for a given date."""
    # TODO: Implement after DataCamp Courses 4-6 (Importing Data / APIs)
    logger.info("Extracting data for %s", game_date)
    raise NotImplementedError("Extract stage not yet implemented")


def run_transform() -> None:
    """Transform raw extracted data into cleaned, enriched datasets."""
    # TODO: Implement after DataCamp Course 7 (Cleaning Data)
    logger.info("Running transformations")
    raise NotImplementedError("Transform stage not yet implemented")


def run_load() -> None:
    """Load transformed data into PostgreSQL."""
    # TODO: Implement after DataCamp Course 13 (ETL and ELT in Python)
    logger.info("Loading data into PostgreSQL")
    raise NotImplementedError("Load stage not yet implemented")


def run_pipeline(game_date: date) -> None:
    """Run the full ETL pipeline for a given date."""
    logger.info("Starting pipeline for %s", game_date)
    run_extract(game_date)
    run_transform()
    run_load()
    logger.info("Pipeline complete for %s", game_date)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NHL Data Pipeline")
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=date.today(),
        help="Game date to process (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument("--extract", action="store_true", help="Run extract only")
    parser.add_argument("--transform", action="store_true", help="Run transform only")
    parser.add_argument("--load", action="store_true", help="Run load only")
    args = parser.parse_args()

    if args.extract:
        run_extract(args.date)
    elif args.transform:
        run_transform()
    elif args.load:
        run_load()
    else:
        run_pipeline(args.date)
