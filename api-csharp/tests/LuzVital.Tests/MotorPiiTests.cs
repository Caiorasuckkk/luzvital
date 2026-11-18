using LuzVital.Api.Seguranca;

namespace LuzVital.Tests;

public class MotorPiiTests
{
    [Fact]
    public void Cpf_valido_e_encontrado_e_mascarado()
    {
        var achado = Assert.Single(MotorPii.Analisar("cadastro do CPF 529.982.247-25 recebido"));
        Assert.Equal("CPF", achado.Tipo);
        Assert.Equal("529.***.***-25", achado.Mascarado);
        Assert.Equal("cadastro do CPF 529.***.***-25 recebido", MotorPii.Mascarar("cadastro do CPF 529.982.247-25 recebido"));
    }

    [Fact]
    public void Cpf_com_digito_errado_nao_conta() =>
        Assert.DoesNotContain(MotorPii.Analisar("protocolo 529.982.247-26"), a => a.Tipo == "CPF");

    [Theory]
    [InlineData("CPF 529.***.***-25")]
    [InlineData("telefone (11) *****-0001")]
    public void Valor_ja_mascarado_e_ignorado(string texto) =>
        Assert.Empty(MotorPii.Analisar(texto));

    [Fact]
    public void Rg_e_encontrado()
    {
        var achado = Assert.Single(MotorPii.Analisar("RG 12.345.678-9"));
        Assert.Equal("RG", achado.Tipo);
        Assert.DoesNotContain("345", achado.Mascarado);
    }

    [Fact]
    public void Campo_senha_e_dado_sensivel_pelo_nome()
    {
        var r = MotorPii.AnalisarJson("""{"nome":"Teste","senha":"abc123"}""");

        var achado = Assert.Single(r.Achados);
        Assert.Equal("Senha", achado.Tipo);
        Assert.Equal("senha", achado.Campo);
        Assert.Contains("\"senha\":\"***\"", r.JsonMascarado);
        Assert.DoesNotContain("abc123", r.JsonMascarado);
    }

    [Fact]
    public void Json_mascarado_mantem_campos_sem_dado_pessoal()
    {
        var r = MotorPii.AnalisarJson("""{"nome":"Teste","cpf":"52998224725","bairro":"Mooca"}""");

        Assert.Contains("\"cpf\":\"529.***.***-25\"", r.JsonMascarado);
        Assert.Contains("\"bairro\":\"Mooca\"", r.JsonMascarado);
    }
}
