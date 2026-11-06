import json
import sys
import types

from cyber.ia import remediacao

ITEM = {"id": "1.1", "alvo": "x", "regra": "telefone", "rotulo": "Telefone", "categoria": "contato", "onde": "log",
        "local": "Notificador.cs:28", "caminho": "destinatario.Telefone → _logger.LogInformation(...) [log]",
        "trecho": "(11) *****-4321", "com_saude": True}


def test_sem_chave_cai_no_offline(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = remediacao.remediar([ITEM])
    assert r["modo"] == "offline" and "ANTHROPIC_API_KEY" in r["motivo"]
    texto = r["itens"][0]
    assert "telefone" in texto["alerta_cidadao"].lower() and "Mascara.Telefone" in texto["correcao_tecnica"]


def _cliente_falso(registro, resposta_texto=None, erro=None):
    """Módulo `anthropic` de mentira: guarda o pedido e devolve uma resposta pronta."""
    mod = types.ModuleType("anthropic")

    class APIStatusError(Exception):
        status_code = 500
        message = "erro"

    for nome in ("AuthenticationError", "PermissionDeniedError", "NotFoundError", "RateLimitError", "BadRequestError"):
        setattr(mod, nome, type(nome, (APIStatusError,), {}))
    mod.APIStatusError = APIStatusError
    mod.APIConnectionError = type("APIConnectionError", (Exception,), {})

    class Mensagens:
        def create(self, **kw):
            registro.append(kw)
            if erro:
                raise getattr(mod, erro)()
            bloco = types.SimpleNamespace(type="text", text=resposta_texto)
            return types.SimpleNamespace(stop_reason="end_turn", content=[bloco], model=kw["model"])

    class Anthropic:
        def __init__(self):
            self.messages = Mensagens()
            self.beta = types.SimpleNamespace(messages=Mensagens())

    mod.Anthropic = Anthropic
    return mod


def test_online_manda_so_o_achado_mascarado(monkeypatch):
    registro = []
    resposta = json.dumps({"itens": [{"id": "1.1", "alerta_cidadao": "A", "correcao_tecnica": "B"}]})
    monkeypatch.setitem(sys.modules, "anthropic", _cliente_falso(registro, resposta))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "teste")
    monkeypatch.setenv("LUZVITAL_MODELO", "claude-opus-5-5")

    item = {**ITEM, "campo_extra_que_nao_pode_sair": "11987654321"}
    r = remediacao.remediar([item])

    assert r["modo"] == "online" and r["itens"][0]["alerta_cidadao"] == "A"
    enviado = registro[0]["messages"][0]["content"]
    assert "11987654321" not in enviado and "campo_extra" not in enviado
    assert "(11) *****-4321" in enviado
    assert registro[0]["model"] == "claude-opus-5-5"
    assert registro[0]["fallbacks"] == "default"


def test_erro_da_api_cai_no_offline(monkeypatch):
    monkeypatch.setitem(sys.modules, "anthropic", _cliente_falso([], erro="RateLimitError"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "teste")
    r = remediacao.remediar([ITEM])
    assert r["modo"] == "offline" and "limite" in r["motivo"]


def test_payload_com_dado_inteiro_nao_e_enviado(monkeypatch):
    registro = []
    monkeypatch.setitem(sys.modules, "anthropic", _cliente_falso(registro, "{}"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "teste")
    r = remediacao.remediar([{**ITEM, "trecho": "(11) 98765-4321"}])
    assert r["modo"] == "offline" and registro == []
