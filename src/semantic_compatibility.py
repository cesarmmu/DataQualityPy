"""Compatibilidad semántica básica de valores para DataQualityPy V7-C2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import ipaddress
import re
from typing import Callable
from urllib.parse import urlparse
import uuid

import pandas as pd

from src.column_analysis import ColumnAnalysis


class SemanticCompatibilityType(str, Enum):
    """Formatos genéricos cuya compatibilidad puede medirse."""

    NUMERIC = "numeric"
    DATE = "date"
    BOOLEAN = "boolean"
    EMAIL = "email"
    URL = "url"
    IPV4 = "ipv4"
    UUID = "uuid"


@dataclass(frozen=True)
class CompatibilityEvidence:
    """Evidencia resumida para una compatibilidad concreta."""

    compatibility_type: SemanticCompatibilityType
    compatible_count: int
    compatible_ratio: float


@dataclass(frozen=True)
class SemanticCompatibilityAnalysis:
    """Resultado descriptivo de compatibilidades observadas."""

    analyzed_count: int
    compatibilities: tuple[CompatibilityEvidence, ...]


_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_BOOLEAN_TRUE = {"true", "yes", "si", "sí"}
_BOOLEAN_FALSE = {"false", "no"}


def _ratio(cantidad: int, total: int) -> float:
    """Calcula un porcentaje evitando divisiones por cero."""
    return cantidad / total * 100 if total > 0 else 0.0


def _es_email_compatible(valor: object) -> bool:
    """Comprueba compatibilidad con un formato básico de email."""
    return bool(_EMAIL_PATTERN.fullmatch(str(valor).strip()))


def _es_url_compatible(valor: object) -> bool:
    """Comprueba compatibilidad básica con URL HTTP o HTTPS."""
    texto = str(valor).strip()

    try:
        resultado = urlparse(texto)
    except ValueError:
        return False

    return (
        resultado.scheme.lower() in {"http", "https"}
        and bool(resultado.netloc)
    )


def _es_ipv4_compatible(valor: object) -> bool:
    """Comprueba si un valor representa una dirección IPv4."""
    texto = str(valor).strip()

    try:
        return ipaddress.ip_address(texto).version == 4
    except ValueError:
        return False


def _es_uuid_compatible(valor: object) -> bool:
    """Comprueba si un valor representa un UUID estándar."""
    texto = str(valor).strip()

    try:
        uuid.UUID(texto)
    except (ValueError, AttributeError):
        return False

    return True


def _es_booleano_compatible(valor: object) -> bool:
    """Comprueba formas booleanas conservadoras, incluidas 0 y 1."""
    if isinstance(valor, bool):
        return True

    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return valor in {0, 1}

    texto = str(valor).strip().casefold()

    if texto in {"0", "1"}:
        return True

    return texto in _BOOLEAN_TRUE or texto in _BOOLEAN_FALSE


def _contar_compatibles(
    serie: pd.Series,
    comprobador: Callable[[object], bool],
) -> int:
    """Cuenta valores compatibles mediante un comprobador."""
    return int(serie.map(comprobador).sum())


def analizar_compatibilidad_semantica(
    analisis: ColumnAnalysis,
) -> SemanticCompatibilityAnalysis:
    """
    Mide compatibilidades genéricas sin inferir significado de negocio.

    COMPATIBLE no significa válido, correcto ni confirmado semánticamente.
    """
    serie = analisis.analyzable_series
    total = len(serie)

    if total == 0:
        return SemanticCompatibilityAnalysis(
            analyzed_count=0,
            compatibilities=(),
        )

    resultados: list[CompatibilityEvidence] = []

    numeric_conversion = analisis.numeric_conversion
    numeric_count = (
        numeric_conversion.convertible_count
        if numeric_conversion is not None
        else 0
    )
    resultados.append(
        CompatibilityEvidence(
            compatibility_type=SemanticCompatibilityType.NUMERIC,
            compatible_count=numeric_count,
            compatible_ratio=_ratio(numeric_count, total),
        )
    )

    datetime_conversion = analisis.datetime_conversion
    date_count = (
        datetime_conversion.convertible_count
        if datetime_conversion is not None
        else 0
    )
    resultados.append(
        CompatibilityEvidence(
            compatibility_type=SemanticCompatibilityType.DATE,
            compatible_count=date_count,
            compatible_ratio=_ratio(date_count, total),
        )
    )

    comprobadores = (
        (SemanticCompatibilityType.BOOLEAN, _es_booleano_compatible),
        (SemanticCompatibilityType.EMAIL, _es_email_compatible),
        (SemanticCompatibilityType.URL, _es_url_compatible),
        (SemanticCompatibilityType.IPV4, _es_ipv4_compatible),
        (SemanticCompatibilityType.UUID, _es_uuid_compatible),
    )

    for tipo, comprobador in comprobadores:
        cantidad = _contar_compatibles(serie, comprobador)
        resultados.append(
            CompatibilityEvidence(
                compatibility_type=tipo,
                compatible_count=cantidad,
                compatible_ratio=_ratio(cantidad, total),
            )
        )

    return SemanticCompatibilityAnalysis(
        analyzed_count=total,
        compatibilities=tuple(resultados),
    )
