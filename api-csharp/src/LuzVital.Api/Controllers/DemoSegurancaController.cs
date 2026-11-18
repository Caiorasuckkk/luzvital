using LuzVital.Domain;
using Microsoft.AspNetCore.Mvc;

namespace LuzVital.Api.Controllers;

/// <summary>
/// Rotas que vazam dado pessoal DE PROPÓSITO, para demonstrar a camada de segurança em tempo real.
/// Só existe em Development (ver Program.cs). Usa os dados fictícios do seed (Maria Aparecida).
/// Fica fora da análise estática do cyber/ (cyber/exclusoes.json).
/// </summary>
[ApiController]
[Route("api/demo-seguranca")]
[Produces("application/json")]
public class DemoSegurancaController : ControllerBase
{
    private static readonly string CpfFicticio = Cpf.ComDigitos("100000001");
    private const string EnderecoFicticio = "Rua Exemplo, 100";

    private readonly ILogger<DemoSegurancaController> _logger;

    public DemoSegurancaController(ILogger<DemoSegurancaController> logger) => _logger = logger;

    /// <summary>Tenta logar um CPF inteiro. O log sai mascarado.</summary>
    [HttpGet("log-cpf")]
    public IActionResult LogCpf()
    {
        _logger.LogWarning("Conferindo o cadastro do CPF {Cpf}", CpfFicticio);
        return Ok(new { mensagem = "O controller tentou logar um CPF inteiro. Confira no console: ele saiu mascarado." });
    }

    /// <summary>Tenta devolver um CPF cru na resposta. O guarda bloqueia com 500.</summary>
    [HttpGet("resposta-cpf")]
    public IActionResult RespostaCpf() =>
        Ok(new { nome = "Maria Aparecida (fictícia)", cpf = CpfFicticio });

    /// <summary>Lança uma exceção com um endereço na mensagem. O tratamento de erros mascara antes de logar.</summary>
    [HttpGet("excecao-endereco")]
    public IActionResult ExcecaoEndereco() =>
        throw new InvalidOperationException($"Falha ao calcular a rota do voluntário até {EnderecoFicticio}");
}

/// <summary>Remove o <see cref="DemoSegurancaController"/> da aplicação fora de Development.</summary>
public sealed class SemControllerDeDemo : Microsoft.AspNetCore.Mvc.ApplicationParts.IApplicationFeatureProvider<
    Microsoft.AspNetCore.Mvc.Controllers.ControllerFeature>
{
    public void PopulateFeature(IEnumerable<Microsoft.AspNetCore.Mvc.ApplicationParts.ApplicationPart> partes,
        Microsoft.AspNetCore.Mvc.Controllers.ControllerFeature feature)
    {
        var demo = feature.Controllers.FirstOrDefault(c => c.AsType() == typeof(DemoSegurancaController));
        if (demo is not null)
            feature.Controllers.Remove(demo);
    }
}
