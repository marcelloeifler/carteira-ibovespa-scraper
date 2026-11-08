"""Interpretação das respostas brutas da B3 (usado na etapa MongoDB -> Postgres).

Tudo aqui é tolerante a mudanças no JSON: nada levanta exceção por campo ausente.
"""

from datetime import datetime, timezone
from decimal import Decimal

PART_TOLERANCE = Decimal("0.1")


def get_path(data, *path):
    """Lê data[path[0]][path[1]]..., devolvendo None se algum nível não existir."""
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def parse_br_number(value: str) -> Decimal:
    """Converte "1.460.506,056" em Decimal("1460506.056")."""
    return Decimal(value.replace(".", "").replace(",", "."))


def parse_reference_date(payloads: list[dict]) -> datetime | None:
    """Data de vigência da carteira (header.date, "09/11/26") em UTC, ou None se não der."""
    value = get_path(payloads[0], "header", "date") if payloads else None
    try:
        return datetime.strptime(value, "%d/%m/%y").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def validate(payloads: list[dict]) -> list[str]:
    """Lista os problemas encontrados; lista vazia significa carteira coerente."""
    if not payloads:
        return ["Nenhuma página retornada"]

    errors = []
    dates = {get_path(p, "header", "date") for p in payloads}
    if None in dates:
        errors.append("Campo header.date ausente")
    elif len(dates) != 1:
        errors.append(f"Páginas com datas diferentes: {sorted(dates)}")
    elif parse_reference_date(payloads) is None:
        errors.append(f"header.date em formato inesperado: {sorted(dates)}")

    pages_results = [get_path(p, "results") for p in payloads]
    if not all(isinstance(r, list) for r in pages_results):
        errors.append("Campo results ausente ou não é uma lista")
        return errors
    results = [r for page in pages_results for r in page]
    if not results:
        errors.append("Nenhum ativo retornado")
        return errors

    expected = get_path(payloads[0], "page", "totalRecords")
    if expected is None:
        errors.append("Campo page.totalRecords ausente")
    elif len(results) != expected:
        errors.append(f"Esperados {expected} ativos, recebidos {len(results)}")

    codes = [get_path(r, "cod") for r in results]
    if None in codes:
        errors.append("Ativo sem o campo cod")
    elif len(set(codes)) != len(codes):
        errors.append("Há códigos de ativos repetidos")

    try:
        total = sum(parse_br_number(get_path(r, "part")) for r in results)
    except (AttributeError, ArithmeticError):
        errors.append("Campo part ausente ou em formato inesperado")
    else:
        if abs(total - 100) > PART_TOLERANCE:
            errors.append(f"Soma das participações fora do esperado: {total}")
    return errors
