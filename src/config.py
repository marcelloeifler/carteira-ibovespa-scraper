"""Configurações do projeto: variáveis do .env e log."""

import logging.config
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def setup_logging() -> None:
    """Aplica o logs.conf da raiz do projeto. Cada pipeline chama isto ao iniciar."""
    # disable_existing_loggers=False: mantém os loggers dos módulos já importados.
    logging.config.fileConfig(ROOT_DIR / "logs.conf", disable_existing_loggers=False)

_TRUE = {"1", "true", "yes", "sim", "on"}
_FALSE = {"0", "false", "no", "nao", "não", "off"}


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ValueError(f"Valor inválido para {name}: {raw!r}. Use True ou False.")


def _get_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Defina {name} no .env")
    return value


DRY_RUN: bool = _get_bool("DRY_RUN", default=False)


@dataclass(frozen=True)
class MongoSettings:
    host: str
    port: int
    user: str
    password: str
    database: str


def mongo_settings() -> MongoSettings:
    return MongoSettings(
        host=os.getenv("MONGO_HOST", "localhost"),
        port=int(os.getenv("MONGO_PORT", "27017")),
        user=_get_required("MONGO_USER"),
        password=_get_required("MONGO_PASSWORD"),
        database=os.getenv("MONGO_DB", "carteira_ibovespa"),
    )
