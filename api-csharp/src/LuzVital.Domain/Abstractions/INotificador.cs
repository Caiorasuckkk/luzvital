using LuzVital.Domain.Entities;

namespace LuzVital.Domain.Abstractions;

/// <summary>Canal de envio de alerta. Cada canal (SMS, WhatsApp) é uma implementação.</summary>
public interface INotificador
{
    string Canal { get; }

    Task EnviarAsync(Pessoa destinatario, string mensagem, CancellationToken ct = default);
}
