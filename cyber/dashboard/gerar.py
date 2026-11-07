"""Gera o relatorio.html a partir do achados.json.

Um arquivo só, com CSS e SVG embutidos: abre offline, sem CDN e sem JavaScript.
Tudo o que aparece já está mascarado (o motor PII nunca devolve o dado inteiro).

Cores: as duas séries (alvo 1 e alvo 2) usam os dois primeiros tons da paleta
categórica validada (azul e laranja, ΔE ≥ 24 também para daltonismo). As faixas
do índice usam a paleta de status, sempre com ícone e texto, nunca só a cor.
"""

from __future__ import annotations

from html import escape

from cyber.pii.regras import CATEGORIAS

FAIXA_STATUS = {"baixo": ("bom", "✓"), "médio": ("atencao", "▲"), "alto": ("critico", "■")}

CSS = """
:root{--plano:#f9f9f7;--superficie:#fcfcfb;--tinta:#0b0b0b;--tinta2:#52514e;--muda:#898781;--grade:#e1e0d9;
--eixo:#c3c2b7;--borda:rgba(11,11,11,.10);--s1:#2a78d6;--s2:#eb6834;--bom:#0ca30c;--atencao:#fab219;
--critico:#d03b3b;--aviso-fundo:#fdf0ef}
@media (prefers-color-scheme:dark){:root{--plano:#0d0d0d;--superficie:#1a1a19;--tinta:#f0efec;--tinta2:#c3c2b7;
--grade:#2c2c2a;--eixo:#383835;--borda:rgba(255,255,255,.10);--s1:#3987e5;--s2:#d95926;--aviso-fundo:#2a1716}}
*{box-sizing:border-box}
body{margin:0;background:var(--plano);color:var(--tinta);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:36px 0 12px}h3{font-size:16px;margin:18px 0 8px}
.sub{color:var(--tinta2);margin:0}
.cartao{background:var(--superficie);border:1px solid var(--borda);border-radius:10px;padding:18px}
.lado{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
.alvo-nome{display:flex;align-items:center;gap:8px;font-weight:600;font-family:ui-monospace,Consolas,monospace;font-size:13px}
.ponto{width:12px;height:12px;border-radius:3px;display:inline-block;flex:none}
.heroi{display:flex;align-items:flex-end;gap:16px;margin:10px 0 4px;flex-wrap:wrap}
.indice{font-size:64px;font-weight:650;line-height:1}
.indice small{font-size:18px;color:var(--tinta2);font-weight:500}
.faixa{display:inline-flex;align-items:center;gap:6px;font-weight:600;padding:3px 10px;border-radius:999px;border:1px solid var(--borda)}
.faixa i{font-style:normal;width:18px;height:18px;border-radius:50%;display:inline-grid;place-items:center;font-size:11px;color:#fff}
.faixa.bom i{background:var(--bom)}.faixa.atencao i{background:var(--atencao);color:#0b0b0b}.faixa.critico i{background:var(--critico)}
.aceitas{font-size:14px;color:var(--tinta2);border-left:3px solid var(--atencao);padding-left:10px}
.aceitas b{color:var(--tinta);font-size:20px}
dl.numeros{display:grid;grid-template-columns:1fr auto;gap:4px 16px;margin:14px 0 0;font-size:14px}
dl.numeros dt{color:var(--tinta2)}dl.numeros dd{margin:0;font-weight:600;text-align:right;font-variant-numeric:tabular-nums}
.aviso{border:2px solid var(--critico);background:var(--aviso-fundo);border-radius:10px;padding:16px 18px;display:flex;gap:14px}
.aviso .icone{font-size:28px;line-height:1;color:var(--critico)}
.aviso p{margin:0;font-size:17px;font-weight:650}
.recomendacao{border-left:3px solid var(--s1);padding:6px 14px;margin:14px 0}
table{width:100%;border-collapse:collapse;font-size:13px;background:var(--superficie)}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--grade);vertical-align:top}
th{color:var(--tinta2);font-weight:600;border-bottom:1px solid var(--eixo)}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
code,.mono{font-family:ui-monospace,Consolas,monospace;font-size:12px}
.caminho{color:var(--tinta2);font-size:12px}
.tag{display:inline-block;font-size:11px;font-weight:700;padding:1px 7px;border-radius:4px;border:1px solid currentColor}
.tag.vaz{color:var(--critico)}.tag.ace{color:#9a6a00}.tag.san{color:#006300}
@media (prefers-color-scheme:dark){.tag.ace{color:var(--atencao)}.tag.san{color:var(--bom)}}
.alertas{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:12px}
.alerta .cidadao{font-size:16px;margin:0 0 10px}
.alerta .tecnica{font-size:13px;color:var(--tinta2);margin:0;border-top:1px solid var(--grade);padding-top:8px}
.meta{font-size:12px;color:var(--muda);margin-top:8px}
.legenda{display:flex;gap:18px;font-size:13px;color:var(--tinta2);margin:6px 0 10px;flex-wrap:wrap}
.legenda span{display:inline-flex;align-items:center;gap:6px}
details summary{cursor:pointer;color:var(--tinta2);margin:8px 0}
.modo{display:inline-block;margin-top:8px;font-size:13px;padding:3px 10px;border-radius:6px;border:1px solid var(--borda);background:var(--superficie)}
footer{margin-top:40px;color:var(--tinta2);font-size:13px}
"""


def _e(x) -> str:
    return escape(str(x)) if x is not None else ""


def _medidor(indice: int, faixa: str) -> str:
    """Barra de 0 a 100 com marcas em 30 e 60, na cor da faixa."""
    status = FAIXA_STATUS[faixa][0]
    largura = max(indice, 0) * 6
    return (
        f'<svg viewBox="0 0 600 40" width="100%" role="img" aria-label="Índice {indice} de 100, faixa {faixa}">'
        f'<title>Índice {indice} de 100 · faixa {faixa}</title>'
        '<rect x="0" y="6" width="600" height="12" rx="6" fill="var(--grade)"/>'
        + (f'<rect x="0" y="6" width="{largura}" height="12" rx="6" fill="var(--{status})"/>' if largura else "")
        + '<line x1="180" y1="2" x2="180" y2="22" stroke="var(--eixo)" stroke-width="2"/>'
        '<line x1="360" y1="2" x2="360" y2="22" stroke="var(--eixo)" stroke-width="2"/>'
        '<text x="0" y="37" font-size="13" fill="var(--muda)">0</text>'
        '<text x="90" y="37" font-size="13" fill="var(--muda)" text-anchor="middle">baixo</text>'
        '<text x="270" y="37" font-size="13" fill="var(--muda)" text-anchor="middle">médio</text>'
        '<text x="480" y="37" font-size="13" fill="var(--muda)" text-anchor="middle">alto</text>'
        '<text x="600" y="37" font-size="13" fill="var(--muda)" text-anchor="end">100</text>'
        "</svg>"
    )


def _cartao_alvo(i: int, a: dict) -> str:
    faixa = a["faixa"]
    status, icone = FAIXA_STATUS[faixa]
    c = a["contagens"]
    linhas = [
        ("Vazamentos (defeitos únicos)", c["vazamentos_unicos"]),
        ("Fluxos de vazamento no taint", c["fluxos_vazamento"]),
        ("Fluxos sanitizados", c["fluxos_sanitizados"]),
        ("Achados no código (fora do índice)", c["achados_codigo"]),
        ("Dados fictícios declarados", c["ficticios"]),
    ]
    if a.get("runtime"):
        rt = a["runtime"]
        if rt["no_ar"]:
            linhas += [("Runtime: rotas chamadas", len(rt["rotas"])),
                       ("Runtime: valores mascarados vistos", rt["mascarados"]),
                       ("Runtime: dado inteiro na resposta", c["runtime_vazamentos"])]
        else:
            linhas += [("Runtime", "API fora do ar")]
    dl = "".join(f"<dt>{_e(k)}</dt><dd>{_e(v)}</dd>" for k, v in linhas)
    return f"""
<div class="cartao">
  <div class="alvo-nome"><span class="ponto" style="background:var(--s{i + 1})"></span>{_e(a['alvo'])}</div>
  <div class="heroi">
    <div class="indice">{a['indice']}<small> / 100</small></div>
    <div>
      <div class="faixa {status}"><i aria-hidden="true">{icone}</i>Risco {_e(faixa)}</div>
      <div class="aceitas" style="margin-top:10px"><b>{c['exposicoes_aceitas']}</b>
        {"exposição aceita" if c['exposicoes_aceitas'] == 1 else "exposições aceitas"}
        <br>({c['fluxos_aceitos']} fluxos, fora da conta do índice)</div>
    </div>
  </div>
  {_medidor(a['indice'], faixa)}
  <dl class="numeros">{dl}</dl>
  <div class="meta">S = {a['soma']:g} → índice = 100 × (1 − e^(−{a['soma']:g}/20))</div>
</div>"""


def _grafico_categorias(alvos: list[dict]) -> str:
    """Barras horizontais agrupadas: vazamentos únicos por categoria, um tom por alvo."""
    maximo = max([1] + [a["por_categoria"][cat]["vazamentos"] for a in alvos for cat in CATEGORIAS])
    rot_larg, area = 130, 860  # viewBox ~1030 de largura: no tamanho do cartão, o texto fica em 12px
    altura_barra, vao = 12, 2
    grupo = len(alvos) * (altura_barra + vao) + 14
    alt = len(CATEGORIAS) * grupo + 24
    partes = [f'<svg viewBox="0 0 {rot_larg + area + 40} {alt}" width="100%" role="img" '
              f'aria-label="Vazamentos únicos por categoria, por alvo">']
    for t in range(0, maximo + 1):
        x = rot_larg + area * t / maximo
        partes.append(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{alt - 20}" stroke="var(--grade)" stroke-width="1"/>'
                      f'<text x="{x:.1f}" y="{alt - 6}" font-size="10" fill="var(--muda)" text-anchor="middle">{t}</text>')
    for gi, cat in enumerate(CATEGORIAS):
        y0 = gi * grupo + 4
        partes.append(f'<text x="{rot_larg - 10}" y="{y0 + grupo / 2 - 3}" font-size="12" fill="var(--tinta2)" '
                      f'text-anchor="end">{_e(cat)}</text>')
        for ai, a in enumerate(alvos):
            v = a["por_categoria"][cat]["vazamentos"]
            y = y0 + ai * (altura_barra + vao)
            w = area * v / maximo
            if v:
                partes.append(
                    f'<g><title>{_e(a["alvo"])} · {_e(cat)}: {v} vazamento(s)</title>'
                    f'<path d="M{rot_larg},{y} h{w - 4:.1f} a4,4 0 0 1 4,4 v{altura_barra - 8} a4,4 0 0 1 -4,4 h-{w - 4:.1f} z" '
                    f'fill="var(--s{ai + 1})"/>'
                    f'<text x="{rot_larg + w + 5:.1f}" y="{y + altura_barra - 2}" font-size="11" fill="var(--tinta)">{v}</text></g>')
            else:
                partes.append(f'<g><title>{_e(a["alvo"])} · {_e(cat)}: 0</title>'
                              f'<text x="{rot_larg + 4}" y="{y + altura_barra - 2}" font-size="11" fill="var(--muda)">0</text></g>')
        partes.append(f'<line x1="{rot_larg}" y1="{y0 - 2}" x2="{rot_larg}" y2="{y0 + grupo - 12}" stroke="var(--eixo)" stroke-width="1"/>')
    partes.append("</svg>")
    legenda = '<div class="legenda">' + "".join(
        f'<span><span class="ponto" style="background:var(--s{i + 1})"></span>{_e(a["alvo"])}</span>'
        for i, a in enumerate(alvos)) + "</div>"

    cab = "".join(f'<th class="num" colspan="1">{_e(a["alvo"])}</th>' for a in alvos)
    linhas = []
    for cat in CATEGORIAS:
        celulas = []
        for a in alvos:
            p = a["por_categoria"][cat]
            celulas.append(f'<td class="num">{p["vazamentos"]} vaz. · {p["aceitas"]} aceitas · '
                           f'{p["sanitizados"]} sanit. · {p["codigo"]} no código · {p["ficticios"]} fictícios</td>')
        linhas.append(f"<tr><td>{_e(cat)}</td>{''.join(celulas)}</tr>")
    tabela = f'<table><thead><tr><th>Categoria</th>{cab}</tr></thead><tbody>{"".join(linhas)}</tbody></table>'
    return legenda + "".join(partes) + "<details><summary>Ver em tabela (todas as contagens)</summary>" + tabela + "</details>"


def _tabela_fluxos(fluxos: list[dict], vazio: str) -> str:
    if not fluxos:
        return f'<p class="sub">{_e(vazio)}</p>'
    tag = {"VAZAMENTO": ("vaz", "VAZAMENTO"), "EXPOSICAO_ACEITA": ("ace", "EXPOSIÇÃO ACEITA"),
           "SANITIZADO": ("san", "SANITIZADO")}
    linhas = []
    for f in fluxos:
        classe, texto = tag[f["status"]]
        linhas.append(
            f'<tr><td><span class="tag {classe}">{texto}</span></td><td>{_e(f["rotulo"])}<br>'
            f'<span class="caminho">{_e(f["tipo_sorvedouro"])}</span></td>'
            f'<td class="mono">{_e(f["fonte"])}</td><td class="mono">{_e(f["sorvedouro"])}</td>'
            f'<td class="caminho">{_e(" → ".join(f["caminho"]))}</td></tr>')
    return ('<table><thead><tr><th>Status</th><th>Dado</th><th>Fonte</th><th>Sorvedouro</th><th>Caminho</th></tr>'
            f'</thead><tbody>{"".join(linhas)}</tbody></table>')


def _secao_exposicoes(dados: dict) -> str:
    exc = dados["excecoes"]
    blocos = []
    for e in exc["excecoes"]:
        fluxos = []
        for a in dados["alvos"]:
            for f in a["fluxos"]:
                if f["status"] == "EXPOSICAO_ACEITA" and f["excecao"] == e["id"]:
                    fluxos.append(f"{f['sorvedouro']} ({a['alvo']})")
        runtime = [r for a in dados["alvos"] if a.get("runtime")
                   for r in a["runtime"]["achados"] if r["status"] == "EXPOSICAO_ACEITA" and r["motivo"] == e["id"]]
        itens = "".join(f"<li class='mono'>{_e(x)}</li>" for x in fluxos)
        rt = f"<p class='sub'>Na API em funcionamento: {len(runtime)} valor(es) do campo <code>{_e(e['campo_json'])}</code> " \
             f"vistos nessa rota.</p>" if runtime else ""
        blocos.append(f"""
<div class="cartao" style="margin-top:12px">
  <h3 style="margin-top:0">{_e(e['titulo'])}</h3>
  <p><b>Rota:</b> <code>{_e(', '.join(e['endpoints']))}</code> · <b>Campo:</b> <code>{_e(e['campo'])}</code></p>
  <p><b>Motivo:</b> {_e(e['motivo'])}</p>
  <details><summary>{len(fluxos)} fluxo(s) do taint que chegam aqui</summary><ul>{itens}</ul></details>
  {rt}
</div>""")
    return f"""
<h2 id="aceitas">Exposições aceitas</h2>
<p class="sub">Fluxos de dado de saúde que saem de propósito, por finalidade de cuidado. Ficam fora da conta do índice,
mas registrados aqui com o motivo (cyber/taint/excecoes.json).</p>
<div class="aviso" role="alert" style="margin-top:12px"><div class="icone" aria-hidden="true">⚠</div>
  <div><p>{_e(exc['aviso'])}</p></div></div>
<div class="recomendacao"><b>Recomendação técnica:</b> {_e(exc['recomendacao'])}</div>
{''.join(blocos)}"""


def _secao_alertas(dados: dict) -> str:
    rem = dados["remediacao"]
    if rem["modo"] == "online":
        modo = f"Textos gerados pela IA (modo online, modelo {_e(rem['modelo'])}). Só achados mascarados foram enviados."
    else:
        modo = f"Modo offline: textos-modelo por tipo de achado. Motivo: {_e(rem['motivo'])}."
    cartoes = []
    for it in rem["itens"]:
        cartoes.append(f"""
<div class="cartao alerta">
  <p class="cidadao">{_e(it['alerta_cidadao'])}</p>
  <p class="tecnica"><b>Correção:</b> {_e(it['correcao_tecnica'])}</p>
  <div class="meta">{_e(it['alvo'])} · {_e(it['rotulo'])} · {_e(it['onde'])} · <span class="mono">{_e(it['local'])}</span>
   · texto: {_e(it['origem_texto'])}</div>
</div>""")
    corpo = "".join(cartoes) or '<p class="sub">Nenhum achado para remediar.</p>'
    return f"""
<h2 id="alertas">Alertas em linguagem simples (IA na remediação)</h2>
<div class="modo">{modo}</div>
<div class="alertas" style="margin-top:12px">{corpo}</div>"""


def _secao_codigo(dados: dict) -> str:
    blocos = []
    for a in dados["alvos"]:
        linhas = "".join(
            f'<tr><td><span class="tag {"vaz" if x["status"] == "ACHADO" else "san"}">'
            f'{"ACHADO" if x["status"] == "ACHADO" else "FICTÍCIO DECLARADO"}</span></td>'
            f'<td>{_e(x["rotulo"])}</td><td class="mono">{_e(x["trecho"])}</td>'
            f'<td class="mono">{_e(x["arquivo"])}:{x["linha"]}</td></tr>'
            for x in a["achados_codigo"])
        tabela = (f'<table><thead><tr><th>Status</th><th>Dado</th><th>Trecho (mascarado)</th><th>Local</th></tr></thead>'
                  f'<tbody>{linhas}</tbody></table>') if linhas else '<p class="sub">Nenhum dado pessoal escrito no código.</p>'
        blocos.append(f"<h3>{_e(a['alvo'])}</h3>{tabela}")
    return """
<h2 id="codigo">Dado pessoal escrito no código (motor PII)</h2>
<p class="sub">Segredos entram no índice. Dado pessoal escrito no código aparece aqui, fora do índice; os dados
fictícios declarados valem só por valor e arquivo juntos (seed e arquivo .http da API).</p>""" + "".join(blocos)


def _secao_runtime(dados: dict) -> str:
    rts = [(a["alvo"], a["runtime"]) for a in dados["alvos"] if a.get("runtime")]
    if not rts:
        return ""
    partes = ['<h2 id="runtime">Scanner de runtime (API em funcionamento)</h2>']
    for alvo, rt in rts:
        if not rt["no_ar"]:
            partes.append(f'<p class="sub">{_e(" ".join(rt["avisos"]))}</p>')
            continue
        linhas = "".join(
            f'<tr><td class="mono">GET {_e(r["rota"])}</td><td class="num">{r["status"]}</td>'
            f'<td class="num">{r["valores"]}</td><td class="num">{r["mascarados"]}</td><td class="num">{r["achados"]}</td></tr>'
            for r in rt["rotas"])
        achados = "".join(
            f'<tr><td><span class="tag {"ace" if x["status"] == "EXPOSICAO_ACEITA" else "vaz"}">'
            f'{"EXPOSIÇÃO ACEITA" if x["status"] == "EXPOSICAO_ACEITA" else "DADO INTEIRO"}</span></td>'
            f'<td>{_e(x["rotulo"])}</td><td class="mono">{_e(x["trecho"])}</td><td class="mono">{_e(x["contexto"])}</td></tr>'
            for x in rt["achados"])
        avisos = f'<p class="sub">{_e(" ".join(rt["avisos"]))}</p>' if rt["avisos"] else ""
        partes.append(f"""
<p class="sub">{_e(rt['url'])} · atribuído ao alvo <code>{_e(alvo)}</code> · {rt['mascarados']} valores já mascarados vistos nas respostas.</p>{avisos}
<table><thead><tr><th>Rota</th><th class="num">HTTP</th><th class="num">Valores lidos</th><th class="num">Mascarados</th>
<th class="num">Achados</th></tr></thead><tbody>{linhas}</tbody></table>
<details><summary>Achados nas respostas ({len(rt['achados'])})</summary>
<table><thead><tr><th>Status</th><th>Dado</th><th>Trecho</th><th>Rota · campo</th></tr></thead><tbody>{achados}</tbody></table></details>""")
    return "".join(partes)


def gerar(dados: dict) -> str:
    alvos = dados["alvos"]
    cartoes = "".join(_cartao_alvo(i, a) for i, a in enumerate(alvos))
    taint = []
    for a in alvos:
        vaz = [f for f in a["fluxos"] if f["status"] == "VAZAMENTO"]
        ace = [f for f in a["fluxos"] if f["status"] == "EXPOSICAO_ACEITA"]
        san = [f for f in a["fluxos"] if f["status"] == "SANITIZADO"]
        taint.append(f"""
<h3>{_e(a['alvo'])}</h3>
{_tabela_fluxos(vaz, 'Nenhum vazamento: todo dado sensível que chega a um sorvedouro passou por sanitizador.')}
<details><summary>Exposições aceitas ({len(ace)})</summary>{_tabela_fluxos(ace, 'Nenhuma.')}</details>
<details><summary>Fluxos sanitizados ({len(san)})</summary>{_tabela_fluxos(san, 'Nenhum.')}</details>""")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Luz Vital · Risco Cidadão</title>
<style>{CSS}</style>
</head>
<body>
<main>
<h1>Luz Vital · Índice de Risco Cidadão</h1>
<p class="sub">Gerado em {_e(dados['gerado_em'])} · <code>{_e(dados['comando'])}</code></p>
<p class="sub">Todos os dados das telas e do código são fictícios. Nenhum valor aparece inteiro neste relatório.</p>

<h2 id="comparacao">Comparação lado a lado</h2>
<div class="lado">{cartoes}</div>

{_secao_exposicoes(dados)}

<h2 id="categorias">Vazamentos por categoria</h2>
<p class="sub">Defeitos únicos que entram no índice. Saúde pesa o dobro na conta.</p>
<div class="cartao">{_grafico_categorias(alvos)}</div>

{_secao_alertas(dados)}

<h2 id="taint">Fluxos do taint analysis</h2>
<p class="sub">Da fonte (onde o dado sensível entra) ao sorvedouro (log, exceção, resposta HTTP, notificação).</p>
{''.join(taint)}

{_secao_codigo(dados)}
{_secao_runtime(dados)}

<h2 id="formula">Como o índice é calculado</h2>
<div class="cartao"><pre class="mono" style="margin:0;white-space:pre-wrap">{_e(dados['formula'])}</pre></div>

<footer>Luz Vital · Global Solution FIAP 2026 · módulo cyber/</footer>
</main>
</body>
</html>"""
