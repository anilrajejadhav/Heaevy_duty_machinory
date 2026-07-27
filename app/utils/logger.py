"""Logging setup used by the API and services."""

import logging


def configure_logging(level: str) -> None:
    """Configure concise logs suitable for a terminal demo."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True,
    )
