using LuzVital.Domain;
using LuzVital.Infrastructure.Data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace LuzVital.Api.Controllers;

public record ResumoSeguranca(NivelSeguranca Farol, DateTime Desde, int Total,
    IReadOnlyDictionary<TipoEventoSeguranca, int> PorTipo);

public record EventoSegurancaResponse(int Id, DateTime OcorridoEm, TipoEventoSeguranca Tipo, NivelSeguranca Nivel,
    string Rota, string TiposDeDado, string MensagemCidadao, string DescricaoTecnica, string ModoIa);

/// <summary>Farol da camada de segurança em tempo real (lido pelo painel-seguranca.html).</summary>
[ApiController]
[Route("api/seguranca")]
[Produces("application/json")]
public class SegurancaController : ControllerBase
{
    private readonly LuzVitalDbContext _db;
    private readonly IWebHostEnvironment _env;

    public SegurancaController(LuzVitalDbContext db, IWebHostEnvironment env)
    {
        _db = db;
        _env = env;
    }

    /// <summary>Farol das últimas 24h: o pior nível registrado (Verde se não houve nada) e as contagens por tipo.</summary>
    [HttpGet("resumo")]
    public async Task<ActionResult<ResumoSeguranca>> Resumo(CancellationToken ct)
    {
        var desde = DateTime.UtcNow.AddHours(-24);
        var eventos = await _db.EventosSeguranca.AsNoTracking()
            .Where(e => e.OcorridoEm >= desde)
            .Select(e => new { e.Tipo, e.Nivel })
            .ToListAsync(ct);

        var farol = eventos.Count == 0 ? NivelSeguranca.Verde : eventos.Max(e => e.Nivel);
        var porTipo = Enum.GetValues<TipoEventoSeguranca>()
            .ToDictionary(t => t, t => eventos.Count(e => e.Tipo == t));

        return Ok(new ResumoSeguranca(farol, desde, eventos.Count, porTipo));
    }

    /// <summary>Últimos eventos, com a mensagem traduzida para o cidadão.</summary>
    [HttpGet("eventos")]
    public async Task<ActionResult<IEnumerable<EventoSegurancaResponse>>> Eventos([FromQuery] int limite = 50,
        CancellationToken ct = default)
    {
        var lista = await _db.EventosSeguranca.AsNoTracking()
            .OrderByDescending(e => e.Id)
            .Take(Math.Clamp(limite, 1, 200))
            .Select(e => new EventoSegurancaResponse(e.Id, e.OcorridoEm, e.Tipo, e.Nivel, e.Rota, e.TiposDeDado,
                e.MensagemCidadao, e.DescricaoTecnica, e.ModoIa))
            .ToListAsync(ct);
        return Ok(lista);
    }

    /// <summary>Apaga todos os eventos (só em Development), para começar uma demonstração com o farol verde.</summary>
    [HttpPost("limpar")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<IActionResult> Limpar(CancellationToken ct)
    {
        if (!_env.IsDevelopment())
            return NotFound();

        await _db.EventosSeguranca.ExecuteDeleteAsync(ct);
        return NoContent();
    }
}
