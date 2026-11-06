"""O que o taint considera fonte, sanitizador e sorvedouro na API da Luz Vital.

Fonte (dado sensível entrando)
    As propriedades Cpf, Telefone, Endereco e Dependencia de Cidadao, Pessoa,
    Voluntario e dos DTOs de request. Uma variável vira fonte quando:
      - é parâmetro de um desses tipos (ou de uma coleção deles);
      - recebe algo lido de _db.Cidadaos, _db.Voluntarios ou _db.Pessoas;
      - recebe um `new Cidadao(...)` / `new Voluntario(...)`;
      - é ligada por `x is Cidadao c` a partir de outra fonte;
      - dentro da própria classe Cidadao/Pessoa, o código lê a propriedade direto.

Sanitizador (dado deixa de ser perigoso)
    Cpf.Mascarar(...) e Mascara.*(...), e os DTOs de resposta (classes *Response):
    um campo que o DTO não expõe, ou expõe mascarado, sai sanitizado.

Sorvedouro (dado saindo do sistema)
    log            _logger.Log*(...), Console.Write*(...), Debug.Write*(...)
    exceção        new XxxException(...)  (a mensagem pode ir para o log ou para a resposta)
    resposta HTTP  Ok(...), Created*(...), Accepted*(...), Conflict(...), NotFound(...), etc.
    notificação    EnviarAsync(destinatario, mensagem): só a MENSAGEM conta como saída;
                   o destinatário é para quem o aviso vai, não conteúdo enviado.
"""

from __future__ import annotations

import re

# Tipo -> propriedades sensíveis que ele carrega
FONTES_TIPOS: dict[str, list[str]] = {
    "Cidadao": ["Cpf", "Telefone", "Endereco", "Dependencia"],
    "CidadaoRequest": ["Cpf", "Telefone", "Endereco", "Dependencia"],
    "Pessoa": ["Telefone"],
    "Voluntario": ["Telefone"],
    "VoluntarioRequest": ["Telefone"],
}

# DbSet -> tipo da entidade
COLECOES: dict[str, str] = {"Cidadaos": "Cidadao", "Voluntarios": "Voluntario", "Pessoas": "Pessoa"}

CAMPOS = {"Cpf", "Telefone", "Endereco", "Dependencia"}

# Propriedade -> regra do motor PII (dá severidade e categoria para o índice)
CAMPO_REGRA = {"Cpf": "cpf", "Telefone": "telefone", "Endereco": "endereco", "Dependencia": "saude"}

SANITIZADORES = re.compile(r"\b(Cpf\.Mascarar|Mascara\.\w+)\s*\(")

# Métodos de coleção que devolvem os mesmos objetos (o dado continua contaminado)
PASSA_ADIANTE = {
    "Where", "OrderBy", "OrderByDescending", "ThenBy", "ThenByDescending", "ToList", "ToListAsync",
    "ToArray", "ToArrayAsync", "AsNoTracking", "AsEnumerable", "AsQueryable", "Cast", "OfType", "Concat",
    "Union", "Distinct", "Skip", "Take", "Include", "First", "FirstOrDefault", "FirstOrDefaultAsync",
    "FirstAsync", "Single", "SingleOrDefault", "SingleOrDefaultAsync", "SingleAsync", "Last",
    "LastOrDefault", "FindAsync", "Find", "Reverse", "ElementAt",
}

# (tipo, regex até o "(", índices dos argumentos que saem; None = todos)
SORVEDOUROS: list[tuple[str, re.Pattern, list[int] | None]] = [
    ("log", re.compile(r"\b\w*[Ll]ogger\s*\.\s*Log\w*\s*\("), None),
    ("log", re.compile(r"\b(?:Console|Debug|Trace)\s*\.\s*(?:Error\s*\.\s*)?Write\w*\s*\("), None),
    ("exceção", re.compile(r"\bnew\s+\w*Exception\s*\("), None),
    ("resposta HTTP", re.compile(
        r"(?<![\w.])(?:Ok|Created|CreatedAtAction|CreatedAtRoute|Accepted|AcceptedAtAction|AcceptedAtRoute"
        r"|BadRequest|NotFound|Conflict|UnprocessableEntity|Problem|ValidationProblem|Json|Content)\s*\("), None),
    ("resposta HTTP", re.compile(r"\bResults\s*\.\s*\w+\s*\("), None),
    ("resposta HTTP", re.compile(r"\.\s*Write(?:AsJson)?Async\s*\("), None),
    ("notificação", re.compile(r"\.\s*EnviarAsync\s*\("), [1]),
]

PALAVRAS_RESERVADAS = {
    "if", "for", "foreach", "while", "switch", "catch", "using", "lock", "return", "new", "nameof", "typeof",
    "sizeof", "default", "await", "throw", "var", "base", "this", "fixed", "checked", "unchecked",
}
