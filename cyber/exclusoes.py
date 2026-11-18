"""Arquivos que ficam fora da análise estática, com o motivo (cyber/exclusoes.json).

Os caminhos no JSON são relativos à raiz do repositório. A comparação é feita pelo
caminho absoluto, então funciona com qualquer pasta de trabalho.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

RAIZ_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARQUIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exclusoes.json")


@lru_cache(maxsize=1)
def carregar() -> tuple[dict, ...]:
    with open(ARQUIVO, encoding="utf-8") as f:
        return tuple(json.load(f)["arquivos"])


def _normalizar(caminho: str) -> str:
    return os.path.normcase(os.path.abspath(caminho))


@lru_cache(maxsize=1)
def _excluidos() -> frozenset[str]:
    return frozenset(_normalizar(os.path.join(RAIZ_REPO, e["caminho"])) for e in carregar())


def excluido(caminho: str) -> bool:
    return _normalizar(caminho) in _excluidos()
