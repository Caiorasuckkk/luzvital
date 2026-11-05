using LuzVital.Api.Dtos;
using LuzVital.Domain.Abstractions;
using LuzVital.Domain.Entities;
using LuzVital.Infrastructure.Data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace LuzVital.Api.Controllers;

/// <summary>Alertas de risco de apagão. É daqui que o app lê o "risco de hoje".</summary>
[ApiController]
[Route("api/alertas")]
[Produces("application/json")]
public class AlertasController : ControllerBase
{
    private readonly LuzVitalDbContext _db;
    private readonly IRelogio _relogio;

    public AlertasController(LuzVitalDbContext db, IRelogio relogio)
    {
        _db = db;
        _relogio = relogio;
    }

    /// <summary>Alertas ativos de hoje em diante. Com bairro, traz os da cidade toda + os do bairro.</summary>
    [HttpGet]
    public async Task<ActionResult<IEnumerable<AlertaResponse>>> Ativos([FromQuery] string? bairro, CancellationToken ct)
    {
        var hoje = _relogio.Hoje;
        var query = _db.Alertas.AsNoTracking().Where(a => a.Ativo && a.Data >= hoje);

        if (!string.IsNullOrWhiteSpace(bairro))
        {
            var b = Pessoa.NormalizarBairro(bairro);
            query = query.Where(a => a.Bairro == null || a.Bairro == b);
        }

        var lista = await query.OrderBy(a => a.Data).ToListAsync(ct);
        return Ok(lista.OrderBy(a => a.Data).ThenByDescending(a => a.Nivel).Select(AlertaResponse.De));
    }

    [HttpGet("{id:int}")]
    public async Task<ActionResult<AlertaResponse>> Obter(int id, CancellationToken ct)
    {
        var a = await _db.Alertas.AsNoTracking().FirstOrDefaultAsync(x => x.Id == id, ct);
        return a is null ? NotFound() : Ok(AlertaResponse.De(a));
    }

    /// <summary>Abre um alerta à mão para um bairro (ex.: a luz já caiu ali).</summary>
    [HttpPost]
    [ProducesResponseType(typeof(AlertaResponse), StatusCodes.Status201Created)]
    public async Task<ActionResult<AlertaResponse>> CriarManual(AlertaManualRequest req, CancellationToken ct)
    {
        var a = Alerta.Manual(req.Data, req.Nivel, req.Bairro, req.Mensagem);
        _db.Alertas.Add(a);
        await _db.SaveChangesAsync(ct);
        return CreatedAtAction(nameof(Obter), new { id = a.Id }, AlertaResponse.De(a));
    }

    /// <summary>Encerra o alerta quando a energia volta.</summary>
    [HttpPost("{id:int}/encerrar")]
    public async Task<ActionResult<AlertaResponse>> Encerrar(int id, CancellationToken ct)
    {
        var a = await _db.Alertas.FirstOrDefaultAsync(x => x.Id == id, ct);
        if (a is null)
            return NotFound();

        a.Encerrar();
        await _db.SaveChangesAsync(ct);
        return Ok(AlertaResponse.De(a));
    }
}
