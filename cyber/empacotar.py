"""Gera cyber/entrega/luzvital-cyber.zip para a entrega da disciplina.

    python -m cyber.empacotar

Só entra no zip o que está na lista INCLUIR: o código do módulo, os prints e os
.txt de evidência e o relatório gerado (cyber/saida). A pasta cyber/ nunca é
copiada inteira, porque cyber/evidencias/ recebe arquivos pessoais que não podem
sair na entrega. Rode antes `python -m cyber.analisar ...` para o relatório
estar atualizado.
"""

from __future__ import annotations

import glob
import os
import sys
import zipfile

RAIZ_CYBER = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(RAIZ_CYBER, "entrega", "luzvital-cyber.zip")

# Relativos a cyber/. Cada padrão casa um tipo de arquivo numa pasta só, sem descer em subpastas.
INCLUIR = [
    "README.md",
    "requirements.txt",
    "exclusoes.json",
    "*.py",
    "dashboard/*.py",
    "ia/*.py",
    "pii/*.py",
    "runtime/*.py",
    "taint/*.py",
    "taint/excecoes.json",
    "tests/*.py",
    "exemplos/vulneravel/*.cs",
    "evidencias/README.md",
    "evidencias/*.txt",
    "evidencias/prints/*.png",
    "saida/relatorio.html",
    "saida/achados.json",
    "saida/fluxos-taint.txt",
]


def arquivos_da_entrega() -> list[str]:
    encontrados: list[str] = []
    for padrao in INCLUIR:
        achados = sorted(glob.glob(os.path.join(RAIZ_CYBER, padrao)))
        if not achados:
            print(f"aviso: nada encontrado para cyber/{padrao}", file=sys.stderr)
        encontrados.extend(a for a in achados if os.path.isfile(a) and a not in encontrados)
    return encontrados


def main() -> int:
    relatorio = os.path.join(RAIZ_CYBER, "saida", "relatorio.html")
    if not os.path.exists(relatorio):
        print("cyber/saida/relatorio.html não existe. Rode antes:\n"
              "  python -m cyber.analisar --alvo api-csharp/src --alvo cyber/exemplos/vulneravel", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
    arquivos = arquivos_da_entrega()
    with zipfile.ZipFile(DESTINO, "w", zipfile.ZIP_DEFLATED) as z:
        for caminho in arquivos:
            interno = os.path.join("luzvital-cyber", "cyber", os.path.relpath(caminho, RAIZ_CYBER))
            z.write(caminho, interno.replace("\\", "/"))
    print(f"{DESTINO} ({len(arquivos)} arquivos, {os.path.getsize(DESTINO) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
