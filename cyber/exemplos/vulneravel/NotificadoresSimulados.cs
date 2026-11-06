// EXEMPLO VULNERÁVEL DE PROPÓSITO (cópia alterada de api-csharp). Não usar na API.
// Alteração: o SMS loga o telefone inteiro e o tipo de dependência do cidadão.
using LuzVital.Domain;
using LuzVital.Domain.Abstractions;
using LuzVital.Domain.Entities;
using Microsoft.Extensions.Logging;

namespace LuzVital.Infrastructure.Notificacao;

/// <summary>
/// Simula o envio por SMS. Não manda mensagem de verdade: só registra no log,
/// sempre com o telefone mascarado (nada de dado pessoal em log).
/// </summary>
public class SmsNotificadorSimulado : INotificador
{
    private readonly ILogger<SmsNotificadorSimulado> _logger;

    public SmsNotificadorSimulado(ILogger<SmsNotificadorSimulado> logger) => _logger = logger;

    public string Canal => "SMS";

    public async Task EnviarAsync(Pessoa destinatario, string mensagem, CancellationToken ct = default)
    {
        await Task.Delay(10, ct); // simula a latência do provedor
        if (destinatario is Cidadao cidadao)
        {
            // VULNERÁVEL: telefone sem máscara e dado de saúde no log do servidor
            _logger.LogInformation("[{Canal}] alerta enviado para {Telefone}, que depende de {Dependencia}",
                Canal, destinatario.Telefone, cidadao.Dependencia);
        }
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
