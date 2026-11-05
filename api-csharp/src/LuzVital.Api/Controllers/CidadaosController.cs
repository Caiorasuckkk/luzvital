using LuzVital.Api.Dtos;
using LuzVital.Domain;
using LuzVital.Domain.Entities;
using LuzVital.Infrastructure.Data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace LuzVital.Api.Controllers;

/// <summary>Cadastro de quem depende de energia em casa.</summary>
[ApiController]
[Route("api/cidadaos")]
[Produces("application/json")]
public class CidadaosController : ControllerBase
{
    private readonly LuzVitalDbContext _db;

    public CidadaosController(LuzVitalDbContext db) => _db = db;

    /// <summary>Lista cidadãos, com filtro opcional por bairro. Prioritários primeiro.</summary>
    [HttpGet]
    public async Task<ActionResult<IEnumerable<CidadaoResponse>>> Listar([FromQuery] string? bairro, CancellationToken ct)
    {
        var query = _db.Cidadaos.AsNoTracking();
        if (!string.IsNullOrWhiteSpace(bairro))
        {
            var b = Pessoa.NormalizarBairro(bairro);
            query = query.Where(c => c.Bairro == b);
        }

        var lista = await query.OrderBy(c => c.AutonomiaHoras).ThenBy(c => c.Nome).ToListAsync(ct);
        return Ok(lista.Select(CidadaoResponse.De));
    }

    [HttpGet("{id:int}")]
    public async Task<ActionResult<CidadaoResponse>> Obter(int id, CancellationToken ct)
    {
        var c = await _db.Cidadaos.AsNoTracking().FirstOrDefaultAsync(x => x.Id == id, ct);
        return c is null ? NotFound() : Ok(CidadaoResponse.De(c));
    }

    /// <summary>Cadastra um cidadão. CPF precisa ser válido e não pode repetir.</summary>
    [HttpPost]
    [ProducesResponseType(typeof(CidadaoResponse), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status409Conflict)]
    public async Task<ActionResult<CidadaoResponse>> Criar(CidadaoRequest req, CancellationToken ct)
    {
        var cpf = Cpf.SomenteDigitos(req.Cpf);
        if (await _db.Cidadaos.AnyAsync(c => c.Cpf == cpf, ct))
            return Conflict(new ProblemDetails { Title = "CPF já cadastrado." });

        var cidadao = new Cidadao(req.Nome, req.Cpf, req.Telefone, req.Endereco, req.Bairro,
            req.Dependencia, req.AutonomiaHoras);

        _db.Cidadaos.Add(cidadao);
        await _db.SaveChangesAsync(ct);

        return CreatedAtAction(nameof(Obter), new { id = cidadao.Id }, CidadaoResponse.De(cidadao));
    }

    /// <summary>Atualiza contato e necessidade. O CPF não muda.</summary>
    [HttpPut("{id:int}")]
    public async Task<ActionResult<CidadaoResponse>> Atualizar(int id, CidadaoRequest req, CancellationToken ct)
    {
        var c = await _db.Cidadaos.FirstOrDefaultAsync(x => x.Id == id, ct);
        if (c is null)
            return NotFound();

        c.AtualizarContato(req.Nome, req.Telefone, req.Bairro);
        c.AtualizarNecessidade(req.Endereco, req.Dependencia, req.AutonomiaHoras);
        await _db.SaveChangesAsync(ct);

        return Ok(CidadaoResponse.De(c));
    }

    [HttpDelete("{id:int}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<IActionResult> Remover(int id, CancellationToken ct)
    {
        var c = await _db.Cidadaos.FirstOrDefaultAsync(x => x.Id == id, ct);
        if (c is null)
            return NotFound();

        if (await _db.CheckIns.AnyAsync(ci => ci.CidadaoId == id, ct))
            return Conflict(new ProblemDetails { Title = "Cidadão tem check-ins registrados e não pode ser removido." });

        _db.Cidadaos.Remove(c);
        await _db.SaveChangesAsync(ct);
        return NoContent();
    }
}
