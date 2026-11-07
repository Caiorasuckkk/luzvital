using LuzVital.Api.Dtos;
using LuzVital.Infrastructure.Data;
using LuzVital.Infrastructure.Servicos;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace LuzVital.Api.Controllers;

/// <summary>Ponto de entrada do modelo de ML: recebe a previsão do dia.</summary>
[ApiController]
[Route("api/previsoes")]
[Produces("application/json")]
public class PrevisoesController : ControllerBase
{
    private readonly IServicoAlertas _alertas;
    private readonly LuzVitalDbContext _db;

    public PrevisoesController(IServicoAlertas alertas, LuzVitalDbContext db)
    {
        _alertas = alertas;
        _db = db;
    }

    /// <summary>
    /// Registra a previsão. Probabilidade a partir de 0,4 abre alerta de atenção; a partir de 0,7, alerta alto.
    /// Quando abre alerta, avisa cidadãos (prioritários primeiro) e voluntários.
    /// </summary>
    [HttpPost]
    [ProducesResponseType(typeof(PrevisaoResponse), StatusCodes.Status201Created)]
    public async Task<ActionResult<PrevisaoResponse>> Registrar(PrevisaoRequest req, CancellationToken ct)
    {
        var r = await _alertas.ProcessarPrevisaoAsync(req.Data, req.Probabilidade, req.VersaoModelo, ct);
        var resposta = new PrevisaoResponse(r.Previsao.Id, r.Previsao.Data, r.Previsao.Probabilidade,
            r.Previsao.Nivel, r.Previsao.VersaoModelo, r.Alerta?.Id, r.PessoasNotificadas);

        return CreatedAtAction(nameof(Listar), null, resposta);
    }

    /// <summary>Últimas previsões recebidas.</summary>
    [HttpGet]
    public async Task<ActionResult<IEnumerable<PrevisaoResponse>>> Listar([FromQuery] int limite = 30, CancellationToken ct = default)
    {
        limite = Math.Clamp(limite, 1, 200);
        var lista = await _db.Previsoes.AsNoTracking()
            .OrderByDescending(p => p.Data)
            .ThenByDescending(p => p.RecebidaEm)
            .Take(limite)
            .Select(p => new PrevisaoResponse(p.Id, p.Data, p.Probabilidade, p.Nivel, p.VersaoModelo, null, 0))
            .ToListAsync(ct);

        return Ok(lista);
    }
}
