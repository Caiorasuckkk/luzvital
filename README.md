# Luz Vital

Global Solution CitizenTech · FIAP 2026.2 · Engenharia de Software

## Ficha da CitizenTech

| Campo | Conteúdo |
| --- | --- |
| Nome | Luz Vital |
| Cidade e bairro | São Paulo, área de concessão da Enel SP |
| Cidadão beneficiado | Quem depende de energia em casa (oxigênio domiciliar, insulina na geladeira, cadeira motorizada, idoso acamado) e quem cuida dessas pessoas |
| Problema, em uma frase | Quando um temporal derruba a energia, quem depende dela para viver não é avisado antes, não sabe quanto tempo vai ficar sem luz nem onde achar uma tomada, e ninguém vai checar se está bem |
| Como funciona | Um modelo treinado com dados do INMET e da ANEEL prevê os dias de risco de apagão. O app avisa os cadastrados com antecedência, aciona vizinhos voluntários para checar essas pessoas e mostra pontos com energia por perto |
| O que cada parte faz | `api-csharp/` cidadãos, voluntários, alertas e check-ins · `soa-java/` pontos com energia · `mobile/` app do cidadão · `ml/` previsão do dia de risco · `cyber/` proteção dos dados de saúde · `docs/` requisitos e testes |
| Link do repositório | https://github.com/Caiorasuckkk/luzvital |
| Indicador de impacto | % de cadastrados avisados pelo menos 12h antes de um dia de risco · tempo até o primeiro check-in depois que a luz cai |
| ODS conectados | 3, 7, 10, 11 e 13 |

## Integrantes

- Caio Rasuck RM 93645
- Arthur Albuquerque RM 93025

## Partes

| Pasta | Disciplina | Status | Vídeo |
| --- | --- | --- | --- |
| `api-csharp/` | C# Software Development | Pronto | |
| `soa-java/` | SOA e Web Services | A fazer | |
| `mobile/` | Mobile Development | A fazer | |
| [luzvital-ml](https://github.com/Caiorasuckkk/luzvital-ml) | IA & Machine Learning | Pronto | https://youtu.be/a17KP1B8xQU |
| `cyber/` | Cybersecurity | Pronto | https://youtu.be/seKUeEGIqPk |
| `docs/` | Testing, Compliance & QA | A fazer | |

Dados: tudo o que aparece como pessoa no sistema é fictício. As bases do ML são públicas (INMET e ANEEL) e a fonte de cada uma está em [`dados/README.md` do luzvital-ml](https://github.com/Caiorasuckkk/luzvital-ml/blob/main/dados/README.md).
