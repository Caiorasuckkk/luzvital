using LuzVital.Infrastructure.Servicos;
using Microsoft.AspNetCore.Mvc;

namespace LuzVital.Api.Controllers;

/// <summary>Visão de quem coordena os voluntários durante um apagão.</summary>
[ApiController]
[Route("api/painel")]
[Produces("application/json")]
public class PainelController : ControllerBase
{
    private readonly IServicoPainel _painel;

    public PainelController(IServicoPainel painel) => _painel = painel;

    /// <summary>Cidadãos que ainda ninguém checou nesse alerta, prioritários primeiro.</summary>
    [HttpGet("sem-checkin")]
    public async Task<ActionResult<IEnumerable<CidadaoPendente>>> SemCheckIn([FromQuery] int alertaId,
        [FromQuery] string? bairro, CancellationToken ct) =>
        Ok(await _painel.CidadaosSemCheckInAsync(alertaId, bairro, ct));

    /// <summary>Resumo por bairro: quantos cidadãos, prioritários, checados, pedindo ajuda e pendentes.</summary>
    [HttpGet("resumo")]
    public async Task<ActionResult<IEnumerable<ResumoBairro>>> Resumo([FromQuery] int alertaId, CancellationToken ct) =>
        Ok(await _painel.ResumoPorBairroAsync(alertaId, ct));
}
