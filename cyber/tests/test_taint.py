from cyber.taint import analisador as taint
from cyber.taint.analisador import Analisador, ler_metodos


def _status(fluxos):
    return {(f.campo, f.status) for f in fluxos}


# ---------------------------------------------------------------- exemplo vulnerável e API real

def test_exemplo_vulneravel_tem_os_tres_vazamentos():
    fluxos = taint.analisar("cyber/exemplos/vulneravel", base=".")
    vaz = [f for f in fluxos if f.status == taint.VAZAMENTO]
    defeitos = {(f.campo, f.tipo_sorvedouro) for f in vaz}
    assert ("Telefone", "log") in defeitos                 # log com o telefone inteiro
    assert ("Dependencia", "log") in defeitos              # e a dependência junto
    assert ("Cpf", "resposta HTTP") in defeitos            # DTO devolvendo o CPF cru
    assert ("Endereco", "exceção") in defeitos             # exceção com o endereço
    pontos = {(f.campo, f.ponto) for f in vaz}
    assert len(pontos) == 4                                # 4 defeitos, mesmo com 7 fluxos


def test_api_real_tem_zero_vazamentos():
    fluxos = taint.analisar("api-csharp/src", base=".")
    assert [f for f in fluxos if f.status == taint.VAZAMENTO] == []
    assert sum(f.status == taint.SANITIZADO for f in fluxos) > 0


def test_api_real_so_tem_as_duas_exposicoes_aceitas():
    fluxos = taint.analisar("api-csharp/src", base=".")
    aceitas = {f.excecao for f in fluxos if f.status == taint.EXPOSICAO_ACEITA}
    assert aceitas == {"dependencia-cadastro", "dependencia-painel"}
    assert all(f.campo == "Dependencia" for f in fluxos if f.status == taint.EXPOSICAO_ACEITA)


def test_dto_de_resposta_sanitiza_cpf_telefone_e_endereco():
    fluxos = taint.analisar("api-csharp/src", base=".")
    pelo_dto = [f for f in fluxos if any("CidadaoResponse.De" in p for p in f.caminho)]
    assert {("Cpf", "SANITIZADO"), ("Telefone", "SANITIZADO"), ("Endereco", "SANITIZADO")} <= _status(pelo_dto)


# ---------------------------------------------------------------- trechos pequenos de C#

def _analisar_codigo(tmp_path, codigo):
    arq = tmp_path / "Teste.cs"
    arq.write_text(codigo, encoding="utf-8")
    return Analisador(ler_metodos(str(arq), "Teste.cs")).executar()


def test_log_sem_mascara_e_vazamento(tmp_path):
    fluxos = _analisar_codigo(tmp_path, """
public class Servico {
    public void Avisar(Cidadao c) {
        var tel = c.Telefone;
        _logger.LogInformation("Ligando para {Tel}", tel);
    }
}""")
    assert _status(fluxos) == {("Telefone", "VAZAMENTO")}
    assert fluxos[0].fonte == "Teste.cs:3" and fluxos[0].sorvedouro == "Teste.cs:5"


def test_log_com_mascara_e_sanitizado(tmp_path):
    fluxos = _analisar_codigo(tmp_path, """
public class Servico {
    public void Avisar(Cidadao c) {
        _logger.LogInformation("Ligando para {Tel}", Mascara.Telefone(c.Telefone));
    }
}""")
    assert _status(fluxos) == {("Telefone", "SANITIZADO")}


def test_destinatario_da_notificacao_nao_conta_como_saida(tmp_path):
    fluxos = _analisar_codigo(tmp_path, """
public class Servico {
    public async Task Avisar(Cidadao c) {
        await _notificador.EnviarAsync(c, "Risco de apagão amanhã.", ct);
    }
    public async Task AvisarErrado(Cidadao c) {
        await _notificador.EnviarAsync(c, $"Seu CPF {c.Cpf} está cadastrado.", ct);
    }
}""")
    assert _status(fluxos) == {("Cpf", "VAZAMENTO")}
    assert all(f.metodo == "Servico.AvisarErrado" for f in fluxos)


def test_mensagem_de_excecao_com_endereco(tmp_path):
    fluxos = _analisar_codigo(tmp_path, """
public class Controller {
    public IActionResult Criar(CidadaoRequest req) {
        throw new DomainException($"Endereço {req.Endereco} inválido.");
    }
}""")
    assert _status(fluxos) == {("Endereco", "VAZAMENTO")}
    assert fluxos[0].tipo_sorvedouro == "exceção"
