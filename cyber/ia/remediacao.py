"""IA na remediação.

Para cada achado, gera:
    alerta_cidadao     explicação em linguagem simples do risco para a pessoa
    correcao_tecnica   o que o desenvolvedor deve mudar no código

Modo online: API da Anthropic (pacote `anthropic`). Chave em ANTHROPIC_API_KEY,
modelo em LUZVITAL_MODELO (padrão: claude-opus-5-5). Nos modelos que aceitam, o
pedido vai com `fallbacks: "default"`: se o modelo recusar por política, a própria
API refaz o pedido em outro modelo.

Modo offline: sem chave, sem o pacote ou com erro na API, usa os textos-modelo de
textos_offline.py. O relatório diz qual modo foi usado e por quê.

Proteção do dado: o que vai para o modelo é montado a partir de uma lista fixa de
campos (tipo do dado, onde saiu, arquivo:linha, caminho no código e o trecho JÁ
mascarado). Antes de enviar, o payload passa pelo motor PII; se aparecer qualquer
dado inteiro, o envio é cancelado e o modo cai para offline.
"""

from __future__ import annotations

import json
import os

from cyber.ia import textos_offline
from cyber.pii import regras as pii

MODELO_PADRAO = "claude-opus-5-5"
MODELOS_COM_FALLBACK = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}
MODELOS_COM_EFFORT = MODELOS_COM_FALLBACK | {"claude-haiku-5-5", "claude-fable-5", "claude-sonnet-5", "claude-opus-4-8"}

CAMPOS_PERMITIDOS = ("id", "regra", "rotulo", "categoria", "onde", "local", "caminho", "trecho", "com_saude")

SISTEMA = """Você ajuda a equipe da Luz Vital, um sistema que avisa pessoas que dependem de energia em casa \
(oxigênio, insulina na geladeira, cadeira motorizada) quando há risco de apagão. Você recebe achados de \
segurança de uma análise do código C# da API. Os dados pessoais já vêm mascarados; nunca tente reconstruí-los.

Para cada achado, escreva:
- alerta_cidadao: 1 ou 2 frases curtas em português simples, para a pessoa cadastrada. Diga qual dado ficou \
exposto, onde, e o que alguém mal-intencionado poderia fazer com ele. Sem termos técnicos (nada de "log", \
"endpoint", "DTO"; diga "registro do servidor", "resposta do sistema"). Exemplo: "O telefone de quem usa \
oxigênio aparecia no registro do servidor. Qualquer pessoa com acesso aos registros poderia ligar para ela."
- correcao_tecnica: 1 ou 2 frases para o desenvolvedor C#. Diga o que mudar e onde. Use as ferramentas que já \
existem no projeto: Cpf.Mascarar(...), Mascara.Telefone(...) e DTOs de resposta que omitem o campo.

Devolva um item por achado, com o mesmo id."""

SCHEMA = {
    "type": "object",
    "properties": {
        "itens": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "alerta_cidadao": {"type": "string"},
                    "correcao_tecnica": {"type": "string"},
                },
                "required": ["id", "alerta_cidadao", "correcao_tecnica"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["itens"],
    "additionalProperties": False,
}


def _payload(itens: list[dict]) -> list[dict]:
    return [{k: item[k] for k in CAMPOS_PERMITIDOS if k in item} for item in itens]


def _tem_dado_inteiro(texto: str) -> bool:
    return any(a.status == pii.ACHADO for a in pii.encontrar(texto).achados)


def _offline(itens: list[dict], motivo: str, modelo: str | None = None) -> dict:
    return {
        "modo": "offline",
        "modelo": modelo,
        "motivo": motivo,
        "itens": [{**item, **textos_offline.gerar(item), "origem_texto": "modelo offline"} for item in itens],
    }


def remediar(itens: list[dict]) -> dict:
    """Recebe achados já mascarados e devolve os textos de remediação, com o modo usado."""
    if not itens:
        return {"modo": "offline", "modelo": None, "motivo": "nenhum achado para remediar", "itens": []}
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _offline(itens, "ANTHROPIC_API_KEY não configurada")
    try:
        import anthropic
    except ImportError:
        return _offline(itens, "pacote anthropic não instalado (pip install -r cyber/requirements.txt)")

    modelo = os.environ.get("LUZVITAL_MODELO") or MODELO_PADRAO
    conteudo = json.dumps({"achados": _payload(itens)}, ensure_ascii=False, indent=1)
    if _tem_dado_inteiro(conteudo):
        return _offline(itens, "envio cancelado: o payload continha dado pessoal inteiro", modelo)

    pedido = {
        "model": modelo,
        "max_tokens": 16000,
        "system": SISTEMA,
        "messages": [{"role": "user", "content": conteudo}],
        "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
    }
    if modelo in MODELOS_COM_EFFORT:
        pedido["output_config"]["effort"] = "medium"

    client = anthropic.Anthropic()
    try:
        if modelo in MODELOS_COM_FALLBACK:
            resposta = client.beta.messages.create(
                **pedido, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            )
        else:
            resposta = client.messages.create(**pedido)
    except anthropic.AuthenticationError:
        return _offline(itens, "chave da Anthropic inválida", modelo)
    except anthropic.PermissionDeniedError:
        return _offline(itens, "a chave não tem permissão para esse modelo", modelo)
    except anthropic.NotFoundError:
        return _offline(itens, f"modelo {modelo} não encontrado (confira LUZVITAL_MODELO)", modelo)
    except anthropic.RateLimitError:
        return _offline(itens, "limite de uso da API atingido; tente de novo mais tarde", modelo)
    except anthropic.BadRequestError as e:
        return _offline(itens, f"pedido recusado pela API: {e.message}", modelo)
    except anthropic.APIStatusError as e:
        return _offline(itens, f"erro da API ({e.status_code})", modelo)
    except anthropic.APIConnectionError:
        return _offline(itens, "sem conexão com a API da Anthropic", modelo)

    if resposta.stop_reason == "refusal":
        categoria = getattr(getattr(resposta, "stop_details", None), "category", None)
        return _offline(itens, f"o modelo recusou o pedido (categoria: {categoria})", modelo)
    if resposta.stop_reason == "max_tokens":
        return _offline(itens, "resposta cortada por max_tokens", modelo)

    try:
        texto = next(b.text for b in resposta.content if b.type == "text")
        gerados = {i["id"]: i for i in json.loads(texto)["itens"]}
    except (StopIteration, json.JSONDecodeError, KeyError, TypeError):
        return _offline(itens, "resposta do modelo fora do formato esperado", modelo)

    saida = []
    for item in itens:
        g = gerados.get(item["id"])
        if g:
            saida.append({**item, "alerta_cidadao": g["alerta_cidadao"], "correcao_tecnica": g["correcao_tecnica"],
                          "origem_texto": f"IA ({resposta.model})"})
        else:
            saida.append({**item, **textos_offline.gerar(item), "origem_texto": "modelo offline (IA não devolveu)"})
    return {"modo": "online", "modelo": resposta.model, "motivo": None, "itens": saida}
