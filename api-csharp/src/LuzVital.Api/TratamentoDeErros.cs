using LuzVital.Api.Seguranca;
using LuzVital.Domain;
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;

namespace LuzVital.Api;

/// <summary>Converte exceções em respostas HTTP padronizadas (ProblemDetails).</summary>
public class TratamentoDeErros : IExceptionHandler
{
    private readonly ILogger<TratamentoDeErros> _logger;
    private readonly FilaEventosSeguranca _fila;

    public TratamentoDeErros(ILogger<TratamentoDeErros> logger, FilaEventosSeguranca fila)
    {
        _logger = logger;
        _fila = fila;
    }

    public async ValueTask<bool> TryHandleAsync(HttpContext http, Exception ex, CancellationToken ct)
    {
        // A mensagem da exceção vai para a resposta (422, 404) e para o log, então passa pelo motor antes.
        var achados = MotorPii.Analisar(ex.Message);
        var mensagem = achados.Count > 0 ? MotorPii.Mascarar(ex.Message) : ex.Message;

        var (status, titulo) = ex switch
        {
            DomainException => (StatusCodes.Status422UnprocessableEntity, mensagem),
            KeyNotFoundException => (StatusCodes.Status404NotFound, mensagem),
            _ => (StatusCodes.Status500InternalServerError, "Erro inesperado. Tente de novo.")
        };

        // O texto já sai mascarado daqui. Passar a exceção inteira faria o provedor de log
        // registrar um segundo evento (LogMascarado) para a mesma falha.
        if (status == StatusCodes.Status500InternalServerError)
            _logger.LogError("Erro não tratado em {Path}: {Detalhe}", http.Request.Path, MotorPii.Mascarar(ex.ToString()));

        if (achados.Count > 0)
        {
            var rota = $"{http.Request.Method} {http.Request.Path}";
            var tipos = string.Join(", ", achados.Select(a => a.Tipo).Distinct());
            _fila.Registrar(TipoEventoSeguranca.ExcecaoMascarada, rota, achados,
                $"Uma {ex.GetType().Name} em {rota} trazia {tipos} inteiro na mensagem. " +
                $"Resposta {status} e log gravados com a mensagem mascarada: \"{mensagem}\"");
        }

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
