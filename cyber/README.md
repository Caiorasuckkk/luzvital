# Luz Vital - Cybersecurity

A API da Luz Vital guarda dados sensíveis de quem depende de energia em casa: CPF, telefone, endereço e o equipamento médico que a pessoa usa. Esse último é dado de saúde (LGPD, art. 11). Este módulo verifica de três jeitos se algum desses dados sai do sistema inteiro:

1. Motor de regras PII: procura dado pessoal em texto (código, respostas da API e o que vai para a IA).
2. Taint analysis: segue cada dado sensível no código C#, da entrada até a saída (log, exceção, resposta HTTP e notificação).
3. Scanner de runtime: chama a API rodando e confere se as respostas trazem o dado mascarado.

O motor PII detecta CPF (com dígito verificador), telefone, e-mail, CEP, endereço, termos de saúde e segredos no código.

O resultado vira o Índice de Risco Cidadão (0 a 100), mostrado num dashboard HTML. Cada problema também ganha um alerta em linguagem simples para o cidadão e uma correção para o desenvolvedor, escritos pela IA. Todos os dados usados são os fictícios do seed da API.

## Vídeo

https://youtu.be/seKUeEGIqPk

## Como rodar

Python 3.10 ou mais novo, a partir da raiz do repositório (`luzvital/`).

```bash
python -m venv .venv
.venv\Scripts\activate                 # Linux/macOS: source .venv/bin/activate
pip install -r cyber/requirements.txt

# opcional: subir a API para o scanner de runtime (outro terminal)
dotnet run --project api-csharp/src/LuzVital.Api

python -m cyber.analisar --alvo api-csharp/src --alvo cyber/exemplos/vulneravel
python -m pytest cyber/tests          # testes
python -m cyber.empacotar             # gera cyber/entrega/luzvital-cyber.zip
```

A análise grava em `cyber/saida/` o `relatorio.html` (abre offline, sem JavaScript), o `achados.json` e o `fluxos-taint.txt`.

Para a IA, defina `ANTHROPIC_API_KEY`. O modelo padrão é `claude-haiku-5-5` e pode ser trocado em `LUZVITAL_MODELO`. Sem chave, com `--offline` ou se a API der erro, o módulo usa textos-modelo por tipo de achado, e o relatório diz qual modo foi usado. Para o modelo vai só o tipo do dado, o local, o caminho no código e o trecho já mascarado, como `(11) *****-4321`. Antes do envio, o motor PII confere o pedido e cancela se encontrar dado inteiro.

## Pastas

- `analisar.py`: entrada única, junta tudo e grava `cyber/saida/`
- `indice.py`: cálculo do índice
- `pii/`: regras de dado pessoal e os dados fictícios declarados
- `taint/`: taint analysis, configuração e exposições aceitas (`excecoes.json`)
- `runtime/`: scanner da API em funcionamento
- `ia/`: chamada à IA e textos do modo offline
- `dashboard/`: geração do `relatorio.html`
- `exemplos/vulneravel/`: três arquivos da API alterados de propósito para vazar
- `tests/`, `evidencias/`

## Exposições aceitas

A API devolve o tipo de dependência (oxigênio, insulina etc.) em `GET /api/cidadaos` e em `GET /api/painel/sem-checkin`. Isso é proposital, porque o voluntário precisa saber quem checar primeiro. Esses fluxos estão em `taint/excecoes.json` com o motivo. O relatório mostra os dois numa seção própria, com a contagem ao lado do índice, mas eles não entram na conta.

> **A API não tem autenticação: qualquer pessoa pode listar quem usa oxigênio em cada bairro.**
>
> Recomendação: autenticação (JWT) e perfil de acesso (coordenador, voluntário e cidadão), para que só o voluntário daquele bairro veja a dependência, e só durante um alerta ativo. Para os outros perfis, a resposta traz só "prioritário: sim/não".

## Índice de Risco Cidadão

```
peso   = severidade da regra (1 a 5) x fator da categoria
fator  = saúde 2,0; segredo 1,5; identificação, contato e localização 1,0
S      = soma dos pesos dos vazamentos não sanitizados
Índice = arredonda(100 x (1 - e^(-S/20)))
Faixa  = 0 a 29 baixo, 30 a 59 médio, 60 a 100 alto
```

Entram em S os fluxos do taint com status VAZAMENTO, o dado inteiro encontrado nas respostas da API e os segredos escritos no código. Fluxos sanitizados, exposições aceitas e dados fictícios aparecem no relatório, mas ficam fora da conta. Cada defeito conta uma vez: um CPF cru num DTO usado por quatro rotas é um vazamento só.

A curva fica sempre entre 0 e 100 e não depende do tamanho do código. O primeiro vazamento pesa bastante e os seguintes somam cada vez menos. Como saúde pesa o dobro, um único vazamento de saúde já leva o índice para a faixa média.

| Alvo | Vazamentos | Exposições aceitas | Sanitizados | Índice |
| --- | --- | --- | --- | --- |
| `api-csharp/src` (API real) | 0 | 2 (5 fluxos) | 18 | 0, baixo |
| `cyber/exemplos/vulneravel` | 4 defeitos (7 fluxos) | 1 (4 fluxos) | 9 | 65, alto |

No exemplo vulnerável, o SMS loga o telefone e a dependência, o `CidadaoResponse` devolve o CPF sem máscara e a exceção do cadastro leva o endereço: S = 4 + 8 + 5 + 4 = 21. A API em `api-csharp/` não foi alterada.

## Evidências

| Onde | O quê |
| --- | --- |
| `saida/relatorio.html` | dashboard com os dois alvos lado a lado |
| `saida/fluxos-taint.txt` | fluxos do taint, com fonte, sorvedouro e caminho |
| `saida/achados.json` | dados completos da análise |
| `evidencias/pytest.txt`, `evidencias/analisar.txt` | saída dos testes e da análise |
| `evidencias/prints/` | prints do dashboard |
