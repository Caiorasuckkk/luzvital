using LuzVital.Domain;
using LuzVital.Domain.Abstractions;
using LuzVital.Domain.Entities;
using LuzVital.Infrastructure.Data;
using LuzVital.Infrastructure.Servicos;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;

namespace LuzVital.Tests;

public class ServicoAlertasTests
{
    private sealed class RelogioFixo : IRelogio
    {
        public DateOnly Hoje { get; init; } = new(2026, 11, 10);
    }

    /// <summary>Guarda quem recebeu mensagem, para o teste conferir.</summary>
    private sealed class NotificadorFake : INotificador
    {
        public List<Pessoa> Enviados { get; } = new();
        public string Canal => "Fake";

        public Task EnviarAsync(Pessoa destinatario, string mensagem, CancellationToken ct = default)
        {
            Enviados.Add(destinatario);
            return Task.CompletedTask;
        }
    }

    private static async Task<LuzVitalDbContext> NovoBancoAsync()
    {
        var opcoes = new DbContextOptionsBuilder<LuzVitalDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options;

        var db = new LuzVitalDbContext(opcoes);
        await SeedDados.PopularAsync(db);
        return db;
    }

    private static ServicoAlertas NovoServico(LuzVitalDbContext db, NotificadorFake fake) =>
        new(db, new[] { fake }, new RelogioFixo(), NullLogger<ServicoAlertas>.Instance);

    [Fact]
    public async Task Risco_alto_abre_alerta_e_avisa_prioritarios_primeiro()
    {
        await using var db = await NovoBancoAsync();
        var fake = new NotificadorFake();

        var r = await NovoServico(db, fake).ProcessarPrevisaoAsync(new DateOnly(2026, 11, 11), 0.85, "teste");

        Assert.NotNull(r.Alerta);
        Assert.Equal(NivelRisco.Alto, r.Alerta!.Nivel);
        Assert.Equal(6, r.PessoasNotificadas); // 4 cidadãos + 2 voluntários do seed
        Assert.IsType<Cidadao>(fake.Enviados[0]);
        Assert.Equal(2, ((Cidadao)fake.Enviados[0]).AutonomiaHoras);
    }

    [Fact]
    public async Task Risco_baixo_so_grava_a_previsao()
    {
        await using var db = await NovoBancoAsync();
        var fake = new NotificadorFake();

        var r = await NovoServico(db, fake).ProcessarPrevisaoAsync(new DateOnly(2026, 11, 11), 0.15, "teste");

        Assert.Null(r.Alerta);
        Assert.Empty(fake.Enviados);
        Assert.Equal(1, await db.Previsoes.CountAsync());
    }

    [Fact]
    public async Task Segunda_previsao_do_mesmo_dia_nao_duplica_alerta()
    {
        await using var db = await NovoBancoAsync();
        var servico = NovoServico(db, new NotificadorFake());
        var dia = new DateOnly(2026, 11, 11);

        await servico.ProcessarPrevisaoAsync(dia, 0.5, "teste");
        await servico.ProcessarPrevisaoAsync(dia, 0.9, "teste");

        Assert.Equal(1, await db.Alertas.CountAsync());
        Assert.Equal(2, await db.Previsoes.CountAsync());
    }

    [Fact]
    public async Task Painel_lista_quem_ainda_nao_foi_checado()
    {
        await using var db = await NovoBancoAsync();
        var r = await NovoServico(db, new NotificadorFake())
            .ProcessarPrevisaoAsync(new DateOnly(2026, 11, 11), 0.9, "teste");

        var voluntaria = await db.Voluntarios.FirstAsync(v => v.Bairro == "BELA VISTA");
        var maria = await db.Cidadaos.FirstAsync(c => c.Bairro == "BELA VISTA" && c.AutonomiaHoras == 2);
        db.CheckIns.Add(CheckIn.Registrar(r.Alerta!, voluntaria, maria, SituacaoCheckIn.Ok, null));
        await db.SaveChangesAsync();

        var pendentes = await new ServicoPainel(db).CidadaosSemCheckInAsync(r.Alerta!.Id, "Bela Vista");

        Assert.Single(pendentes);
        Assert.DoesNotContain(pendentes, p => p.Id == maria.Id);
    }
}
