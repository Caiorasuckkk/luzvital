using Microsoft.Extensions.DependencyInjection.Extensions;

namespace LuzVital.Api.Seguranca;

public static class ConfiguracaoSeguranca
{
    /// <summary>Fila de eventos, tradutor (IA), processador em segundo plano e exceções de exposição.</summary>
    public static IServiceCollection AddCamadaSeguranca(this IServiceCollection services, IConfiguration config)
    {
        services.TryAddSingleton<FilaEventosSeguranca>();
        services.Configure<OpcoesSeguranca>(config.GetSection("Seguranca"));
        services.AddHttpClient<ITradutorRisco, TradutorRiscoAnthropic>(c => c.Timeout = TimeSpan.FromSeconds(20));
        services.AddHostedService<ProcessadorEventosSeguranca>();
        return services;
    }

    /// <summary>Ordem: o guarda fica por fora de tudo, para conferir até a resposta do tratamento de erros.</summary>
    public static IApplicationBuilder UseGuardaRespostas(this IApplicationBuilder app) =>
        app.UseMiddleware<GuardaRespostas>();

    public static IApplicationBuilder UsePiiNaEntrada(this IApplicationBuilder app) =>
        app.UseMiddleware<MiddlewarePiiEntrada>();
}
