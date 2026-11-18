using LuzVital.Domain;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace LuzVital.Api.Seguranca;

/// <summary>
/// Embrulha os provedores de log que já existiam (console, debug...). Antes de qualquer escrita, passa a
/// mensagem e a exceção pelo motor PII; se houver dado inteiro, escreve a versão mascarada e registra o evento.
/// </summary>
public sealed class ProvedorLogSeguro : ILoggerProvider, ISupportExternalScope
{
    public const string ChaveInternos = "LuzVital.LogInterno";

    private readonly ILoggerProvider[] _internos;
    private readonly FilaEventosSeguranca _fila;
    private readonly IHttpContextAccessor? _http;

    public ProvedorLogSeguro(IEnumerable<ILoggerProvider> internos, FilaEventosSeguranca fila, IHttpContextAccessor? http)
    {
        _internos = internos.ToArray();
        _fila = fila;
        _http = http;
    }

    public ILogger CreateLogger(string categoria) =>
        new LoggerSeguro(categoria, _internos.Select(p => p.CreateLogger(categoria)).ToArray(), _fila, _http);

    public void SetScopeProvider(IExternalScopeProvider scopeProvider)
    {
        foreach (var p in _internos.OfType<ISupportExternalScope>())
            p.SetScopeProvider(scopeProvider);
    }

    public void Dispose()
    {
        foreach (var p in _internos)
            p.Dispose();
    }

    private sealed class LoggerSeguro : ILogger
    {
        private readonly string _categoria;
        private readonly ILogger[] _internos;
        private readonly FilaEventosSeguranca _fila;
        private readonly IHttpContextAccessor? _http;

        public LoggerSeguro(string categoria, ILogger[] internos, FilaEventosSeguranca fila, IHttpContextAccessor? http)
        {
            _categoria = categoria;
            _internos = internos;
            _fila = fila;
            _http = http;
        }

        public IDisposable? BeginScope<TState>(TState state) where TState : notnull =>
            new Escopos(_internos.Select(l => l.BeginScope(state)).ToArray());

        public bool IsEnabled(LogLevel nivel) => _internos.Any(l => l.IsEnabled(nivel));

        public void Log<TState>(LogLevel nivel, EventId id, TState state, Exception? ex,
            Func<TState, Exception?, string> formatar)
        {
            if (!IsEnabled(nivel))
                return;

            var mensagem = formatar(state, ex);
            var textoExcecao = ex?.ToString();
            var achados = MotorPii.Analisar(mensagem).Concat(MotorPii.Analisar(textoExcecao)).ToList();

            if (achados.Count == 0)
            {
                foreach (var l in _internos)
                    l.Log(nivel, id, state, ex, formatar);
                return;
            }

            var mascarada = MotorPii.Mascarar(mensagem);
            var excecaoMascarada = ex is null ? null : new ExcecaoComDadoMascarado(MotorPii.Mascarar(textoExcecao));
            foreach (var l in _internos)
                l.Log(nivel, id, mascarada, excecaoMascarada, (s, _) => s);

            var req = _http?.HttpContext?.Request;
            var rota = req is null ? "(fora de requisição)" : $"{req.Method} {req.Path}";
            var tipos = string.Join(", ", achados.Select(a => a.Tipo).Distinct());
            var trecho = mascarada.Length > 160 ? mascarada[..160] + "..." : mascarada;
            _fila.Registrar(TipoEventoSeguranca.LogMascarado, rota, achados,
                $"Um log {nivel} de {_categoria} trazia {tipos} inteiro. Foi gravado mascarado: \"{trecho}\"");
        }
    }

    private sealed class Escopos : IDisposable
    {
        private readonly IDisposable?[] _escopos;
        public Escopos(IDisposable?[] escopos) => _escopos = escopos;

        public void Dispose()
        {
            foreach (var e in _escopos)
                e?.Dispose();
        }
    }

    /// <summary>Os provedores escrevem ex.ToString(); esta exceção devolve o texto já mascarado.</summary>
    private sealed class ExcecaoComDadoMascarado : Exception
    {
        private readonly string _texto;
        public ExcecaoComDadoMascarado(string texto) : base(texto) => _texto = texto;
        public override string ToString() => _texto;
    }
}

public static class LogSeguroExtensions
{
    /// <summary>
    /// Troca os provedores de log registrados até aqui pelo <see cref="ProvedorLogSeguro"/>, que os chama por dentro.
    /// Chame depois de qualquer outro AddXxx de logging.
    /// </summary>
    public static ILoggingBuilder EmbrulharComLogSeguro(this ILoggingBuilder logging)
    {
        var servicos = logging.Services;
        var originais = servicos.Where(d => d.ServiceType == typeof(ILoggerProvider) && !d.IsKeyedService).ToList();

        foreach (var d in originais)
        {
            servicos.Remove(d);
            servicos.Add(d switch
            {
                { ImplementationInstance: not null } =>
                    new ServiceDescriptor(typeof(ILoggerProvider), ProvedorLogSeguro.ChaveInternos, d.ImplementationInstance),
                { ImplementationFactory: not null } =>
                    new ServiceDescriptor(typeof(ILoggerProvider), ProvedorLogSeguro.ChaveInternos,
                        (sp, _) => d.ImplementationFactory(sp), d.Lifetime),
                _ => new ServiceDescriptor(typeof(ILoggerProvider), ProvedorLogSeguro.ChaveInternos,
                    d.ImplementationType!, d.Lifetime)
            });
        }

        servicos.AddHttpContextAccessor();
        servicos.TryAddSingleton<FilaEventosSeguranca>();
        servicos.AddSingleton<ILoggerProvider>(sp => new ProvedorLogSeguro(
            sp.GetKeyedServices<ILoggerProvider>(ProvedorLogSeguro.ChaveInternos),
            sp.GetRequiredService<FilaEventosSeguranca>(),
            sp.GetService<IHttpContextAccessor>()));
        return logging;
    }
}
