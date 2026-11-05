using LuzVital.Domain.Abstractions;
using LuzVital.Domain.Entities;
using LuzVital.Infrastructure.Data;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;

namespace LuzVital.Infrastructure.Servicos;

public record ResultadoPrevisao(PrevisaoRisco Previsao, Alerta? Alerta, int PessoasNotificadas);

public interface IServicoAlertas
{
    /// <summary>Grava a previsão do ML e, se o risco não for baixo, abre o alerta e avisa todo mundo.</summary>
    Task<ResultadoPrevisao> ProcessarPrevisaoAsync(DateOnly data, double probabilidade, string versaoModelo,
        CancellationToken ct = default);
}

public class ServicoAlertas : IServicoAlertas
{
    private readonly LuzVitalDbContext _db;
    private readonly IEnumerable<INotificador> _notificadores;
    private readonly IRelogio _relogio;
    private readonly ILogger<ServicoAlertas> _logger;

    public ServicoAlertas(LuzVitalDbContext db, IEnumerable<INotificador> notificadores, IRelogio relogio,
        ILogger<ServicoAlertas> logger)
    {
        _db = db;
        _notificadores = notificadores;
        _relogio = relogio;
        _logger = logger;
    }

    public async Task<ResultadoPrevisao> ProcessarPrevisaoAsync(DateOnly data, double probabilidade,
        string versaoModelo, CancellationToken ct = default)
    {
        var previsao = new PrevisaoRisco(data, probabilidade, versaoModelo, _relogio.Hoje);
        _db.Previsoes.Add(previsao);

        if (!previsao.DeveGerarAlerta)
        {
            await _db.SaveChangesAsync(ct);
            return new ResultadoPrevisao(previsao, null, 0);
        }

        // Um alerta por dia: uma previsão nova para o mesmo dia atualiza o cenário, não duplica aviso.
        var jaExiste = await _db.Alertas.AnyAsync(a => a.Data == data && a.Ativo && a.Bairro == null, ct);
        if (jaExiste)
        {
            await _db.SaveChangesAsync(ct);
            return new ResultadoPrevisao(previsao, null, 0);
        }

        var alerta = Alerta.APartirDaPrevisao(previsao);
        _db.Alertas.Add(alerta);
        await _db.SaveChangesAsync(ct);

        var notificadas = await NotificarAsync(alerta, ct);
        _logger.LogInformation("Alerta {AlertaId} ({Nivel}) para {Data}: {Qtd} pessoas avisadas",
            alerta.Id, alerta.Nivel, alerta.Data, notificadas);

        return new ResultadoPrevisao(previsao, alerta, notificadas);
    }

    private async Task<int> NotificarAsync(Alerta alerta, CancellationToken ct)
    {
        // Prioritários (pouca autonomia sem energia) recebem primeiro.
        var cidadaos = await _db.Cidadaos
            .OrderBy(c => c.AutonomiaHoras)
            .ToListAsync(ct);

        var voluntarios = await _db.Voluntarios
            .Where(v => v.Disponivel)
            .ToListAsync(ct);

        var destinatarios = cidadaos.Cast<Pessoa>().Concat(voluntarios)
            .Where(p => alerta.Abrange(p.Bairro))
            .ToList();

        foreach (var pessoa in destinatarios)
        {
            var texto = $"{pessoa.SaudacaoAlerta()} {alerta.Mensagem}";
            await Task.WhenAll(_notificadores.Select(n => n.EnviarAsync(pessoa, texto, ct)));
        }

        return destinatarios.Count;
    }
}
