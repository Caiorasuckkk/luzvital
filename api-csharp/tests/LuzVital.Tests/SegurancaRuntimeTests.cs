using System.Text;
using LuzVital.Api.Seguranca;
using LuzVital.Domain;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace LuzVital.Tests;

public class SegurancaRuntimeTests
{
    private static readonly OpcoesSeguranca Opcoes = new()
    {
        ExcecoesExposicao =
        {
            new ExcecaoExposicao { Campo = "dependencia", Rotas = { "/api/cidadaos" }, Motivo = "teste" }
        }
    };

    private static async Task<(int Status, string Corpo)> PassarPeloGuarda(FilaEventosSeguranca fila, string rota,
        object resposta)
    {
        var ctx = new DefaultHttpContext { RequestServices = new ServiceCollection().BuildServiceProvider() };
        ctx.Request.Method = "GET";
        ctx.Request.Path = rota;
        var saida = new MemoryStream();
        ctx.Response.Body = saida;

        var guarda = new GuardaRespostas(c => c.Response.WriteAsJsonAsync(resposta), fila, Options.Create(Opcoes));
        await guarda.InvokeAsync(ctx);

        return (ctx.Response.StatusCode, Encoding.UTF8.GetString(saida.ToArray()));
    }

    [Fact]
    public async Task Guarda_bloqueia_resposta_com_cpf_inteiro()
    {
        var fila = new FilaEventosSeguranca();

        var (status, corpo) = await PassarPeloGuarda(fila, "/api/teste", new { nome = "Teste", cpf = "52998224725" });

        Assert.Equal(500, status);
        Assert.Contains(GuardaRespostas.TituloBloqueio, corpo);
        Assert.DoesNotContain("52998224725", corpo);
        Assert.True(fila.Leitor.TryRead(out var evento));
        Assert.Equal(TipoEventoSeguranca.RespostaBloqueada, evento!.Tipo);
        Assert.DoesNotContain("52998224725", evento.DescricaoTecnica);
    }

    [Fact]
    public async Task Guarda_deixa_passar_resposta_mascarada_e_excecao_aceita()
    {
        var fila = new FilaEventosSeguranca();
        var resposta = new { cpfMascarado = "529.***.***-25", dependencia = "OxigenioDomiciliar" };

        var (status, corpo) = await PassarPeloGuarda(fila, "/api/cidadaos", resposta);

        Assert.Equal(200, status);
        Assert.Contains("OxigenioDomiciliar", corpo);
        Assert.False(fila.Leitor.TryRead(out _));
    }

    [Fact]
    public void Log_com_cpf_inteiro_sai_mascarado()
    {
        var fila = new FilaEventosSeguranca();
        var interno = new ProvedorDeTeste();
        using var provedor = new ProvedorLogSeguro(new[] { interno }, fila, http: null);

        provedor.CreateLogger("Teste").LogWarning("Conferindo o CPF {Cpf}", "52998224725");

        Assert.Equal("Conferindo o CPF 529.***.***-25", Assert.Single(interno.Mensagens));
        Assert.True(fila.Leitor.TryRead(out var evento));
        Assert.Equal(TipoEventoSeguranca.LogMascarado, evento!.Tipo);
        Assert.Equal(NivelSeguranca.Amarelo, LuzVital.Domain.Entities.EventoSeguranca.NivelDe(evento.Tipo));
    }

    private sealed class ProvedorDeTeste : ILoggerProvider, ILogger
    {
        public List<string> Mensagens { get; } = new();
        public ILogger CreateLogger(string categoria) => this;
        public IDisposable? BeginScope<TState>(TState state) where TState : notnull => null;
        public bool IsEnabled(LogLevel nivel) => true;

        public void Log<TState>(LogLevel nivel, EventId id, TState state, Exception? ex,
            Func<TState, Exception?, string> formatar) => Mensagens.Add(formatar(state, ex));

        public void Dispose() { }
    }
}
