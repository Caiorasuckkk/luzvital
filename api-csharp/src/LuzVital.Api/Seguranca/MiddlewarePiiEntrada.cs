using System.Text;
using LuzVital.Domain;

namespace LuzVital.Api.Seguranca;

/// <summary>Campo da requisição marcado como dado pessoal. Fica em HttpContext.Items[<see cref="MiddlewarePiiEntrada.ChaveItens"/>].</summary>
public sealed record CampoPii(string? Campo, string Tipo);

/// <summary>
/// Em POST e PUT com JSON, lê o corpo, marca os campos com dado pessoal e loga só a versão mascarada.
/// O corpo volta para o início e chega igual ao controller.
/// </summary>
public sealed class MiddlewarePiiEntrada
{
    public const string ChaveItens = "Seguranca.CamposPii";

    private readonly RequestDelegate _next;
    private readonly ILogger<MiddlewarePiiEntrada> _logger;
    private readonly FilaEventosSeguranca _fila;

    public MiddlewarePiiEntrada(RequestDelegate next, ILogger<MiddlewarePiiEntrada> logger, FilaEventosSeguranca fila)
    {
        _next = next;
        _logger = logger;
        _fila = fila;
    }

    public async Task InvokeAsync(HttpContext ctx)
    {
        var req = ctx.Request;
        if ((HttpMethods.IsPost(req.Method) || HttpMethods.IsPut(req.Method)) && EhJson(req.ContentType))
        {
            req.EnableBuffering();
            string corpo;
            using (var leitor = new StreamReader(req.Body, Encoding.UTF8, detectEncodingFromByteOrderMarks: false,
                       bufferSize: 4096, leaveOpen: true))
                corpo = await leitor.ReadToEndAsync(ctx.RequestAborted);
            req.Body.Position = 0;

            if (!string.IsNullOrWhiteSpace(corpo))
                Analisar(ctx, corpo);
        }

        await _next(ctx);
    }

    private void Analisar(HttpContext ctx, string corpo)
    {
        var resultado = MotorPii.AnalisarJson(corpo);
        if (resultado.Achados.Count == 0)
            return;

        ctx.Items[ChaveItens] = resultado.Achados.Select(a => new CampoPii(a.Campo, a.Tipo)).ToList();

        var rota = $"{ctx.Request.Method} {ctx.Request.Path}";
        var tipos = string.Join(", ", resultado.Achados.Select(a => a.Tipo).Distinct());
        _logger.LogInformation("Entrada {Rota} com dado pessoal ({Tipos}): {Corpo}", rota, tipos, resultado.JsonMascarado);

        var campos = string.Join(", ", resultado.Achados.Select(a => $"{a.Campo ?? "?"}={a.Mascarado}"));
        _fila.Registrar(TipoEventoSeguranca.PiiNaEntrada, rota, resultado.Achados,
            $"{rota} recebeu {tipos} nos campos {campos}. O log guardou só a versão mascarada.");
    }

    internal static bool EhJson(string? contentType) =>
        contentType is not null && contentType.Contains("json", StringComparison.OrdinalIgnoreCase);
}
