"""Coleta a carteira do dia do Ibovespa na B3 e grava a resposta bruta no MongoDB.

Uso, na raiz do projeto:  python -m src.collect
"""

import hashlib
import json
import logging
from datetime import datetime, timezone

from src import b3, config, mongo

log = logging.getLogger(__name__)

INDEX = "IBOV"
SEGMENT = "2"  # "2" inclui o setor de cada ativo
PAGE_SIZE = 120


def content_hash(payloads: list[dict]) -> str:
    canonical = json.dumps(payloads, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_document(payloads: list[dict], params: dict, collected_at: datetime) -> dict:
    # O coletor não interpreta o JSON da B3: guarda a resposta intacta em "payloads" e só
    # acrescenta o que ele sabe com certeza (o que foi pedido, quando e o hash).
    # Data de vigência e validação ficam para a etapa MongoDB -> Postgres (src/transform.py).
    return {
        "index": params["index"],
        "segment": params["segment"],
        "collected_at": collected_at,
        "source_url": b3.BASE_URL,
        "request_params": params,
        "content_hash": content_hash(payloads),
        "payloads": payloads,  # respostas da API sem alterações, uma por página
        "processed_at": None,
    }


def main() -> int:
    try:
        collected_at = datetime.now(timezone.utc)
        params = b3.request_params(INDEX, SEGMENT, PAGE_SIZE)
        payloads = b3.fetch_portfolio(params)
        document = build_document(payloads, params, collected_at)

        log.info(
            "Coleta de %s: %d página(s), hash %s",
            INDEX, len(payloads), document["content_hash"][:12],
        )

        if config.DRY_RUN:
            log.warning("DRY_RUN ativo: nada foi gravado no MongoDB")
            return 0

        settings = config.mongo_settings()
        with mongo.get_client(settings) as client:
            collection = client[settings.database][mongo.RAW_COLLECTION]
            mongo.ensure_indexes(collection)
            inserted = mongo.save_raw(collection, document)

        if inserted:
            log.info("Documento novo gravado em %s.%s", settings.database, mongo.RAW_COLLECTION)
        else:
            log.info("Conteúdo já existia; atualizado apenas last_seen_at")
        return 0
    except Exception:
        log.exception("Falha na coleta")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
