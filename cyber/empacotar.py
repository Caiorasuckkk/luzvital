"""Gera cyber/entrega/luzvital-cyber.zip para a entrega da disciplina.

    python -m cyber.empacotar

Leva o código do módulo, o relatório gerado (cyber/saida) e as evidências
(cyber/evidencias). Deixa de fora .venv, __pycache__, .pytest_cache e a própria
pasta de entrega. Rode antes `python -m cyber.analisar ...` para o relatório
estar atualizado.
"""

from __future__ import annotations

import os
import sys
import zipfile

RAIZ_CYBER = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(RAIZ_CYBER, "entrega", "luzvital-cyber.zip")
IGNORAR_PASTAS = {".venv", "venv", "__pycache__", ".pytest_cache", "entrega"}
IGNORAR_EXT = {".pyc", ".pyo"}
# Arquivos do ML e o zip de origem dos prints (já extraídos em evidencias/prints/)
IGNORAR_ARQUIVOS = {"luzvital-ml.mp4", "luzvital-ml.pptx", "evidencias-cyber.zip"}


def main() -> int:
    relatorio = os.path.join(RAIZ_CYBER, "saida", "relatorio.html")
    if not os.path.exists(relatorio):
        print("cyber/saida/relatorio.html não existe. Rode antes:\n"
              "  python -m cyber.analisar --alvo api-csharp/src --alvo cyber/exemplos/vulneravel", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
    total = 0
    with zipfile.ZipFile(DESTINO, "w", zipfile.ZIP_DEFLATED) as z:
        for raiz, pastas, nomes in os.walk(RAIZ_CYBER):
            pastas[:] = sorted(p for p in pastas if p not in IGNORAR_PASTAS)
            for nome in sorted(nomes):
                if os.path.splitext(nome)[1] in IGNORAR_EXT or nome in IGNORAR_ARQUIVOS:
                    continue
                caminho = os.path.join(raiz, nome)
                interno = os.path.join("luzvital-cyber", "cyber", os.path.relpath(caminho, RAIZ_CYBER))
                z.write(caminho, interno.replace("\\", "/"))
                total += 1
    print(f"{DESTINO} ({total} arquivos, {os.path.getsize(DESTINO) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
