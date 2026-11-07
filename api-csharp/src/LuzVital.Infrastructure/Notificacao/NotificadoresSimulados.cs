using LuzVital.Domain;
using LuzVital.Domain.Abstractions;
using LuzVital.Domain.Entities;
using Microsoft.Extensions.Logging;

namespace LuzVital.Infrastructure.Notificacao;

/// <summary>Simula o envio por SMS: só registra no log, com o telefone mascarado.</summary>
public class SmsNotificadorSimulado : INotificador
{
    private readonly ILogger<SmsNotificadorSimulado> _logger;

    public SmsNotificadorSimulado(ILogger<SmsNotificadorSimulado> logger) => _logger = logger;

    public string Canal => "SMS";

    public async Task EnviarAsync(Pessoa destinatario, string mensagem, CancellationToken ct = default)
    {
        await Task.Delay(10, ct); // simula a latência do provedor
        _logger.LogInformation("[{Canal}] alerta enviado para {Telefone} (pessoa {Id})",
            Canal, Mascara.Telefone(destinatario.Telefone), destinatario.Id);
    }
}

/// <summary>Mesma ideia do SMS, simulando WhatsApp.</summary>
public class WhatsAppNotificadorSimulado : INotificador
{
    private readonly ILogger<WhatsAppNotificadorSimulado> _logger;

    public WhatsAppNotificadorSimulado(ILogger<WhatsAppNotificadorSimulado> logger) => _logger = logger;

    public string Canal => "WhatsApp";

    public async Task EnviarAsync(Pessoa destinatario, string mensagem, CancellationToken ct = default)
    {
        await Task.Delay(10, ct);
        _logger.LogInformation("[{Canal}] alerta enviado para {Telefone} (pessoa {Id})",
            Canal, Mascara.Telefone(destinatario.Telefone), destinatario.Id);
    }
}
