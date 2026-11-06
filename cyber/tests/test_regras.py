import json

from cyber.pii import regras as pii


def regras_achadas(texto, arquivo=None):
    return [a.regra for a in pii.encontrar(texto, arquivo=arquivo).achados]


# ---------------------------------------------------------------- CPF

def test_cpf_valido_com_e_sem_pontuacao():
    assert pii.cpf_valido("529.982.247-25")
    assert pii.cpf_valido("52998224725")
    assert regras_achadas("CPF: 529.982.247-25") == ["cpf"]
    assert regras_achadas("cpf=52998224725") == ["cpf"]


def test_cpf_invalido_nao_e_achado():
    assert not pii.cpf_valido("123.456.789-00")
    assert not pii.cpf_valido("111.111.111-11")
    assert "cpf" not in regras_achadas("pedido 123.456.789-00 e 111.111.111-11")


def test_cpf_ja_mascarado_e_ignorado():
    r = pii.encontrar('{"cpfMascarado":"529.***.***-25"}')
    assert r.achados == []
    assert [m["tipo"] for m in r.mascarados] == ["cpf"]


# ---------------------------------------------------------------- telefone, endereço, contato

def test_telefone_inteiro_e_mascarado():
    assert regras_achadas("ligar para (11) 98765-4321") == ["telefone"]
    r = pii.encontrar('{"telefoneMascarado":"(11) *****-0001"}')
    assert r.achados == []
    assert r.mascarados[0]["tipo"] == "telefone"


def test_endereco_email_cep():
    achados = regras_achadas("Mora na Av. Paulista 1000, CEP 01310-100, maria@exemplo.com")
    assert achados == ["endereco", "cep", "email"]


# ---------------------------------------------------------------- saúde

def test_termos_de_saude():
    assert regras_achadas("usa oxigênio em casa") == ["saude"]
    assert regras_achadas("guarda insulina na geladeira") == ["saude"]
    assert regras_achadas('"dependencia":"OxigenioDomiciliar"') == ["saude"]
    assert regras_achadas("diagnóstico CID E10.9") == ["cid10"]


def test_saude_no_cs_so_vale_em_string_e_comentario():
    codigo = "var d = TipoDependencia.OxigenioDomiciliar;\n"
    assert regras_achadas(codigo, arquivo="X.cs") == []
    codigo_com_string = 'var msg = "paciente usa insulina";\n// usa oxigênio\n'
    assert regras_achadas(codigo_com_string, arquivo="X.cs") == ["saude", "saude"]


# ---------------------------------------------------------------- segredos

def test_segredos_no_codigo():
    assert regras_achadas('"Server=db;User=sa;Password=SenhaForte123;"') == ["senha"]
    assert regras_achadas("password=abc12345") == ["senha"]
    assert regras_achadas('ApiKey = "abcdefghijklmnop1234"') == ["chave_api"]


# ---------------------------------------------------------------- fictícios: valor E arquivo

def test_ficticio_vale_so_no_arquivo_declarado():
    tel = '"11900000001"'
    seed = pii.encontrar(tel, arquivo="api-csharp/src/LuzVital.Infrastructure/Data/SeedDados.cs").achados
    outro = pii.encontrar(tel, arquivo="api-csharp/src/LuzVital.Api/Program.cs").achados
    assert seed[0].status == pii.FICTICIO
    assert outro[0].status == pii.ACHADO


def test_outro_valor_no_arquivo_declarado_continua_achado():
    r = pii.encontrar('"Rua de Teste, 1"', arquivo="LuzVital.Api.http").achados
    assert r[0].regra == "endereco" and r[0].status == pii.ACHADO
    r = pii.encontrar('"Rua Exemplo, 100"', arquivo="LuzVital.Api.http").achados
    assert r[0].status == pii.FICTICIO


# ---------------------------------------------------------------- o relatório nunca tem o dado inteiro

def test_achado_nunca_carrega_o_valor_inteiro():
    valores = ["529.982.247-25", "(11) 98765-4321", "Av. Paulista 1000", "maria@exemplo.com",
               "01310-100", "Password=SenhaForte123"]
    r = pii.encontrar(" | ".join(valores))
    serializado = json.dumps([a.para_dict() for a in r.achados], ensure_ascii=False)
    assert len(r.achados) == len(valores)
    for v in valores:
        assert v not in serializado
    assert "52998224725" not in serializado and "98765-4321" not in serializado and "SenhaForte123" not in serializado
