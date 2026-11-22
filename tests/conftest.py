from pathlib import Path

import pytest

from plemio.config import Config, load_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def config() -> Config:
    return load_config(ROOT)
