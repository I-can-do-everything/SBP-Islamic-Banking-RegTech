"""Shared test fixtures. Tests run against the local PostgreSQL (see backend/.env)."""

from __future__ import annotations

import os

# Tests never call a real AI provider; the deterministic summary is used instead.
os.environ.setdefault("AI_PROVIDER", "off")

from datetime import date
from pathlib import Path

import duckdb
import pytest

from daleel.core.config import get_settings
from daleel.datagen.export import build_sample
from daleel.datagen.generator import Scenario
from daleel.db.database import migrate
from daleel.ingestion.clean import install_macros
from daleel.ingestion.service import ingest_file
from daleel.pipeline.process import process

PERIOD = date(2026, 9, 30)


@pytest.fixture(scope="session", autouse=True)
def database():
    migrate()


@pytest.fixture()
def duck():
    con = duckdb.connect()
    install_macros(con)
    return con


def _run(name: str, tmp: Path):
    path = get_settings().data_dir / "samples" / f"EXIB_regulatory_extract_2026-09_{name}.xlsx"
    if not path.exists():
        build_sample(Scenario(name=name), path)
    ingestion = ingest_file(path.read_bytes(), path.name, tmp / name)
    result = process({k: d.parquet_path for k, d in ingestion.datasets.items()}, PERIOD, 30, ingestion.summary())
    return ingestion, result


@pytest.fixture(scope="session")
def baseline(tmp_path_factory):
    return _run("baseline", tmp_path_factory.mktemp("runs"))


@pytest.fixture(scope="session")
def stressed(tmp_path_factory):
    return _run("stressed", tmp_path_factory.mktemp("runs"))
