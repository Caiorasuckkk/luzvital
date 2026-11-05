using LuzVital.Domain;
using LuzVital.Domain.Entities;
using LuzVital.Infrastructure.Data;
using Microsoft.EntityFrameworkCore;

namespace LuzVital.Infrastructure.Servicos;

public record CidadaoPendente(int Id, string Nome, string Bairro, TipoDependencia Dependencia, int AutonomiaHoras);

public record ResumoBairro(string Bairro, int Cidadaos, int Prioritarios, int Checados, int PedemAjuda, int Pendentes);

public interface IServicoPainel
{
    Task<IReadOnlyList<CidadaoPendente>> CidadaosSemCheckInAsync(int alertaId, string? bairro, CancellationToken ct = default);
    Task<IReadOnlyList<ResumoBairro>> ResumoPorBairroAsync(int alertaId, CancellationToken ct = default);
}

/// <summary>Consultas LINQ usadas no painel de quem coordena os voluntários durante um apagão.</summary>
public class ServicoPainel : IServicoPainel
{
    private readonly LuzVitalDbContext _db;

    public ServicoPainel(LuzVitalDbContext db) => _db = db;

    public async Task<IReadOnlyList<CidadaoPendente>> CidadaosSemCheckInAsync(int alertaId, string? bairro,
        CancellationToken ct = default)
    {
        var alerta = await _db.Alertas.AsNoTracking().FirstOrDefaultAsync(a => a.Id == alertaId, ct)
                     ?? throw new KeyNotFoundException($"Alerta {alertaId} não encontrado.");

        var query = _db.Cidadaos.AsNoTracking()
            .Where(c => !_db.CheckIns.Any(ci => ci.AlertaId == alertaId && ci.CidadaoId == c.Id));

        if (alerta.Bairro is not null)
            query = query.Where(c => c.Bairro == alerta.Bairro);

        if (!string.IsNullOrWhiteSpace(bairro))
        {
            var b = Pessoa.NormalizarBairro(bairro);
            query = query.Where(c => c.Bairro == b);
        }

        return await query
            .OrderBy(c => c.AutonomiaHoras)
            .ThenBy(c => c.Nome)
            .Select(c => new CidadaoPendente(c.Id, c.Nome, c.Bairro, c.Dependencia, c.AutonomiaHoras))
            .ToListAsync(ct);
    }

    public async Task<IReadOnlyList<ResumoBairro>> ResumoPorBairroAsync(int alertaId, CancellationToken ct = default)
    {
        if (!await _db.Alertas.AnyAsync(a => a.Id == alertaId, ct))
            throw new KeyNotFoundException($"Alerta {alertaId} não encontrado.");

        var cidadaos = await _db.Cidadaos.AsNoTracking()
            .Select(c => new { c.Id, c.Bairro, c.AutonomiaHoras })
            .ToListAsync(ct);

        // Último check-in de cada cidadão nesse alerta.
        var checkIns = await _db.CheckIns.AsNoTracking()
            .Where(ci => ci.AlertaId == alertaId)
            .ToListAsync(ct);

        var porCidadao = checkIns
            .GroupBy(ci => ci.CidadaoId)
            .ToDictionary(g => g.Key, g => g.OrderByDescending(ci => ci.RegistradoEm).First());

        return cidadaos
            .GroupBy(c => c.Bairro)
            .Select(g => new ResumoBairro(
                g.Key,
                g.Count(),
                g.Count(c => c.AutonomiaHoras <= Cidadao.LimitePrioridadeHoras),
                g.Count(c => porCidadao.ContainsKey(c.Id)),
                g.Count(c => porCidadao.TryGetValue(c.Id, out var ci) && ci.PedeAjuda),
                g.Count(c => !porCidadao.ContainsKey(c.Id))))
            .OrderByDescending(r => r.Pendentes)
            .ThenBy(r => r.Bairro)
            .ToList();
    }
}
