"""Taint analysis estático, baseado em texto, para os .cs da API.

Como funciona
-------------
1. Cada .cs vira uma lista de métodos (com classe, parâmetros e corpo). Comentários
   são apagados antes; strings são respeitadas para não confundir '{', '}' e ';'.
2. O corpo de cada método é quebrado em comandos (por ';', '{' e '}' fora de
   parênteses e de strings) e percorrido em ordem, guardando quais variáveis estão
   contaminadas e por quais campos (Cpf, Telefone, Endereco, Dependencia).
3. Cada expressão é avaliada em camadas:
      a. `.Select(...)` no fim da cadeia: o resultado é só o que o Select projeta;
      b. sanitizadores (Cpf.Mascarar, Mascara.*): o que passa por eles sai SANITIZADO;
      c. chamadas a métodos com resumo (ver abaixo);
      d. `new Tipo(...)` / `new { ... }`: o que entra nos argumentos sai no objeto;
      e. identificadores: `x.Cpf` dá o campo Cpf de x; `x` sozinho dá todos os campos;
         `x.Where(...)`/`x.ToList()` passam tudo adiante; `x.Id`, `x.Nome()` não passam nada.
4. Quando um comando contém um sorvedouro, os argumentos dele são avaliados e cada
   campo que chega vira um fluxo: SANITIZADO, VAZAMENTO ou EXPOSICAO_ACEITA (excecoes.json).

Resumo de método
----------------
A regra é seguir o dado dentro do mesmo método. Para os DTOs funcionarem como
sanitizadores, e para o painel (o dado nasce no serviço e sai no controller), há um
passo a mais: antes da análise final, cada método ganha um "resumo" do que ele devolve
(campo por campo, cru ou mascarado). Uma chamada `CidadaoResponse.De(c)` usa esse resumo.
O resumo é por nome (Classe.Metodo, ou só Metodo quando é único), não por tipo: é uma
aproximação, documentada como tal.

Limites conhecidos
------------------
- Não resolve tipos, herança, sobrecarga nem injeção de dependência.
- Não segue o dado por campos de classe, eventos ou banco de dados.
- Método chamado sem resumo passa adiante o que recebeu (postura conservadora).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field, replace

from cyber import csharp
from cyber.pii.regras import REGRAS_POR_NOME
from cyber.taint import config as cfg

SANITIZADO = "SANITIZADO"
VAZAMENTO = "VAZAMENTO"
EXPOSICAO_ACEITA = "EXPOSICAO_ACEITA"

CAMINHO_EXCECOES = os.path.join(os.path.dirname(__file__), "excecoes.json")


# ---------------------------------------------------------------- estruturas

@dataclass(frozen=True)
class Marca:
    """Um campo sensível dentro de uma variável ou expressão."""
    campo: str
    sanitizado: bool
    fonte_arquivo: str
    fonte_linha: int
    caminho: tuple[str, ...]
    param: bool = False  # veio de um parâmetro do método (usado nos resumos)
    ponto: str | None = None  # onde o dado cru escapou (DTO que expõe o campo)


@dataclass
class Metodo:
    arquivo: str
    classe: str
    nome: str
    params: list[tuple[str, str]]
    linha: int
    corpo_inicio: int
    corpo_fim: int
    expressao: bool  # corpo "=> expr;"
    texto: str  # arquivo inteiro, sem comentários
    em_string: list[bool]

    @property
    def rotulo(self) -> str:
        return f"{self.classe}.{self.nome}"


@dataclass
class Resumo:
    metodo: Metodo
    marcas: list[Marca]
    eh_dto: bool


@dataclass
class Fluxo:
    campo: str
    regra: str
    rotulo: str
    categoria: str
    severidade: int
    fonte: str  # arquivo:linha
    sorvedouro: str  # arquivo:linha
    tipo_sorvedouro: str
    chamada: str
    metodo: str
    caminho: list[str]
    status: str
    ponto: str  # unidade de deduplicação do índice
    excecao: str | None = None

    def para_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------- utilidades de texto

def _casar(texto: str, i: int, em_string: list[bool] | None = None) -> int:
    """i aponta para '(', '[' ou '{'. Devolve o índice do fechamento correspondente."""
    pares = {"(": ")", "[": "]", "{": "}"}
    abre = texto[i]
    fecha = pares[abre]
    prof = 0
    n = len(texto)
    k = i
    while k < n:
        if em_string is not None and em_string[k]:
            k += 1
            continue
        c = texto[k]
        if c == abre:
            prof += 1
        elif c == fecha:
            prof -= 1
            if prof == 0:
                return k
        k += 1
    return n - 1


def _mascara_local(expr: str) -> list[bool]:
    return csharp.mascara_de_strings(expr)


def _dividir_args(texto: str) -> list[str]:
    """Divide por vírgulas de nível 0 (fora de (), [], {}, <> e strings)."""
    em_str = _mascara_local(texto)
    partes, atual, prof = [], [], 0
    for k, c in enumerate(texto):
        if not em_str[k]:
            if c in "([{":
                prof += 1
            elif c in ")]}":
                prof -= 1
            elif c == "<" and re.match(r"<\s*[\w.,\s<>?\[\]]*>", texto[k:]):
                prof += 1
            elif c == ">" and prof > 0 and k > 0 and texto[k - 1] != "=":
                prof -= 1
            elif c == "," and prof == 0:
                partes.append("".join(atual))
                atual = []
                continue
        atual.append(c)
    if atual and "".join(atual).strip():
        partes.append("".join(atual))
    return [p.strip() for p in partes]


def _apagar_strings_simples(expr: str) -> str:
    """Troca o conteúdo de strings comuns por espaços (strings $"..." ficam: têm código dentro)."""
    saida = list(expr)
    for t in csharp.trechos(expr):
        if t.tipo == "string" and expr[t.inicio] != "$" and expr[t.inicio:t.inicio + 2] not in ("@$",):
            for k in range(t.inicio, t.fim):
                saida[k] = " "
    return "".join(saida)


def _tipo_fonte(tipo: str) -> str | None:
    for palavra in re.findall(r"\w+", tipo):
        if palavra in cfg.FONTES_TIPOS:
            return palavra
    return None


# ---------------------------------------------------------------- leitura dos arquivos

_RE_TIPO = re.compile(r"\b(class|record|struct|interface)\s+(\w+)")
_RE_METODO = re.compile(
    r"^[ \t]*(?:\[[^\]\n]*\][ \t]*)*"
    r"((?:(?:public|private|protected|internal|static|async|override|virtual|sealed|abstract|partial|new"
    r"|extern|unsafe|readonly)\s+)+)"
    r"([^=;{}()\n]*?)\b(\w+)\s*(?:<[^>()]*>)?\s*\(",
    re.MULTILINE,
)


def _tipos(texto: str, em_string: list[bool]) -> list[tuple[str, int, int]]:
    tipos = []
    for m in _RE_TIPO.finditer(texto):
        if em_string[m.start()]:
            continue
        k, prof = m.end(), 0
        while k < len(texto):
            c = texto[k]
            if not em_string[k]:
                if c in "([":
                    prof += 1
                elif c in ")]":
                    prof -= 1
                elif prof == 0 and c == "{":
                    tipos.append((m.group(2), m.start(), _casar(texto, k, em_string)))
                    break
                elif prof == 0 and c == ";":
                    tipos.append((m.group(2), m.start(), k))
                    break
            k += 1
    return tipos


def ler_metodos(caminho: str, nome_relativo: str) -> list[Metodo]:
    with open(caminho, encoding="utf-8-sig", errors="replace") as f:
        original = f.read()
    lista = csharp.trechos(original)
    texto = csharp.apagar_comentarios(original, lista)
    em_string = csharp.mascara_de_strings(texto, lista)
    tipos = _tipos(texto, em_string)

    metodos = []
    for m in _RE_METODO.finditer(texto):
        retorno, nome = m.group(2).strip(), m.group(3)
        if em_string[m.start(3)] or nome in cfg.PALAVRAS_RESERVADAS:
            continue
        ultima = retorno.split()[-1] if retorno.split() else ""
        if ultima in {"class", "record", "struct", "interface", "enum", "delegate", "event"}:
            continue
        abre = m.end() - 1
        fecha = _casar(texto, abre, em_string)
        params_txt = texto[abre + 1:fecha]
        k = fecha + 1
        # pula ": base(...)", ": this(...)" e "where T : ..."
        resto = texto[k:]
        m2 = re.match(r"\s*(?::\s*(?:base|this)\s*\([^)]*\)|where\s+[^{=]*)?\s*", resto)
        k += m2.end() if m2 else 0
        if texto.startswith("=>", k):
            inicio = k + 2
            fim = inicio
            prof = 0
            while fim < len(texto):
                c = texto[fim]
                if not em_string[fim]:
                    if c in "([{":
                        prof += 1
                    elif c in ")]}":
                        prof -= 1
                    elif c == ";" and prof == 0:
                        break
                fim += 1
            expressao = True
        elif k < len(texto) and texto[k] == "{":
            inicio, fim, expressao = k, _casar(texto, k, em_string), False
        else:
            continue  # declaração sem corpo (interface, abstract)

        classe = "?"
        menor = None
        for nome_tipo, ini, fim_tipo in tipos:
            if ini <= m.start() <= fim_tipo and (menor is None or fim_tipo - ini < menor):
                classe, menor = nome_tipo, fim_tipo - ini

        params = []
        for p in _dividir_args(params_txt):
            p = re.sub(r"\[[^\]]*\]", " ", p)
            p = p.split("=")[0].strip()
            p = re.sub(r"^(?:this|ref|out|in|params)\s+", "", p)
            partes = p.split()
            if len(partes) >= 2:
                params.append((" ".join(partes[:-1]), partes[-1]))

        metodos.append(Metodo(
            arquivo=nome_relativo, classe=classe, nome=nome, params=params,
            linha=csharp.linha_de(texto, m.start(3)), corpo_inicio=inicio, corpo_fim=fim,
            expressao=expressao, texto=texto, em_string=em_string,
        ))
    return metodos


def _comandos(metodo: Metodo) -> list[tuple[int, str]]:
    """Quebra o corpo em comandos. Devolve (posição no arquivo, texto)."""
    texto, em_str = metodo.texto, metodo.em_string
    if metodo.expressao:
        return [(metodo.corpo_inicio, "return " + texto[metodo.corpo_inicio:metodo.corpo_fim])]
    comandos, inicio, prof = [], metodo.corpo_inicio + 1, 0
    for k in range(metodo.corpo_inicio + 1, metodo.corpo_fim):
        c = texto[k]
        if em_str[k]:
            continue
        if c in "([":
            prof += 1
        elif c in ")]":
            prof -= 1
        elif prof == 0 and c in ";{}":
            trecho = texto[inicio:k]
            if trecho.strip():
                desloc = len(trecho) - len(trecho.lstrip())
                comandos.append((inicio + desloc, trecho.strip()))
            inicio = k + 1
    trecho = texto[inicio:metodo.corpo_fim]
    if trecho.strip():
        comandos.append((inicio, trecho.strip()))
    return comandos


# ---------------------------------------------------------------- analisador

class Analisador:
    def __init__(self, metodos: list[Metodo], excecoes: list[dict] | None = None):
        self.metodos = metodos
        self.resumos: dict[str, Resumo] = {}
        self.excecoes = excecoes if excecoes is not None else carregar_excecoes()["excecoes"]
        self._nomes_unicos: dict[str, str] = {}

    # -------- resumo

    def _resumo(self, qualificador: str | None, nome: str) -> Resumo | None:
        if qualificador and f"{qualificador}.{nome}" in self.resumos:
            return self.resumos[f"{qualificador}.{nome}"]
        chave = self._nomes_unicos.get(nome)
        return self.resumos.get(chave) if chave else None

    def _aplicar_resumo(self, resumo: Resumo, entrada: list[Marca]) -> list[Marca]:
        m = resumo.metodo
        rotulo = f"{m.rotulo} ({m.arquivo}:{m.linha})"
        saida: list[Marca] = []
        for r in resumo.marcas:
            if r.param:
                for a in entrada:
                    if a.campo != r.campo:
                        continue
                    sanitizado = a.sanitizado or r.sanitizado
                    ponto = a.ponto
                    if resumo.eh_dto and not sanitizado:
                        ponto = rotulo
                    saida.append(replace(
                        a, sanitizado=sanitizado, caminho=a.caminho + (rotulo,) + r.caminho, ponto=ponto,
                    ))
            else:
                saida.append(replace(r, caminho=r.caminho + (rotulo,)))
        if resumo.eh_dto:
            expostos = {r.campo for r in resumo.marcas if r.param}
            for a in entrada:
                if a.campo not in expostos and not a.sanitizado:
                    saida.append(replace(a, sanitizado=True, caminho=a.caminho + (f"{rotulo}: campo não exposto",)))
        return saida

    # -------- avaliação de expressões

    def avaliar(self, expr: str, estado: dict[str, list[Marca]], metodo: Metodo, linha: int) -> list[Marca]:
        expr = expr.strip()
        if not expr:
            return []

        sel = self._ultimo_select(expr)
        if sel:
            receptor, arg = sel
            entrada = self.avaliar(receptor, estado, metodo, linha)
            lam = re.match(r"^\(?\s*(\w+)\s*\)?\s*=>\s*(.*)$", arg, re.S)
            if lam:
                filho = dict(estado)
                filho[lam.group(1)] = [replace(x, caminho=x.caminho + (lam.group(1),)) for x in entrada]
                return self.avaliar(lam.group(2), filho, metodo, linha)
            grupo = re.fullmatch(r"\s*(?:(\w+)\s*\.\s*)?(\w+)\s*", arg)
            if grupo:
                resumo = self._resumo(grupo.group(1), grupo.group(2))
                if resumo:
                    return self._aplicar_resumo(resumo, entrada)
            return entrada

        marcas: list[Marca] = []
        texto = _apagar_strings_simples(expr)

        def apagar(t: str, a: int, b: int) -> str:
            return t[:a] + " " * (b - a) + t[b:]

        # b. sanitizadores
        while True:
            m = cfg.SANITIZADORES.search(texto)
            if not m:
                break
            fecha = _casar(texto, m.end() - 1)
            for x in self.avaliar(texto[m.end():fecha], estado, metodo, linha):
                marcas.append(replace(x, sanitizado=True, caminho=x.caminho + (m.group(1),)))
            texto = apagar(texto, m.start(), fecha + 1)

        # c. chamadas com resumo
        pos = 0
        while True:
            m = re.compile(r"(?:\b(\w+)\s*\.\s*)?\b(\w+)\s*\(").search(texto, pos)
            if not m:
                break
            resumo = None
            if m.group(2) not in cfg.PALAVRAS_RESERVADAS and m.group(2) not in cfg.PASSA_ADIANTE:
                resumo = self._resumo(m.group(1), m.group(2))
            if resumo is None or resumo.metodo is metodo:
                pos = m.end()
                continue
            fecha = _casar(texto, m.end() - 1)
            entrada = self.avaliar(texto[m.end():fecha], estado, metodo, linha)
            marcas.extend(self._aplicar_resumo(resumo, entrada))
            texto = apagar(texto, m.start(), fecha + 1)

        # d. new Tipo(...) / new Tipo { ... } / new { ... }
        while True:
            m = re.search(r"\bnew\s*(\w*)\s*(?:<[^>()]*>)?\s*([({])", texto)
            if not m:
                break
            fecha = _casar(texto, m.end() - 1)
            nome = m.group(1) or ""
            passo = f"new {nome}(...)" if nome else "new(...)"
            if "Exception" in nome:
                passo = f"new {nome}(...)"
            argumentos = self.avaliar(texto[m.end():fecha], estado, metodo, linha)
            for x in argumentos:
                marcas.append(replace(x, caminho=x.caminho + (passo,)))
            # `new Cidadao(...)` também é fonte: o objeto novo carrega todos os campos.
            # Se o campo já veio rastreado pelos argumentos (ex.: req.Cpf), vale o rastro mais antigo.
            if nome in ("Cidadao", "Voluntario"):
                ja_vieram = {x.campo for x in argumentos}
                for campo in cfg.FONTES_TIPOS[nome]:
                    if campo not in ja_vieram:
                        marcas.append(Marca(campo, False, metodo.arquivo, linha, (f"new {nome}(...)",)))
            texto = apagar(texto, m.start(), fecha + 1)

        # e. identificadores
        eh_classe_fonte = metodo.classe in cfg.FONTES_TIPOS
        for m in re.finditer(r"(?<![\w.])(this\s*\.\s*)?([A-Za-z_]\w*)((?:\s*\??\.\s*\w+)*)", texto):
            nome = m.group(2)
            membros = re.findall(r"\w+", m.group(3) or "")
            if m.group(1) is None and nome in estado:
                origem = estado[nome]
                if not membros:
                    marcas.extend(origem)
                elif membros[0] in cfg.CAMPOS:
                    for x in origem:
                        if x.campo == membros[0]:
                            passo = f"{nome}.{membros[0]}"
                            cam = x.caminho[:-1] + (passo,) if x.caminho and x.caminho[-1] == nome else x.caminho + (passo,)
                            marcas.append(replace(x, caminho=cam))
                elif membros[0] in cfg.PASSA_ADIANTE:
                    marcas.extend(origem)
                continue
            if membros and membros[0] in cfg.COLECOES and nome in ("_db", "db", "_context", "context"):
                tipo = cfg.COLECOES[membros[0]]
                for campo in cfg.FONTES_TIPOS[tipo]:
                    marcas.append(Marca(campo, False, metodo.arquivo, linha, (f"{nome}.{membros[0]}",)))
                continue
            if eh_classe_fonte and nome in cfg.FONTES_TIPOS[metodo.classe] and (m.group(1) or not membros or membros[0] not in ("Mascarar", "SomenteDigitos", "EhValido", "ComDigitos")):
                if m.group(1) or not membros:
                    marcas.append(Marca(nome, False, metodo.arquivo, linha, (f"{metodo.classe}.{nome}",)))
        return _unicas(marcas)

    def _ultimo_select(self, expr: str) -> tuple[str, str] | None:
        """Acha o último `.Select(` de nível 0. Devolve (receptor, argumento)."""
        em_str = _mascara_local(expr)
        prof, achado = 0, None
        for k, c in enumerate(expr):
            if em_str[k]:
                continue
            if c in "([{":
                prof += 1
            elif c in ")]}":
                prof -= 1
            elif c == "." and prof == 0:
                m = re.match(r"\.\s*(Select|SelectMany)\s*\(", expr[k:])
                if m:
                    achado = (k, k + m.end() - 1)
        if not achado:
            return None
        ponto, abre = achado
        fecha = _casar(expr, abre, em_str)
        return expr[:ponto], expr[abre + 1:fecha]

    # -------- análise de um método

    def analisar_metodo(self, metodo: Metodo, coletar: bool) -> tuple[list[Marca], list[Fluxo]]:
        estado: dict[str, list[Marca]] = {}
        for tipo, nome in metodo.params:
            base = _tipo_fonte(tipo)
            if base:
                estado[nome] = [
                    Marca(campo, False, metodo.arquivo, metodo.linha, (f"parâmetro {nome} ({base})",), param=True)
                    for campo in cfg.FONTES_TIPOS[base]
                ]

        retornos: list[Marca] = []
        fluxos: list[Fluxo] = []
        for pos, cmd in _comandos(metodo):
            linha = csharp.linha_de(metodo.texto, pos)
            sem_str = _apagar_strings_simples(cmd)

            for m in re.finditer(r"\b(\w+)\s+is\s+(\w+)\s+(\w+)\b", sem_str):
                if m.group(1) in estado and m.group(2) in cfg.FONTES_TIPOS:
                    base = estado[m.group(1)][0] if estado[m.group(1)] else None
                    if base:
                        estado[m.group(3)] = [
                            replace(base, campo=c, caminho=base.caminho + (f"{m.group(1)} is {m.group(2)} {m.group(3)}",))
                            for c in cfg.FONTES_TIPOS[m.group(2)]
                        ]

            fe = re.match(r"foreach\s*\(\s*(?:var|[\w<>?,\[\]\s]+?)\s+(\w+)\s+in\s+(.+)\)\s*$", cmd, re.S)
            if fe:
                estado[fe.group(1)] = [replace(x, caminho=x.caminho + (fe.group(1),))
                                       for x in self.avaliar(fe.group(2), estado, metodo, linha)]
                continue

            if coletar:
                fluxos.extend(self._sorvedouros(cmd, pos, estado, metodo))

            if re.match(r"return\b", cmd):
                retornos.extend(self.avaliar(cmd[6:], estado, metodo, linha))
                continue

            igual = _atribuicao(cmd)
            if igual is not None:
                lado_esq, lado_dir = cmd[:igual], cmd[igual + 1:]
                if lado_esq.rstrip().endswith((")", "]")):
                    continue
                nomes = re.findall(r"\w+", lado_esq)
                if nomes:
                    alvo = nomes[-1]
                    valor = self.avaliar(lado_dir, estado, metodo, linha)
                    estado[alvo] = [replace(x, caminho=x.caminho + (alvo,)) for x in valor]
        return _unicas(retornos), fluxos

    def _sorvedouros(self, cmd: str, pos: int, estado, metodo: Metodo) -> list[Fluxo]:
        fluxos = []
        em_str = _mascara_local(cmd)
        for tipo, padrao, indices in cfg.SORVEDOUROS:
            for m in padrao.finditer(cmd):
                if em_str[m.start()]:
                    continue
                abre = m.end() - 1
                fecha = _casar(cmd, abre, em_str)
                args = _dividir_args(cmd[abre + 1:fecha])
                if indices is not None:
                    args = [args[i] for i in indices if i < len(args)]
                linha = csharp.linha_de(metodo.texto, pos + m.start())
                chamada = re.sub(r"\s+", "", cmd[m.start():abre]).lstrip(".")
                local = f"{metodo.arquivo}:{linha}"
                for x in self.avaliar(", ".join(args), estado, metodo, linha):
                    fluxos.append(self._fluxo(x, tipo, chamada, local, metodo))
        return fluxos

    def _fluxo(self, x: Marca, tipo: str, chamada: str, local: str, metodo: Metodo) -> Fluxo:
        regra = REGRAS_POR_NOME[cfg.CAMPO_REGRA[x.campo]]
        caminho: list[str] = []
        for passo in list(x.caminho) + [f"{chamada}(...) [{tipo}]"]:
            if not caminho or caminho[-1] != passo:  # "query -> query" vira um passo só
                caminho.append(passo)
        status = SANITIZADO if x.sanitizado else VAZAMENTO
        excecao = None
        if status == VAZAMENTO:
            for e in self.excecoes:
                if e["campo"] == x.campo and any(e["via"] in passo for passo in caminho):
                    status, excecao = EXPOSICAO_ACEITA, e["id"]
                    break
        return Fluxo(
            campo=x.campo, regra=regra.nome, rotulo=regra.rotulo, categoria=regra.categoria,
            severidade=regra.severidade, fonte=f"{x.fonte_arquivo}:{x.fonte_linha}", sorvedouro=local,
            tipo_sorvedouro=tipo, chamada=chamada, metodo=metodo.rotulo, caminho=caminho, status=status,
            ponto=x.ponto or local, excecao=excecao,
        )

    # -------- tudo

    def executar(self) -> list[Fluxo]:
        contagem: dict[str, list[str]] = {}
        for m in self.metodos:
            contagem.setdefault(m.nome, []).append(m.rotulo)
        self._nomes_unicos = {nome: rotulos[0] for nome, rotulos in contagem.items() if len(set(rotulos)) == 1}

        for _ in range(3):  # ponto fixo: resumos que dependem de outros resumos
            for m in self.metodos:
                retornos, _f = self.analisar_metodo(m, coletar=False)
                tem_param_fonte = any(_tipo_fonte(t) for t, _n in m.params)
                if retornos or tem_param_fonte:
                    self.resumos[m.rotulo] = Resumo(m, retornos, eh_dto=m.classe.endswith("Response"))

        fluxos: list[Fluxo] = []
        vistos = set()
        for m in self.metodos:
            _r, achados = self.analisar_metodo(m, coletar=True)
            for f in achados:
                chave = (f.campo, f.fonte, f.sorvedouro, f.status, tuple(f.caminho))
                if chave not in vistos:
                    vistos.add(chave)
                    fluxos.append(f)
        fluxos.sort(key=lambda f: ({VAZAMENTO: 0, EXPOSICAO_ACEITA: 1, SANITIZADO: 2}[f.status], f.sorvedouro))
        return fluxos


def _atribuicao(cmd: str) -> int | None:
    """Posição do '=' de atribuição de nível 0 (ignora ==, =>, <=, >=, != e o que está entre parênteses)."""
    em_str = _mascara_local(cmd)
    prof = 0
    for k, c in enumerate(cmd):
        if em_str[k]:
            continue
        if c in "([{":
            prof += 1
        elif c in ")]}":
            prof -= 1
        elif c == "=" and prof == 0:
            antes = cmd[k - 1] if k else ""
            depois = cmd[k + 1] if k + 1 < len(cmd) else ""
            if depois in "=>" or antes in "=!<>+-*/%&|^?":
                continue
            return k
    return None


def _unicas(marcas: list[Marca]) -> list[Marca]:
    vistas, saida = set(), []
    for x in marcas:
        if x not in vistas:
            vistas.add(x)
            saida.append(x)
    return saida


def carregar_excecoes() -> dict:
    with open(CAMINHO_EXCECOES, encoding="utf-8") as f:
        return json.load(f)


def analisar(alvo: str, base: str | None = None) -> list[Fluxo]:
    """Roda o taint em todos os .cs do alvo (fora bin/ e obj/)."""
    metodos: list[Metodo] = []
    for raiz, pastas, nomes in os.walk(alvo):
        pastas[:] = sorted(p for p in pastas if p not in {"bin", "obj", ".vs", "Migrations"})
        for nome in sorted(nomes):
            if nome.endswith(".cs"):
                caminho = os.path.join(raiz, nome)
                rel = os.path.relpath(caminho, base) if base else caminho
                metodos.extend(ler_metodos(caminho, rel.replace("\\", "/")))
    return Analisador(metodos).executar()
