"""Dados fictícios declarados: valores que o motor encontra, mas que não são vazamento.

A exceção vale por VALOR e por ARQUIVO ao mesmo tempo. Um telefone 119000000xx no
SeedDados.cs é fictício declarado; o mesmo telefone em qualquer outro arquivo é um
achado normal. E qualquer outro valor dentro do SeedDados.cs ou do .http também é
achado normal.

Decisões registradas com o Caio em 06/11/2026: a lista inicial, e depois "Rua de Teste, 1"
e OxigenioDomiciliar, que valem só no LuzVital.Api.http (o exemplo de POST da API).
"""

from __future__ import annotations

import os
import re

SEED = "SeedDados.cs"
HTTP = "LuzVital.Api.http"
ARQUIVOS_DE_DADOS_FICTICIOS = {SEED, HTTP}

# (regra, arquivos onde vale, como reconhecer o valor). O valor nunca sai desta função.
_VALORES = [
    ("telefone", {SEED, HTTP}, lambda v: re.fullmatch(r"(?:55)?119000000\d{2}", _digitos(v)) is not None),
    ("endereco", {SEED, HTTP}, lambda v: re.match(r"(?:Rua Exemplo|Rua Modelo)\b", v) is not None),
    ("cpf", {SEED, HTTP}, lambda v: _digitos(v) == "52998224725"),
    ("endereco", {HTTP}, lambda v: v.strip() == "Rua de Teste, 1"),
    ("saude", {HTTP}, lambda v: v == "OxigenioDomiciliar"),
]

DESCRICAO = [
    "Telefones 119000000xx (seed e .http)",
    'Endereços "Rua Exemplo" e "Rua Modelo" (seed e .http)',
    "CPF de teste 529.982.247-25 (seed e .http)",
    '"Rua de Teste, 1" e OxigenioDomiciliar (só no .http)',
]


def _digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor)


def eh_ficticio(regra: str, valor: str, arquivo: str | None) -> bool:
    if not arquivo:
        return False
    nome = os.path.basename(arquivo)
    return any(r == regra and nome in arquivos and teste(valor) for r, arquivos, teste in _VALORES)
