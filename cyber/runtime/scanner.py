"""Scanner de runtime.

Com a API no ar (por padrão em http://localhost:5131), chama os GETs principais e
passa cada valor de texto das respostas JSON pelo motor PII. A prova esperada é:
os CPFs e telefones aparecem só mascarados, e o endereço não aparece.

O tipo de dependência aparece em /api/cidadaos e /api/painel/sem-checkin: é a
exposição aceita registrada em cyber/taint/excecoes.json, e sai marcada assim.

Se a API não estiver no ar, o scanner avisa e devolve `no_ar = False` sem quebrar.
Só faz GET: não cria, não altera e não apaga nada.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from cyber.pii import regras as pii

URL_PADRAO = "http://localhost:5131"
ROTAS_FIXAS = ["/api/cidadaos", "/api/voluntarios", "/api/alertas", "/api/previsoes"]
ROTAS_POR_ALERTA = ["/api/checkins?alertaId={id}", "/api/painel/sem-checkin?alertaId={id}",
                    "/api/painel/resumo?alertaId={id}"]


def _get(url: str, timeout: float = 5.0) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "luzvital-cyber"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def api_no_ar(base: str) -> bool:
    try:
        status, _ = _get(base.rstrip("/") + "/swagger/v1/swagger.json", timeout=2.0)
        return status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def _valores(no, caminho=""):
    """Percorre o JSON e devolve (caminho, chave, valor em texto) de cada folha."""
    if isinstance(no, dict):
        for k, v in no.items():
            yield from _valores(v, f"{caminho}.{k}" if caminho else k)
    elif isinstance(no, list):
        for i, v in enumerate(no):
            yield from _valores(v, f"{caminho}[{i}]")
    elif isinstance(no, str):
        yield caminho, caminho.rsplit(".", 1)[-1], no
    elif isinstance(no, int) and not isinstance(no, bool) and abs(no) >= 10**9:
        yield caminho, caminho.rsplit(".", 1)[-1], str(no)  # número longo pode ser CPF/telefone


def _excecao_para(rota: str, chave: str, regra: str, excecoes: list[dict]) -> dict | None:
    caminho_rota = rota.split("?")[0]
    for e in excecoes:
        if chave == e["campo_json"] and regra in ("saude", "cid10") and any(
            caminho_rota.startswith(ep) for ep in e["endpoints"]
        ):
            return e
    return None


def varrer(base: str = URL_PADRAO, excecoes: list[dict] | None = None) -> dict:
    base = base.rstrip("/")
    excecoes = excecoes or []
    resultado = {"url": base, "no_ar": False, "rotas": [], "achados": [], "mascarados": 0, "avisos": []}
    if not api_no_ar(base):
        resultado["avisos"].append(f"API fora do ar em {base}: scanner de runtime pulado.")
        return resultado
    resultado["no_ar"] = True

    rotas = list(ROTAS_FIXAS)
    _, corpo_alertas = _get(base + "/api/alertas")
    try:
        alertas = json.loads(corpo_alertas)
    except json.JSONDecodeError:
        alertas = []
    if alertas:
        rotas += [r.format(id=alertas[0]["id"]) for r in ROTAS_POR_ALERTA]
    else:
        resultado["avisos"].append("Nenhum alerta ativo: rotas de check-in e painel puladas.")

    for rota in rotas:
        status, corpo = _get(base + rota)
        info = {"rota": rota, "status": status, "valores": 0, "mascarados": 0, "achados": 0}
        try:
            dados = json.loads(corpo) if corpo else None
        except json.JSONDecodeError:
            dados = corpo
        folhas = list(_valores(dados)) if not isinstance(dados, str) else [("", "", dados)]
        for caminho, chave, valor in folhas:
            info["valores"] += 1
            r = pii.encontrar(valor, contexto=f"{rota} · {caminho}")
            info["mascarados"] += len(r.mascarados)
            for a in r.achados:
                e = _excecao_para(rota, chave, a.regra, excecoes)
                if e:
                    a.status, a.motivo = pii.EXPOSICAO_ACEITA, e["id"]
                a.arquivo = rota.split("?")[0]
                a.contexto = f"{rota} · {chave}"
                resultado["achados"].append(a)
                info["achados"] += 1
        resultado["mascarados"] += info["mascarados"]
        resultado["rotas"].append(info)
    return resultado
