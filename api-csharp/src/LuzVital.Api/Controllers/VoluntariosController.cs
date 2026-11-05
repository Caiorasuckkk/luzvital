using LuzVital.Api.Dtos;
using LuzVital.Domain.Entities;
using LuzVital.Infrastructure.Data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace LuzVital.Api.Controllers;

/// <summary>Vizinhos que se oferecem para checar os cidadãos do bairro.</summary>
[ApiController]
[Route("api/voluntarios")]
[Produces("application/json")]
public class VoluntariosController : ControllerBase
{
    private readonly LuzVitalDbContext _db;

    public VoluntariosController(LuzVitalDbContext db) => _db = db;

    [HttpGet]
    public async Task<ActionResult<IEnumerable<VoluntarioResponse>>> Listar([FromQuery] string? bairro, CancellationToken ct)
    {
        var query = _db.Voluntarios.AsNoTracking();
        if (!string.IsNullOrWhiteSpace(bairro))
        {
            var b = Pessoa.NormalizarBairro(bairro);
            query = query.Where(v => v.Bairro == b);
        }

        var lista = await query.OrderBy(v => v.Nome).ToListAsync(ct);
        return Ok(lista.Select(VoluntarioResponse.De));
    }

    [HttpGet("{id:int}")]
    public async Task<ActionResult<VoluntarioResponse>> Obter(int id, CancellationToken ct)
    {
        var v = await _db.Voluntarios.AsNoTracking().FirstOrDefaultAsync(x => x.Id == id, ct);
        return v is null ? NotFound() : Ok(VoluntarioResponse.De(v));
    }

    [HttpPost]
    [ProducesResponseType(typeof(VoluntarioResponse), StatusCodes.Status201Created)]
    public async Task<ActionResult<VoluntarioResponse>> Criar(VoluntarioRequest req, CancellationToken ct)
    {
        var v = new Voluntario(req.Nome, req.Telefone, req.Bairro);
        _db.Voluntarios.Add(v);
        await _db.SaveChangesAsync(ct);
        return CreatedAtAction(nameof(Obter), new { id = v.Id }, VoluntarioResponse.De(v));
    }

    /// <summary>Liga ou desliga a disponibilidade do voluntário.</summary>
    [HttpPatch("{id:int}/disponibilidade")]
    public async Task<ActionResult<VoluntarioResponse>> Disponibilidade(int id, DisponibilidadeRequest req, CancellationToken ct)
    {
        var v = await _db.Voluntarios.FirstOrDefaultAsync(x => x.Id == id, ct);
        if (v is null)
            return NotFound();

        v.DefinirDisponibilidade(req.Disponivel);
        await _db.SaveChangesAsync(ct);
        return Ok(VoluntarioResponse.De(v));
    }
}
