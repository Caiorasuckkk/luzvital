"""Leitura léxica mínima de C#: onde estão as strings e os comentários.

Não é um parser de C#. Só percorre o texto uma vez e devolve os trechos que são
string (inclusive verbatim @"...", interpolada $"..." e raw \"\"\"...\"\"\") e os
trechos que são comentário (// e /* */). Isso basta para:

- o motor PII procurar termos de saúde só dentro de strings e comentários;
- o taint casar chaves e separar comandos sem se confundir com '{', '}' e ';'
  que aparecem dentro de strings.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Trecho:
    inicio: int
    fim: int  # exclusivo
    tipo: str  # "string" ou "comentario"


def _pular_string_simples(texto: str, i: int) -> int:
    """i aponta para a aspa de abertura de "..." comum. Devolve o índice depois da aspa final."""
    n = len(texto)
    i += 1
    while i < n:
        c = texto[i]
        if c == "\\":
            i += 2
            continue
        if c == '"' or c == "\n":
            return i + 1
        i += 1
    return n


def _pular_verbatim(texto: str, i: int) -> int:
    """i aponta para a aspa de abertura de @"...". Aspas duplas "" são escape."""
    n = len(texto)
    i += 1
    while i < n:
        if texto[i] == '"':
            if i + 1 < n and texto[i + 1] == '"':
                i += 2
                continue
            return i + 1
        i += 1
    return n


def _pular_interpolada(texto: str, i: int, verbatim: bool) -> int:
    """i aponta para a aspa de abertura de $"..." (ou $@"..."). Respeita os buracos {expr}."""
    n = len(texto)
    i += 1
    profundidade = 0
    while i < n:
        c = texto[i]
        if profundidade == 0:
            if c == "{":
                if i + 1 < n and texto[i + 1] == "{":
                    i += 2
                    continue
                profundidade = 1
            elif c == '"':
                if verbatim and i + 1 < n and texto[i + 1] == '"':
                    i += 2
                    continue
                return i + 1
            elif c == "\\" and not verbatim:
                i += 2
                continue
            elif c == "\n" and not verbatim:
                return i + 1
        else:
            if c == "{":
                profundidade += 1
            elif c == "}":
                profundidade -= 1
            elif c == '"':
                i = _pular_string_simples(texto, i)
                continue
        i += 1
    return n


def trechos(texto: str) -> list[Trecho]:
    """Lista, em ordem, os trechos de string e de comentário do código C#."""
    resultado: list[Trecho] = []
    n = len(texto)
    i = 0
    while i < n:
        c = texto[i]
        prox = texto[i + 1] if i + 1 < n else ""
        if c == "/" and prox == "/":
            fim = texto.find("\n", i)
            fim = n if fim == -1 else fim
            resultado.append(Trecho(i, fim, "comentario"))
            i = fim
        elif c == "/" and prox == "*":
            fim = texto.find("*/", i + 2)
            fim = n if fim == -1 else fim + 2
            resultado.append(Trecho(i, fim, "comentario"))
            i = fim
        elif texto.startswith('"""', i):
            fim = texto.find('"""', i + 3)
            fim = n if fim == -1 else fim + 3
            resultado.append(Trecho(i, fim, "string"))
            i = fim
        elif c in "$@" and (prox == '"' or (prox in "$@" and texto[i + 2:i + 3] == '"')):
            prefixo = texto[i:i + 2] if prox in "$@" else c
            inicio = i
            aspa = i + len(prefixo)
            if "$" in prefixo:
                fim = _pular_interpolada(texto, aspa, verbatim="@" in prefixo)
            else:
                fim = _pular_verbatim(texto, aspa)
            resultado.append(Trecho(inicio, fim, "string"))
            i = fim
        elif c == '"':
            fim = _pular_string_simples(texto, i)
            resultado.append(Trecho(i, fim, "string"))
            i = fim
        elif c == "'":
            # literal de caractere: 'a', '\n', '"', '\''
            if prox == "\\":
                fim = texto.find("'", i + 3)
            else:
                fim = i + 2 if texto[i + 2:i + 3] == "'" else -1
            if fim != -1 and fim - i <= 8:
                i = fim + 1
            else:
                i += 1
        else:
            i += 1
    return resultado


def apagar_comentarios(texto: str, lista: list[Trecho] | None = None) -> str:
    """Troca cada comentário por espaços, mantendo as quebras de linha (as posições não mudam)."""
    lista = trechos(texto) if lista is None else lista
    partes = list(texto)
    for t in lista:
        if t.tipo == "comentario":
            for k in range(t.inicio, t.fim):
                if partes[k] != "\n":
                    partes[k] = " "
    return "".join(partes)


def mascara_de_strings(texto: str, lista: list[Trecho] | None = None) -> list[bool]:
    """Vetor do tamanho do texto: True onde o caractere está dentro de uma string."""
    lista = trechos(texto) if lista is None else lista
    dentro = [False] * len(texto)
    for t in lista:
        if t.tipo == "string":
            for k in range(t.inicio, t.fim):
                dentro[k] = True
    return dentro


def linha_de(texto: str, posicao: int) -> int:
    """Número da linha (1-based) de uma posição no texto."""
    return texto.count("\n", 0, posicao) + 1
