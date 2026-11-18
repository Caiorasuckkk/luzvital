using System.Text;
using LuzVital.Domain;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;

namespace LuzVital.Api.Seguranca;

/// <summary>
/// Confere o corpo de toda resposta JSON de /api antes de ele sair. Se houver CPF, RG, telefone, e-mail,
/// endereço ou senha inteiros, ou dado de saúde num campo fora das exceções aceitas, a resposta é trocada
/// por um 500 e o evento é registrado.
/// </summary>
public sealed class GuardaRespostas
{
    public const string TituloBloqueio = "Resposta bloqueada para proteger dados pessoais";

    // Saúde só bloqueia pelo nome do campo: um alerta em texto livre que fale de oxigênio não é dado de uma pessoa.
    private static readonly HashSet<string> CamposDeSaude = new(StringComparer.OrdinalIgnoreCase)
        { "dependencia", "laudo", "diagnostico", "cid" };

    private readonly RequestDelegate _next;
    private readonly FilaEventosSeguranca _fila;
    private readonly OpcoesSeguranca _opcoes;

    public GuardaRespostas(RequestDelegate next, FilaEventosSeguranca fila, IOptions<OpcoesSeguranca> opcoes)
    {
        _next = next;
        _fila = fila;
        _opcoes = opcoes.Value;
    }

    public async Task InvokeAsync(HttpContext ctx)
    {
        if (!ctx.Request.Path.StartsWithSegments("/api"))
        {
            await _next(ctx);
            return;
        }

        var original = ctx.Response.Body;
        await using var buffer = new MemoryStream();
        ctx.Response.Body = buffer;
        try
        {
            await _next(ctx);
        }
        finally
        {
            ctx.Response.Body = original;
        }

        buffer.Position = 0;
        if (buffer.Length > 0 && MiddlewarePiiEntrada.EhJson(ctx.Response.ContentType))
        {
            var corpo = Encoding.UTF8.GetString(buffer.ToArray());
            var bloqueantes = MotorPii.AnalisarJson(corpo).Achados
                .Where(a => a.EhIdentificador || EhSaudeNaoPermitida(ctx.Request.Path, a))
                .ToList();

            if (bloqueantes.Count > 0)
            {
                await Bloquear(ctx, bloqueantes);
                return;
            }
        }

        await buffer.CopyToAsync(original, ctx.RequestAborted);
    }

    private bool EhSaudeNaoPermitida(PathString rota, AchadoPii a) =>
        a.Categoria == CategoriaPii.Saude && a.Campo is not null && CamposDeSaude.Contains(a.Campo) &&
        !_opcoes.Permitido(rota, a.Campo);

    private async Task Bloquear(HttpContext ctx, List<AchadoPii> achados)
    {
        var statusOriginal = ctx.Response.StatusCode;
        var rota = $"{ctx.Request.Method} {ctx.Request.Path}";
        var tipos = string.Join(", ", achados.Select(a => a.Tipo).Distinct());
        var campos = string.Join(", ", achados.Select(a => $"{a.Campo ?? "?"}={a.Mascarado}"));

        _fila.Registrar(TipoEventoSeguranca.RespostaBloqueada, rota, achados,
            $"A resposta {statusOriginal} de {rota} trazia {tipos} inteiro nos campos {campos}. " +
            "O guarda trocou a resposta por um erro 500 antes de ela sair.");

        ctx.Response.Headers.Clear();
        ctx.Response.StatusCode = StatusCodes.Status500InternalServerError;
        await ctx.Response.WriteAsJsonAsync(new ProblemDetails
        {
            Status = StatusCodes.Status500InternalServerError,
            Title = TituloBloqueio,
            Instance = ctx.Request.Path
        }, options: null, contentType: "application/problem+json", ctx.RequestAborted);
    }
}
