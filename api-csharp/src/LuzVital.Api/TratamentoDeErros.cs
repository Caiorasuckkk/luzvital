using LuzVital.Domain;
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;

namespace LuzVital.Api;

/// <summary>Converte exceções em respostas HTTP padronizadas (ProblemDetails).</summary>
public class TratamentoDeErros : IExceptionHandler
{
    private readonly ILogger<TratamentoDeErros> _logger;

    public TratamentoDeErros(ILogger<TratamentoDeErros> logger) => _logger = logger;

    public async ValueTask<bool> TryHandleAsync(HttpContext http, Exception ex, CancellationToken ct)
    {
        var (status, titulo) = ex switch
        {
            DomainException => (StatusCodes.Status422UnprocessableEntity, ex.Message),
            KeyNotFoundException => (StatusCodes.Status404NotFound, ex.Message),
            _ => (StatusCodes.Status500InternalServerError, "Erro inesperado. Tente de novo.")
        };

        if (status == StatusCodes.Status500InternalServerError)
            _logger.LogError(ex, "Erro não tratado em {Path}", http.Request.Path);

        http.Response.StatusCode = status;
        await http.Response.WriteAsJsonAsync(new ProblemDetails
        {
            Status = status,
            Title = titulo,
            Instance = http.Request.Path
        }, ct);

        return true;
    }
}
