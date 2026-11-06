"""Dados fictícios declarados: valores que o motor encontra, mas que não são vazamento.

A exceção vale por VALOR e por ARQUIVO ao mesmo tempo. Um telefone 119000000xx no
SeedDados.cs é fictício declarado; o mesmo telefone em qualquer outro arquivo é um
achado normal. E qualquer outro valor dentro do SeedDados.cs ou do .http também é
achado normal.

Decisão registrada com o Caio em 06/11/2026.
"""

from __future__ import annotations

import os
import re

ARQUIVOS_DE_DADOS_FICTICIOS = {"SeedDados.cs", "LuzVital.Api.http"}

# (regra, como reconhecer o valor). O valor nunca sai desta função.
_VALORES = [
    ("telefone", lambda v: re.fullmatch(r"(?:55)?119000000\d{2}", _digitos(v)) is not None),
    ("endereco", lambda v: re.match(r"(?:Rua Exemplo|Rua Modelo)\b", v) is not None),
    ("cpf", lambda v: _digitos(v) == "52998224725"),
]

DESCRICAO = [
    "Telefones 119000000xx",
    'Endereços "Rua Exemplo" e "Rua Modelo"',
    "CPF de teste 529.982.247-25",
]


def _digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor)


def eh_ficticio(regra: str, valor: str, arquivo: str | None) -> bool:
    if not arquivo or os.path.basename(arquivo) not in ARQUIVOS_DE_DADOS_FICTICIOS:
        return False
    return any(nome == regra and teste(valor) for nome, teste in _VALORES)
