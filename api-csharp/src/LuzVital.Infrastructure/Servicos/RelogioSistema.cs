using LuzVital.Domain.Abstractions;

namespace LuzVital.Infrastructure.Servicos;

public class RelogioSistema : IRelogio
{
    private static readonly TimeZoneInfo SaoPaulo = TimeZoneInfo.FindSystemTimeZoneById("America/Sao_Paulo");

    public DateOnly Hoje => DateOnly.FromDateTime(TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, SaoPaulo));
}
