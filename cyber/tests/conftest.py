import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# Os testes usam caminhos relativos à raiz do repositório (api-csharp/src, cyber/exemplos/...).
os.chdir(RAIZ)
