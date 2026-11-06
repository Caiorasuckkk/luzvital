# Uso de IA no projeto

A GS permite IA como copiloto, desde que os prompts fiquem registrados e a gente saiba explicar cada linha. Cada entrada: data, quem usou, ferramenta, o que foi pedido e o que foi aproveitado.

## 05/11/2026 · Caio · Claude

- **Pedido:** análise do PDF da GS, escolha do problema (apagões da Enel em SP), pesquisa de recorrência dos apagões e das bases públicas (INMET, ANEEL), divisão de entregas por disciplina.
- **Aproveitado:** a ideia da Luz Vital, o plano por disciplina e as fontes que conferimos.

## 05/11/2026 · Caio · Claude

- **Pedido:** primeira versão da API em C# (.NET 8, EF Core, SQLite): domínio, controllers, serviços de alerta e painel, testes.
- **Aproveitado:** estrutura em camadas e as regras de negócio. (Antes de subir: rodar `dotnet build` e `dotnet test` e revisar cada arquivo.)

## 06/11/2026 · Caio · Claude Code

- **Pedido:** entrega de Cybersecurity em `cyber/` (Python): motor de regras PII com CPF validado e valores mascarados ignorados; taint analysis estático nos `.cs` da API (fontes, sanitizadores e sorvedouros); exemplo vulnerável para provar o antes e depois sem alterar `api-csharp/`; scanner de runtime na API rodando; IA na remediação com a API da Anthropic e modo offline; Índice de Risco Cidadão e dashboard HTML offline; testes com pytest e script do ZIP.
- **Decisões nossas no caminho:** a estrutura e a fórmula do índice foram aprovadas antes do código; a `Dependencia` que a API devolve de propósito virou "exposição aceita", com seção própria no relatório e o aviso de que a API não tem autenticação; os dados fictícios só valem por valor e arquivo juntos.
- **Aproveitado:** o módulo inteiro (motor PII, taint, runtime, IA, índice, dashboard, testes e empacotamento). Resultado: 0 vazamentos na API real (índice 0) e 4 defeitos no exemplo vulnerável (índice 65). A IA rodou em modo offline, porque a chave da Anthropic não está configurada nesta máquina.
