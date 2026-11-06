"""Motor de regras PII da Luz Vital.

Cada regra tem nome, regex, severidade (1 a 5) e categoria. A função `encontrar`
recebe um texto e devolve os achados com o trecho JÁ MASCARADO: o valor inteiro
nunca sai deste módulo, nem para o relatório, nem para a IA.

Regras:
    cpf          CPF com dígito verificador válido (não pega qualquer número de 11 dígitos)
    telefone     telefone BR, fixo ou celular, com ou sem DDD formatado
    email        endereço de e-mail
    cep          CEP 00000-000 (ou "CEP 00000000")
    endereco     logradouro + número ("Rua X, 100", "Av. Y 2000")
    saude        termos de saúde: oxigênio, insulina e os nomes do enum TipoDependencia
    cid10        código CID-10 no formato A00.0
    senha        connection string com senha, password=..., pwd=...
    chave_api    chaves de API conhecidas e api_key=/secret=/token= com valor longo

Valores já mascarados (529.***.***-25, (11) *****-0001) são reconhecidos e
devolvidos à parte, como prova de que a máscara funcionou. Não contam como vazamento.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field
from typing import Callable

from cyber import csharp
from cyber.pii.ficticios import eh_ficticio

IDENTIFICACAO = "identificação"
CONTATO = "contato"
LOCALIZACAO = "localização"
SAUDE = "saúde"
SEGREDO = "segredo"
CATEGORIAS = [IDENTIFICACAO, CONTATO, LOCALIZACAO, SAUDE, SEGREDO]

# Status de um achado
ACHADO = "ACHADO"
FICTICIO = "FICTICIO_DECLARADO"
EXPOSICAO_ACEITA = "EXPOSICAO_ACEITA"


# ---------------------------------------------------------------- validação e máscara

def _digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor)


def cpf_valido(valor: str) -> bool:
    """Mesmo algoritmo do Cpf.EhValido da API: 11 dígitos, não repetidos, DVs corretos."""
    cpf = _digitos(valor)
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return False

    def dv(numeros: str, tamanho: int) -> int:
        soma = sum(int(numeros[i]) * (tamanho + 1 - i) for i in range(tamanho))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    return int(cpf[9]) == dv(cpf, 9) and int(cpf[10]) == dv(cpf, 10)


def _mask_cpf(v: str) -> str:
    d = _digitos(v)
    return f"{d[:3]}.***.***-{d[9:]}"


def _mask_telefone(v: str) -> str:
    d = _digitos(v)
    if d.startswith("55") and len(d) > 11:
        d = d[2:]
    return f"({d[:2]}) *****-{d[-4:]}"


def _mask_email(v: str) -> str:
    usuario, _, dominio = v.partition("@")
    return f"{usuario[:1]}***@{dominio}"


def _mask_cep(v: str) -> str:
    d = _digitos(v)
    return f"{d[:2]}***-***"


def _mask_endereco(v: str) -> str:
    return f"{v.split()[0]} ***, nº ***"


def _mask_termo(v: str) -> str:
    return f"{v[:3]}***"


def _mask_cid(v: str) -> str:
    return f"{v[0]}**.*"


def _mask_segredo(v: str) -> str:
    m = re.match(r"\s*([A-Za-z_\-]+)\s*[:=]", v)
    if m:
        return f"{m.group(1)}=***"
    return f"{v[:6]}***"


# ---------------------------------------------------------------- regras

@dataclass(frozen=True)
class Regra:
    nome: str
    rotulo: str
    padrao: re.Pattern
    severidade: int
    categoria: str
    mascarar: Callable[[str], str]
    validar: Callable[[str], bool] | None = None
    so_em_strings_no_cs: bool = False  # nos .cs, só procura dentro de strings e comentários


_ENUM_DEPENDENCIA = ["OxigenioDomiciliar", "MedicamentoRefrigerado", "CadeiraMotorizada", "AcamadoComEquipamento"]

REGRAS: list[Regra] = [
    Regra(
        "cpf", "CPF",
        re.compile(r"(?<![\d*])\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?![\d*])"),
        5, IDENTIFICACAO, _mask_cpf, validar=cpf_valido,
    ),
    Regra(
        "telefone", "Telefone",
        re.compile(r"(?<![\d*])(?:\+?55[\s-]?)?\(?[1-9][1-9]\)?[\s-]?(?:9\d{4}|[2-5]\d{3})[\s-]?\d{4}(?![\d*])"),
        4, CONTATO, _mask_telefone,
    ),
    Regra(
        "email", "E-mail",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        3, CONTATO, _mask_email,
    ),
    Regra(
        "cep", "CEP",
        re.compile(r"(?<![\d-])\d{5}-\d{3}(?![\d-])|(?i:\bCEP:?\s*)\d{8}\b"),
        2, LOCALIZACAO, _mask_cep,
    ),
    Regra(
        "endereco", "Endereço",
        re.compile(
            r"\b(?:Rua|R\.|Avenida|Av\.|Alameda|Al\.|Travessa|Tv\.|Estrada|Rodovia|Praça)"
            r"\s+[A-Za-zÀ-ÿ0-9'. ]{2,60}?,?\s*(?:n[º°o]\.?\s*)?\d{1,5}\b"
        ),
        4, LOCALIZACAO, _mask_endereco,
    ),
    Regra(
        "saude", "Dado de saúde",
        re.compile(
            r"(?i)\b(?:" + "|".join(_ENUM_DEPENDENCIA) +
            r"|concentrador de oxig[eê]nio|oxig[eê]nio|insulina|acamad[oa]s?|di[aá]lise)\b"
        ),
        4, SAUDE, _mask_termo, so_em_strings_no_cs=True,
    ),
    Regra(
        "cid10", "CID-10",
        re.compile(r"\b[A-TV-Z]\d{2}\.\d\b"),
        4, SAUDE, _mask_cid, so_em_strings_no_cs=True,
    ),
    Regra(
        "senha", "Senha em connection string",
        re.compile(r"(?i)\b(?:password|pwd)\s*=\s*[\"']?(?!\*)[^;\"'\s]+"),
        5, SEGREDO, _mask_segredo,
    ),
    Regra(
        "chave_api", "Chave de API",
        re.compile(
            r"\b(?:sk-ant-[A-Za-z0-9_\-]{16,}|sk-[A-Za-z0-9]{32,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}"
            r"|AIza[0-9A-Za-z_\-]{35})"
            r"|(?i:\b(?:api[_-]?key|apikey|secret|access[_-]?token)\b)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{16,}"
        ),
        5, SEGREDO, _mask_segredo,
    ),
]

REGRAS_POR_NOME = {r.nome: r for r in REGRAS}

MASCARADOS = [
    ("cpf", re.compile(r"\d{3}\.\*{3}\.\*{3}-\d{2}")),
    ("telefone", re.compile(r"\(\d{2}\)\s?\*{4,5}-\d{4}")),
]


# ---------------------------------------------------------------- achados

@dataclass
class Achado:
    regra: str
    rotulo: str
    categoria: str
    severidade: int
    trecho: str  # sempre mascarado
    linha: int
    coluna: int
    inicio: int
    fim: int
    arquivo: str | None = None
    contexto: str | None = None  # ex.: endpoint e campo JSON no scanner de runtime
    status: str = ACHADO
    motivo: str | None = None

    def para_dict(self) -> dict:
        return asdict(self)


@dataclass
class Resultado:
    achados: list[Achado] = field(default_factory=list)
    mascarados: list[dict] = field(default_factory=list)  # valores que já saíram mascarados


def encontrar(texto: str, arquivo: str | None = None, contexto: str | None = None) -> Resultado:
    """Procura dado pessoal no texto. Devolve achados mascarados e os valores já mascarados.

    Se `arquivo` termina em .cs, as regras de saúde só valem dentro de strings e
    comentários (senão cada `TipoDependencia.OxigenioDomiciliar` do código viraria achado).
    """
    eh_cs = bool(arquivo and arquivo.endswith(".cs"))
    dentro_de_string = None
    if eh_cs:
        lista = csharp.trechos(texto)
        dentro_de_string = [False] * len(texto)
        for t in lista:
            for k in range(t.inicio, t.fim):
                dentro_de_string[k] = True

    resultado = Resultado()

    ocupado: list[tuple[int, int]] = []
    for tipo, padrao in MASCARADOS:
        for m in padrao.finditer(texto):
            ocupado.append(m.span())
            resultado.mascarados.append({
                "tipo": tipo, "trecho": m.group(0), "linha": csharp.linha_de(texto, m.start()),
                "arquivo": arquivo, "contexto": contexto,
            })

    candidatos: list[tuple[Regra, re.Match]] = []
    for regra in REGRAS:
        for m in regra.padrao.finditer(texto):
            valor = m.group(0)
            if regra.validar and not regra.validar(valor):
                continue
            if regra.so_em_strings_no_cs and dentro_de_string is not None:
                if not all(dentro_de_string[k] for k in range(m.start(), m.end())):
                    continue
            if any(a < m.end() and m.start() < b for a, b in ocupado):
                continue
            candidatos.append((regra, m))

    # Sobreposição: fica a regra mais grave (um CPF sem pontuação também casa com telefone).
    candidatos.sort(key=lambda c: (-c[0].severidade, -(c[1].end() - c[1].start()), c[1].start()))
    escolhidos: list[tuple[Regra, re.Match]] = []
    for regra, m in candidatos:
        if any(m.start() < e.end() and e.start() < m.end() for _, e in escolhidos):
            continue
        escolhidos.append((regra, m))
    escolhidos.sort(key=lambda c: c[1].start())

    for regra, m in escolhidos:
        valor = m.group(0)
        inicio_linha = texto.rfind("\n", 0, m.start()) + 1
        achado = Achado(
            regra=regra.nome, rotulo=regra.rotulo, categoria=regra.categoria, severidade=regra.severidade,
            trecho=regra.mascarar(valor), linha=csharp.linha_de(texto, m.start()),
            coluna=m.start() - inicio_linha + 1, inicio=m.start(), fim=m.end(),
            arquivo=arquivo, contexto=contexto,
        )
        if eh_ficticio(regra.nome, valor, arquivo):
            achado.status = FICTICIO
            achado.motivo = "Dado fictício declarado (seed e arquivo de exemplo da API)."
        resultado.achados.append(achado)
    return resultado


# ---------------------------------------------------------------- varredura de pasta

EXTENSOES = {".cs", ".json", ".http", ".xml", ".config", ".yml", ".yaml", ".env", ".txt", ".md", ".csproj"}
PASTAS_IGNORADAS = {"bin", "obj", ".vs", ".git", "node_modules", "__pycache__", ".venv"}


def arquivos_do_alvo(alvo: str) -> list[str]:
    encontrados = []
    for raiz, pastas, nomes in os.walk(alvo):
        pastas[:] = sorted(p for p in pastas if p not in PASTAS_IGNORADAS)
        for nome in sorted(nomes):
            if os.path.splitext(nome)[1].lower() in EXTENSOES:
                encontrados.append(os.path.join(raiz, nome))
    return encontrados


def varrer(alvo: str, base: str | None = None) -> Resultado:
    """Passa o motor em todos os arquivos de texto do alvo. Caminhos saem relativos a `base`."""
    total = Resultado()
    for caminho in arquivos_do_alvo(alvo):
        with open(caminho, encoding="utf-8-sig", errors="replace") as f:
            texto = f.read()
        nome = os.path.relpath(caminho, base).replace("\\", "/") if base else caminho.replace("\\", "/")
        parcial = encontrar(texto, arquivo=nome)
        total.achados.extend(parcial.achados)
        total.mascarados.extend(parcial.mascarados)
    return total
