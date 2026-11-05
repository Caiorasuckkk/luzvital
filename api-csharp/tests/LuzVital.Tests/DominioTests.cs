using LuzVital.Domain;
using LuzVital.Domain.Entities;

namespace LuzVital.Tests;

public class DominioTests
{
    private static readonly DateOnly Hoje = new(2026, 11, 10);

    private static Cidadao NovoCidadao(string bairro = "Bela Vista", int autonomia = 2) =>
        new("Cidadã Teste", "529.982.247-25", "11900000001", "Rua X, 1", bairro,
            TipoDependencia.OxigenioDomiciliar, autonomia);

    [Theory]
    [InlineData("529.982.247-25", true)]
    [InlineData("52998224725", true)]
    [InlineData("529.982.247-26", false)]
    [InlineData("111.111.111-11", false)]
    [InlineData("123", false)]
    public void Cpf_valida_digitos(string cpf, bool esperado) =>
        Assert.Equal(esperado, Cpf.EhValido(cpf));

    [Fact]
    public void Cpf_gerado_para_seed_e_valido() =>
        Assert.True(Cpf.EhValido(Cpf.ComDigitos("100000001")));

    [Fact]
    public void Mascaras_nao_mostram_dado_inteiro()
    {
        Assert.Equal("529.***.***-25", Cpf.Mascarar("52998224725"));
        Assert.Equal("(11) *****-0001", Mascara.Telefone("11900000001"));
    }

    [Fact]
    public void Cidadao_com_cpf_invalido_e_recusado() =>
        Assert.Throws<DomainException>(() =>
            new Cidadao("Fulano", "000.000.000-00", "11900000001", "Rua", "Mooca", TipoDependencia.Outro, 5));

    [Theory]
    [InlineData(2, true)]
    [InlineData(4, true)]
    [InlineData(5, false)]
    public void Prioridade_depende_da_autonomia(int horas, bool prioritario) =>
        Assert.Equal(prioritario, NovoCidadao(autonomia: horas).EhPrioritario);

    [Theory]
    [InlineData(0.10, NivelRisco.Baixo)]
    [InlineData(0.40, NivelRisco.Atencao)]
    [InlineData(0.69, NivelRisco.Atencao)]
    [InlineData(0.70, NivelRisco.Alto)]
    public void Previsao_classifica_o_nivel(double prob, NivelRisco nivel) =>
        Assert.Equal(nivel, new PrevisaoRisco(Hoje, prob, "teste", Hoje).Nivel);

    [Fact]
    public void Previsao_no_passado_e_recusada() =>
        Assert.Throws<DomainException>(() => new PrevisaoRisco(Hoje.AddDays(-1), 0.5, "teste", Hoje));

    [Fact]
    public void Previsao_de_risco_baixo_nao_gera_alerta()
    {
        var previsao = new PrevisaoRisco(Hoje, 0.1, "teste", Hoje);
        Assert.Throws<DomainException>(() => Alerta.APartirDaPrevisao(previsao));
    }

    [Fact]
    public void Voluntario_de_outro_bairro_nao_faz_checkin()
    {
        var alerta = Alerta.APartirDaPrevisao(new PrevisaoRisco(Hoje, 0.9, "teste", Hoje));
        var voluntario = new Voluntario("Vizinho Teste", "11900000011", "Mooca");

        Assert.Throws<DomainException>(() =>
            CheckIn.Registrar(alerta, voluntario, NovoCidadao("Bela Vista"), SituacaoCheckIn.Ok, null));
    }

    [Fact]
    public void Pedido_de_ajuda_exige_descricao()
    {
        var alerta = Alerta.APartirDaPrevisao(new PrevisaoRisco(Hoje, 0.9, "teste", Hoje));
        var voluntario = new Voluntario("Vizinho Teste", "11900000011", "Bela Vista");

        Assert.Throws<DomainException>(() =>
            CheckIn.Registrar(alerta, voluntario, NovoCidadao(), SituacaoCheckIn.PrecisaDeAjuda, " "));

        var ok = CheckIn.Registrar(alerta, voluntario, NovoCidadao(), SituacaoCheckIn.PrecisaDeAjuda,
            "Cilindro de oxigênio acabando");
        Assert.True(ok.PedeAjuda);
    }

    [Fact]
    public void Alerta_encerrado_nao_aceita_checkin()
    {
        var alerta = Alerta.APartirDaPrevisao(new PrevisaoRisco(Hoje, 0.9, "teste", Hoje));
        alerta.Encerrar();
        var voluntario = new Voluntario("Vizinho Teste", "11900000011", "Bela Vista");

        Assert.Throws<DomainException>(() =>
            CheckIn.Registrar(alerta, voluntario, NovoCidadao(), SituacaoCheckIn.Ok, null));
    }
}
