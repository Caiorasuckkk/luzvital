"""Índice de Risco Cidadão (0 a 100).

    peso   = severidade da regra (1 a 5) × fator da categoria
    fator  = saúde 2,0 · segredo 1,5 · identificação, contato e localização 1,0
    S      = soma dos pesos dos vazamentos não sanitizados
    Índice = arredonda( 100 × (1 − e^(−S/20)) )
    Faixa  = 0–29 baixo · 30–59 médio · 60–100 alto

Entram em S:
    - fluxos do taint com status VAZAMENTO;
    - dado inteiro encontrado nas respostas da API em funcionamento (scanner de runtime);
    - segredos (senha, chave de API) escritos no código.

Um defeito conta uma vez, mesmo que chegue a várias rotas: o CPF cru dentro de um DTO
usado por 4 endpoints é 1 vazamento de CPF, e o relatório mostra as 4 rotas. Se o mesmo
ponto vaza dois dados (telefone e dependência no mesmo log), cada dado conta.

Não entram em S (aparecem no relatório, à parte): fluxos SANITIZADOS, exposições aceitas,
dados fictícios declarados e dado pessoal escrito no código que não seja segredo.
"""

from __future__ import annotations

import math

from cyber.pii.regras import SAUDE, SEGREDO

K = 20
FATOR = {SAUDE: 2.0, SEGREDO: 1.5}
FAIXAS = [(60, "alto"), (30, "médio"), (0, "baixo")]


def fator(categoria: str) -> float:
    return FATOR.get(categoria, 1.0)


def faixa(indice: int) -> str:
    for limite, nome in FAIXAS:
        if indice >= limite:
            return nome
    return "baixo"


def calcular(vazamentos: list[dict]) -> dict:
    """`vazamentos`: dicts com chave, rotulo, categoria, severidade e origem. A chave deduplica."""
    unicos: dict[tuple, dict] = {}
    for v in vazamentos:
        unicos.setdefault(tuple(v["chave"]), v)

    parcelas = []
    for v in unicos.values():
        peso = v["severidade"] * fator(v["categoria"])
        parcelas.append({**v, "fator": fator(v["categoria"]), "peso": peso})

    soma = sum(p["peso"] for p in parcelas)
    indice = round(100 * (1 - math.exp(-soma / K)))
    return {"indice": indice, "faixa": faixa(indice), "soma": soma, "parcelas": parcelas}
