# Luz Vital · Cybersecurity

A API da Luz Vital guarda dados sensíveis de quem depende de energia em casa: CPF, telefone, endereço e o equipamento médico de que a pessoa depende, que é dado de saúde (LGPD, art. 11). Este módulo verifica, de três jeitos, se algum desses dados sai do sistema inteiro:

1. **Motor de regras PII** procura dado pessoal em texto: no código, nas respostas da API e nos achados enviados à IA.
2. **Taint analysis** segue cada dado sensível no código C#, da entrada até a saída (log, exceção, resposta HTTP e notificação).
3. **Scanner de runtime** chama a API rodando e confere que as respostas trazem o dado só mascarado.

O resultado vira o **Índice de Risco Cidadão** (0 a 100), mostrado num dashboard HTML. Cada problema também ganha um alerta em linguagem simples para o cidadão e uma correção técnica para o desenvolvedor, escritos por IA.

Todos os dados usados são fictícios (o seed da API). Nenhum relatório deste módulo imprime um dado inteiro.

## Como rodar

Precisa de Python 3.10 ou mais novo. Os comandos são rodados da raiz do repositório (`luzvital/`).

```bash
python -m venv .venv
.venv\Scripts\activate                 # Linux/macOS: source .venv/bin/activate
pip install -r cyber/requirements.txt

# opcional: subir a API para o scanner de runtime (outro terminal)
dotnet run --project api-csharp/src/LuzVital.Api

python -m cyber.analisar --alvo api-csharp/src --alvo cyber/exemplos/vulneravel
```

A análise grava três arquivos em `cyber/saida/`:

| Arquivo | O que é |
| --- | --- |
| `relatorio.html` | Dashboard Risco Cidadão. Abre offline, sem CDN e sem JavaScript |
| `achados.json` | Tudo o que o relatório mostra, em JSON |
| `fluxos-taint.txt` | Os fluxos do taint em texto, para servir de evidência |

Outros comandos:

```bash
python -m pytest cyber/tests          # testes
python -m cyber.empacotar             # gera cyber/entrega/luzvital-cyber.zip
```

### IA na remediação

| Variável | Para que serve |
| --- | --- |
| `ANTHROPIC_API_KEY` | Chave da API da Anthropic. Sem ela, o módulo usa o **modo offline**, com textos-modelo por tipo de achado |
| `LUZVITAL_MODELO` | Modelo usado. O padrão é `claude-haiku-5-5` |

O relatório diz qual modo foi usado e por quê. A opção `--offline` força o modo offline mesmo com chave. Se a API devolver erro, ou se o modelo recusar o pedido, a análise cai direto no modo offline, sem tentar outro modelo.

**O que vai para o modelo:** só o tipo do dado, onde ele saiu, o arquivo e a linha, o caminho no código e o trecho **já mascarado** (por exemplo `(11) *****-4321`). Esse payload é montado a partir de uma lista fixa de campos. Antes do envio, ele ainda passa pelo motor PII; se aparecer qualquer dado inteiro, o envio é cancelado e o módulo usa o modo offline. Há teste cobrindo esse caso.

## Arquitetura

```
cyber/
  analisar.py           entrada única: junta tudo e grava cyber/saida/
  indice.py             Índice de Risco Cidadão
  csharp.py             leitura léxica de C# (onde estão strings e comentários)
  pii/regras.py         motor de regras PII
  pii/ficticios.py      dados fictícios declarados (valor + arquivo)
  taint/config.py       fontes, sanitizadores e sorvedouros
  taint/analisador.py   taint analysis
  taint/excecoes.json   exposições aceitas, com o motivo
  runtime/scanner.py    scanner da API em funcionamento
  ia/remediacao.py      IA (Anthropic) com queda para o modo offline
  ia/textos_offline.py  textos-modelo do modo offline
  dashboard/gerar.py    relatorio.html
  exemplos/vulneravel/  3 arquivos da API alterados para vazar (prova do "antes")
  tests/                pytest
  evidencias/           prints, vídeo e saídas usadas na entrega
  empacotar.py          gera o ZIP da entrega
```

### Motor de regras PII (`pii/regras.py`)

Cada regra tem nome, regex, severidade (1 a 5) e categoria.

| Regra | Categoria | Severidade | Observação |
| --- | --- | --- | --- |
| CPF | identificação | 5 | Valida os dígitos verificadores; um número qualquer de 11 dígitos não conta |
| Telefone | contato | 4 | Fixo ou celular, com ou sem formatação |
| E-mail | contato | 3 | |
| CEP | localização | 2 | |
| Endereço | localização | 4 | "Rua", "Av.", "Alameda" e outros, seguidos de número |
| Saúde | saúde | 4 | Oxigênio, insulina, os nomes do enum `TipoDependencia` e outros termos |
| CID-10 | saúde | 4 | Formato A00.0 |
| Senha | segredo | 5 | Connection string com senha, `password=`, `pwd=` |
| Chave de API | segredo | 5 | Formatos conhecidos (`sk-ant-`, `AKIA`, `ghp_`...) e `api_key=` com valor longo |

- **Valores já mascarados** (`529.***.***-25`, `(11) *****-0001`) são reconhecidos e contados à parte. Eles provam que a máscara funcionou e não contam como vazamento.
- **Nos arquivos `.cs`**, os termos de saúde só valem dentro de strings e comentários. Sem essa regra, cada `TipoDependencia.OxigenioDomiciliar` do código viraria achado.
- **Dados fictícios declarados** (`pii/ficticios.py`): a exceção vale para o valor e para o arquivo ao mesmo tempo. Os telefones `119000000xx`, os endereços "Rua Exemplo" e "Rua Modelo" e o CPF de teste 529.982.247-25 valem só dentro do `SeedDados.cs` e do `LuzVital.Api.http`. "Rua de Teste, 1" e `OxigenioDomiciliar` valem só no `LuzVital.Api.http`, o exemplo de POST da API. Qualquer outro valor nesses arquivos continua sendo um achado normal.
- **O dado inteiro nunca sai do motor:** cada achado traz só o trecho mascarado, a posição, a regra e a severidade.

### Taint analysis (`taint/`)

A análise é estática e baseada em texto. Não é um compilador de C#: ela lê cada arquivo, separa os métodos e segue as variáveis em ordem dentro de cada método.

| Papel | O que conta |
| --- | --- |
| **Fonte** | As propriedades `Cpf`, `Telefone`, `Endereco` e `Dependencia` de `Cidadao`, `Pessoa`, `Voluntario` e dos DTOs de request. Isso inclui parâmetros desses tipos, leituras de `_db.Cidadaos`/`_db.Voluntarios`/`_db.Pessoas`, `new Cidadao(...)` e `x is Cidadao c` |
| **Sanitizador** | `Cpf.Mascarar(...)`, `Mascara.*(...)` e os DTOs de resposta (`*Response`). Um campo que o DTO não expõe, ou expõe mascarado, sai sanitizado |
| **Sorvedouro** | Log (`_logger.Log*`, `Console.Write*`), mensagem de exceção (`new XException(...)`), corpo de resposta HTTP (`Ok`, `Created*`, `Conflict`...) e notificação (`EnviarAsync`) |

Na notificação, só a **mensagem** conta como saída. O destinatário é para quem o aviso vai, não conteúdo enviado.

Cada fluxo sai com a fonte (`arquivo:linha`), o sorvedouro (`arquivo:linha`), o caminho percorrido e um de três status:

- **SANITIZADO:** o dado passou por um sanitizador antes de sair.
- **VAZAMENTO:** o dado saiu inteiro.
- **EXPOSICAO_ACEITA:** o dado saiu inteiro de propósito, e o motivo está registrado em `excecoes.json`.

**Resumo de método.** A análise segue o dado dentro do método. Para os DTOs funcionarem como sanitizadores, e para pegar o painel (o dado nasce no `ServicoPainel` e sai no `PainelController`), há um passo a mais: antes da análise final, cada método ganha um resumo do que devolve, campo por campo, cru ou mascarado. Uma chamada como `CidadaoResponse.De(c)` usa esse resumo.

**Limites conhecidos.** A análise não resolve tipos, herança nem injeção de dependência, e não segue o dado por campos de classe nem pelo banco. Um método chamado sem resumo passa adiante o que recebeu, o que é uma postura conservadora. A pasta `Migrations/` fica fora, por ser código gerado.

### Exposições aceitas

A API devolve o tipo de dependência (oxigênio, insulina...) em `GET /api/cidadaos` e em `GET /api/painel/sem-checkin`. Isso é intencional, porque o voluntário precisa saber quem checar primeiro. Esses fluxos estão registrados em `taint/excecoes.json` com o motivo (finalidade de cuidado). O relatório mostra os dois numa seção própria, com a contagem ao lado do índice, mas eles não entram na conta.

> **A API não tem autenticação: qualquer pessoa pode listar quem usa oxigênio em cada bairro.**
>
> Recomendação: autenticação (JWT) e perfil de acesso (coordenador, voluntário e cidadão), para que só o voluntário daquele bairro, durante um alerta ativo, veja a dependência. Para os demais perfis, a resposta traz só "prioritário: sim/não".

## Índice de Risco Cidadão

```
peso   = severidade da regra (1 a 5) × fator da categoria
fator  = saúde 2,0 · segredo 1,5 · identificação, contato e localização 1,0
S      = soma dos pesos dos vazamentos não sanitizados
Índice = arredonda( 100 × (1 − e^(−S/20)) )
Faixa  = 0–29 baixo · 30–59 médio · 60–100 alto
```

**Entram em S:** os fluxos do taint com status VAZAMENTO, o dado inteiro encontrado nas respostas da API em funcionamento e os segredos escritos no código.

**Não entram em S:** os fluxos sanitizados, as exposições aceitas, os dados fictícios declarados e o dado pessoal escrito no código que não seja segredo. Todos esses aparecem no relatório, à parte.

**Cada defeito conta uma vez.** Um CPF cru dentro de um DTO usado por quatro rotas é um vazamento de CPF, e o relatório mostra as quatro rotas. Se um mesmo ponto vaza dois dados, como telefone e dependência no mesmo log, cada dado conta.

**Por que essa curva:** o índice fica sempre entre 0 e 100 e não depende do tamanho do código. O primeiro vazamento pesa bastante e os seguintes vão somando cada vez menos. Como a saúde pesa o dobro, um único vazamento de saúde já leva o índice à faixa média.

| Cenário | S | Índice |
| --- | --- | --- |
| API real | 0 | **0**, baixo |
| 1 CPF vazado | 5 | 22, baixo |
| 1 dado de saúde vazado | 8 | 33, médio |
| Exemplo vulnerável: telefone e dependência no log, CPF no DTO, endereço na exceção | 4 + 8 + 5 + 4 = 21 | **65**, alto |

## Prova de que funciona (antes e depois)

`exemplos/vulneravel/` tem cópias de três arquivos da API, alteradas de propósito para vazar. A API em `api-csharp/` não foi alterada.

| Arquivo | Alteração | O que o scanner acha |
| --- | --- | --- |
| `NotificadoresSimulados.cs` | O SMS loga o telefone inteiro e a dependência | VAZAMENTO de Telefone e de Dependencia no log |
| `Dtos.cs` | `CidadaoResponse.De` devolve `c.Cpf` sem `Cpf.Mascarar` | VAZAMENTO de CPF na resposta HTTP (4 rotas, 1 defeito) |
| `CidadaosController.cs` | A exceção do cadastro leva `req.Endereco` | VAZAMENTO de Endereço na mensagem de exceção |

| Alvo | Vazamentos | Exposições aceitas | Sanitizados | Índice |
| --- | --- | --- | --- | --- |
| `api-csharp/src` (API real) | **0** | 2 (5 fluxos) | 18 | **0**, baixo |
| `cyber/exemplos/vulneravel` | **4 defeitos** (7 fluxos) | 1 (4 fluxos) | 9 | **65**, alto |

Os testes em `tests/test_taint.py` garantem os dois lados: o exemplo vulnerável tem os quatro defeitos e a API real tem zero vazamentos.

## Evidências

| Onde | O quê |
| --- | --- |
| `saida/relatorio.html` | Dashboard com o índice dos dois alvos lado a lado |
| `saida/fluxos-taint.txt` | Todos os fluxos do taint, com fonte, sorvedouro e caminho |
| `saida/achados.json` | Dados completos da análise |
| `evidencias/` | Saída dos testes e da análise, prints e vídeo do dashboard |
