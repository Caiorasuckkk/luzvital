using System.Net.Http.Json;
using System.Text.Json;
using LuzVital.Domain;

namespace LuzVital.Api.Seguranca;

public sealed record Traducao(string Mensagem, string Modo);

/// <summary>Transforma a descrição técnica de um evento em um aviso que um cidadão leigo entende.</summary>
public interface ITradutorRisco
{
    Task<Traducao> TraduzirAsync(TipoEventoSeguranca tipo, string descricaoTecnica, CancellationToken ct);
}

/// <summary>
/// Chama a API de Messages da Anthropic. Só a descrição técnica mascarada vai para o modelo.
/// Sem ANTHROPIC_API_KEY, com erro, recusa ou resposta cortada, usa o texto offline do tipo de evento.
/// </summary>
public sealed class TradutorRiscoAnthropic : ITradutorRisco
{
    public const string ModeloPadrao = "claude-haiku-5-5";
    private const string Url = "https://api.anthropic.com/v1/messages";
    private const string VersaoApi = "2026-10-21";

    private const string Sistema =
        "Você escreve avisos de segurança para cidadãos brasileiros que usam o app Luz Vital. " +
        "Responda em português simples, sem termos técnicos, sem siglas em inglês e sem inventar dados. " +
        "Diga o que aconteceu e se a pessoa precisa fazer alguma coisa. Responda só com as 2 frases.";

    private readonly HttpClient _http;
    private readonly string _modelo;
    private readonly ILogger<TradutorRiscoAnthropic> _logger;

    public TradutorRiscoAnthropic(HttpClient http, IConfiguration config, ILogger<TradutorRiscoAnthropic> logger)
    {
        _http = http;
        _modelo = config["Seguranca:ModeloIa"] is { Length: > 0 } m ? m : ModeloPadrao;
        _logger = logger;
    }

    public async Task<Traducao> TraduzirAsync(TipoEventoSeguranca tipo, string descricaoTecnica, CancellationToken ct)
    {
        var chave = Environment.GetEnvironmentVariable("ANTHROPIC_API_KEY");
        if (string.IsNullOrWhiteSpace(chave))
            return Offline(tipo);

        // Segunda barreira: se algum identificador inteiro escapou da descrição, nada sai para fora.
        if (MotorPii.Analisar(descricaoTecnica).Any(a => a.EhIdentificador))
        {
            _logger.LogWarning("Tradução cancelada: a descrição do evento {Tipo} tinha dado pessoal inteiro", tipo);
            return Offline(tipo);
        }

        var pedido = new
        {
            model = _modelo,
            max_tokens = 300,
            system = Sistema,
            messages = new[]
            {
                new
                {
                    role = "user",
                    content = $"Traduza a falha técnica '{descricaoTecnica}' para um cidadão leigo de 60 anos, em 2 frases."
                }
            }
        };

        try
        {
            using var req = new HttpRequestMessage(HttpMethod.Post, Url) { Content = JsonContent.Create(pedido) };
            req.Headers.Add("x-api-key", chave);
            req.Headers.Add("anthropic-version", VersaoApi);

            using var resp = await _http.SendAsync(req, ct);
            if (!resp.IsSuccessStatusCode)
            {
                _logger.LogWarning("IA indisponível para o evento {Tipo}: HTTP {Status}", tipo, (int)resp.StatusCode);
                return Offline(tipo);
            }

            using var doc = JsonDocument.Parse(await resp.Content.ReadAsStringAsync(ct));
            var motivoParada = doc.RootElement.TryGetProperty("stop_reason", out var sr) ? sr.GetString() : null;
            if (motivoParada is "refusal" or "max_tokens")
            {
                _logger.LogWarning("IA não concluiu o texto do evento {Tipo} (stop_reason {Motivo})", tipo, motivoParada);
                return Offline(tipo);
            }

            var texto = string.Join(" ", doc.RootElement.GetProperty("content").EnumerateArray()
                .Where(b => b.GetProperty("type").GetString() == "text")
                .Select(b => b.GetProperty("text").GetString())).Trim();

            return texto.Length > 0 ? new Traducao(MotorPii.Mascarar(texto), "online") : Offline(tipo);
        }
        catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException or JsonException
                                       or KeyNotFoundException or InvalidOperationException)
        {
            if (ct.IsCancellationRequested)
                throw;
            _logger.LogWarning("IA indisponível para o evento {Tipo}: {Erro}", tipo, ex.GetType().Name);
            return Offline(tipo);
        }
    }

    private static Traducao Offline(TipoEventoSeguranca tipo) => new(TextosOffline.Para(tipo), "offline");
}

/// <summary>Avisos fixos, usados quando a IA não está disponível.</summary>
public static class TextosOffline
{
    public static string Para(TipoEventoSeguranca tipo) => tipo switch
    {
        TipoEventoSeguranca.PiiNaEntrada =>
            "Seus dados chegaram ao sistema e foram protegidos antes de qualquer registro. Você não precisa fazer nada.",
        TipoEventoSeguranca.LogMascarado =>
            "O sistema tentou anotar um dado seu por inteiro no registro interno, mas escondeu a maior parte antes de gravar. " +
            "Seus dados continuam protegidos e a equipe foi avisada para corrigir.",
        TipoEventoSeguranca.RespostaBloqueada =>
            "O sistema ia mostrar um dado pessoal seu por inteiro e foi barrado antes que isso acontecesse. " +
            "Nada foi exposto, e a equipe técnica foi avisada.",
        TipoEventoSeguranca.ExcecaoMascarada =>
            "Aconteceu um erro no sistema e a mensagem de erro tinha um dado seu, que foi escondido antes de ser gravado. " +
            "Ninguém viu seu dado, e a equipe técnica vai corrigir o erro.",
        _ => "O sistema protegeu um dado pessoal. Você não precisa fazer nada."
    };
}
