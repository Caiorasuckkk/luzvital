"""Textos-modelo usados quando não há chave da Anthropic (modo offline).

Cada achado ganha um alerta em linguagem simples para o cidadão e uma correção técnica.
Os textos são montados por tipo de dado e por onde ele saiu.
"""

from __future__ import annotations

DADO = {
    "cpf": "O CPF",
    "telefone": "O telefone",
    "endereco": "O endereço",
    "saude": "O tipo de aparelho de saúde",
    "cid10": "O código da doença (CID)",
    "email": "O e-mail",
    "cep": "O CEP",
    "senha": "Uma senha do sistema",
    "chave_api": "Uma chave de acesso do sistema",
}

ONDE = {
    "log": "aparecia no registro do servidor",
    "resposta HTTP": "saía inteiro na resposta da API",
    "exceção": "aparecia na mensagem de erro, que vai para a tela do app e para o registro do servidor",
    "notificação": "ia dentro da mensagem enviada por SMS ou WhatsApp",
    "runtime": "saiu inteiro na resposta da API em funcionamento",
    "código": "estava escrito no código do sistema, que fica publicado no GitHub",
}

QUEM_VE = {
    "log": "Qualquer pessoa com acesso aos logs",
    "resposta HTTP": "Qualquer pessoa que chamasse a API",
    "exceção": "Quem visse o erro ou lesse os logs",
    "notificação": "Quem pegasse o celular de outra pessoa",
    "runtime": "Qualquer pessoa que chamasse a API",
    "código": "Qualquer pessoa que abrisse o repositório",
}

CONSEQUENCIA = {
    "cpf": "poderia usar o documento em golpes e cadastros falsos",
    "telefone": "poderia ligar para ela",
    "endereco": "saberia onde ela mora",
    "saude": "saberia que ela depende de um aparelho para viver e fica vulnerável quando a luz cai",
    "cid10": "saberia qual doença ela tem",
    "email": "poderia mandar mensagens falsas para ela",
    "cep": "saberia a região onde ela mora",
    "senha": "poderia entrar no banco de dados e ver os dados de todos",
    "chave_api": "poderia usar o sistema em nome da Luz Vital",
}

CORRECAO = {
    ("telefone", "log"): "Use Mascara.Telefone(...) antes de logar: _logger.LogInformation(\"... {Telefone}\", Mascara.Telefone(destinatario.Telefone)).",
    ("saude", "log"): "Não registre a dependência no log. Registre só o Id da pessoa e, se precisar, \"prioritário: sim/não\".",
    ("cpf", "resposta HTTP"): "No DTO de resposta, troque c.Cpf por Cpf.Mascarar(c.Cpf) e renomeie o campo para CpfMascarado.",
    ("endereco", "exceção"): "Tire o endereço da mensagem da exceção. Use uma mensagem fixa (\"Bairro é obrigatório.\") e, para rastrear, logue só o Id do cadastro.",
    ("endereco", "resposta HTTP"): "Remova o endereço do DTO de resposta; ele só é usado internamente.",
    ("telefone", "resposta HTTP"): "No DTO de resposta, use Mascara.Telefone(...) e exponha o campo como TelefoneMascarado.",
}

CORRECAO_POR_SORVEDOURO = {
    "log": "Não passe o dado para o log; use a máscara (Cpf.Mascarar, Mascara.Telefone) ou registre só o Id.",
    "resposta HTTP": "Devolva o dado por um DTO de resposta que mascara ou omite o campo.",
    "exceção": "Use mensagem de erro fixa, sem dado pessoal; o detalhe vai para o log já mascarado.",
    "notificação": "Monte a mensagem sem dado pessoal; o destinatário já sabe quem é.",
    "runtime": "Ache o DTO que monta essa resposta e aplique a máscara no campo (o taint aponta o arquivo).",
    "código": "Troque o valor por um dado fictício já declarado em cyber/pii/ficticios.py, ou tire-o do código.",
}

CORRECAO_SEGREDO = "Tire o segredo do código e do histórico do git, troque a senha/chave e leia o valor de variável de ambiente ou de um cofre (User Secrets, Key Vault)."


def gerar(item: dict) -> dict:
    regra, onde = item["regra"], item["onde"]
    # se o mesmo ponto também vaza a dependência, o alerta diz isso (é o caso mais grave)
    quem = "de quem usa aparelho de saúde em casa" if item.get("com_saude") and regra != "saude" \
        else "de quem depende de energia em casa"
    alerta = f"{DADO.get(regra, 'Um dado pessoal')} {quem} {ONDE.get(onde, 'ficava exposto')}. " \
             f"{QUEM_VE.get(onde, 'Alguém de fora')} {CONSEQUENCIA.get(regra, 'poderia usar esse dado')}."
    if regra in ("senha", "chave_api"):
        alerta = f"{DADO[regra]} {ONDE.get(onde, 'ficava exposta')}. {QUEM_VE.get(onde, 'Alguém de fora')} {CONSEQUENCIA[regra]}."
    if regra in ("senha", "chave_api"):
        correcao = CORRECAO_SEGREDO
    else:
        correcao = CORRECAO.get((regra, onde)) or CORRECAO_POR_SORVEDOURO.get(onde, "Mascare ou remova o dado antes de ele sair do sistema.")
    return {"alerta_cidadao": alerta, "correcao_tecnica": correcao}
