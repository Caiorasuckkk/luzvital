using LuzVital.Api.Dtos;
using LuzVital.Domain.Entities;
using LuzVital.Infrastructure.Data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace LuzVital.Api.Controllers;

/// <summary>Voluntário registra que checou um cidadão durante um alerta.</summary>
[ApiController]
[Route("api/checkins")]
[Produces("application/json")]
public class CheckInsController : ControllerBase
{
    private readonly LuzVitalDbContext _db;

    public CheckInsController(LuzVitalDbContext db) => _db = db;

    [HttpPost]
    [ProducesResponseType(typeof(CheckInResponse), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status422UnprocessableEntity)]
    public async Task<ActionResult<CheckInResponse>> Registrar(CheckInRequest req, CancellationToken ct)
    {
        // As três buscas são independentes, mas o DbContext não aceita consultas em paralelo.
        var alerta = await _db.Alertas.FirstOrDefaultAsync(a => a.Id == req.AlertaId, ct);
        var voluntario = await _db.Voluntarios.FirstOrDefaultAsync(v => v.Id == req.VoluntarioId, ct);
        var cidadao = await _db.Cidadaos.FirstOrDefaultAsync(c => c.Id == req.CidadaoId, ct);

        if (alerta is null || voluntario is null || cidadao is null)
            return NotFound(new ProblemDetails { Title = "Alerta, voluntário ou cidadão não encontrado." });

        var checkIn = CheckIn.Registrar(alerta, voluntario, cidadao, req.Situacao, req.Observacao);
        _db.CheckIns.Add(checkIn);
        await _db.SaveChangesAsync(ct);

        return CreatedAtAction(nameof(PorAlerta), new { alertaId = checkIn.AlertaId }, CheckInResponse.De(checkIn));
    }

    /// <summary>Check-ins de um alerta, mais recentes primeiro.</summary>
    [HttpGet]
    public async Task<ActionResult<IEnumerable<CheckInResponse>>> PorAlerta([FromQuery] int alertaId, CancellationToken ct)
    {
        var lista = await _db.CheckIns.AsNoTracking()
            .Where(c => c.AlertaId == alertaId)
            .OrderByDescending(c => c.RegistradoEm)
            .ToListAsync(ct);

        return Ok(lista.Select(CheckInResponse.De));
    }
}
