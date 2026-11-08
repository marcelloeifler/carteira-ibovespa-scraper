"""Coleta da carteira do dia de um índice da B3."""

import base64
import json
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

BASE_URL = "https://sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/"
TIMEOUT_SECONDS = 30
MAX_PAGES = 20


def build_url(params: dict) -> str:
    raw = json.dumps(params, separators=(",", ":"))
    return BASE_URL + base64.b64encode(raw.encode()).decode()


def _session() -> requests.Session:
    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"Accept": "application/json", "User-Agent": "carteira-ibovespa-scraper/0.1"})
    return session


def request_params(index: str, segment: str, page_size: int, language: str = "pt-br") -> dict:
    """Parâmetros da requisição, sem o número da página."""
    return {"language": language, "pageSize": page_size, "index": index, "segment": segment}


def _total_pages(payload) -> int | None:
    page = payload.get("page") if isinstance(payload, dict) else None
    total = page.get("totalPages") if isinstance(page, dict) else None
    return total if isinstance(total, int) else None


def fetch_portfolio(params: dict) -> list[dict]:
    """Busca todas as páginas e devolve as respostas da API sem alterações, em ordem.

    Só falha por erro de rede, erro HTTP ou resposta que não seja JSON. Se a paginação
    mudar de formato, mantém o que já veio em vez de falhar.
    """
    payloads = []
    with _session() as session:
        for page_number in range(1, MAX_PAGES + 1):
            url = build_url({"language": params["language"], "pageNumber": page_number,
                             "pageSize": params["pageSize"], "index": params["index"],
                             "segment": params["segment"]})
            log.info("Buscando página %d de %s", page_number, params["index"])
            response = session.get(url, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            payloads.append(response.json())

            total_pages = _total_pages(payloads[-1])
            if total_pages is None:
                log.warning("Resposta sem page.totalPages; mantendo só as páginas já obtidas")
                break
            if page_number >= total_pages:
                break
        else:
            log.warning("Limite de %d páginas atingido", MAX_PAGES)
    return payloads
