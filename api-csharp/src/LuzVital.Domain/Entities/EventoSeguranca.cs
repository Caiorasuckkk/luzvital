namespace LuzVital.Domain.Entities;

/// <summary>
/// Registro de um dado pessoal pego em tempo real pela camada de segurança da API.
/// A descrição técnica só guarda valores mascarados; o dado inteiro nunca é gravado.
/// </summary>
public class EventoSeguranca
{
    public int Id { get; private set; }
    public DateTime OcorridoEm { get; private set; }
    public TipoEventoSeguranca Tipo { get; private set; }
    public NivelSeguranca Nivel { get; private set; }
    public string Rota { get; private set; } = string.Empty;
    public string TiposDeDado { get; private set; } = string.Empty;
    public string DescricaoTecnica { get; private set; } = string.Empty;
    public string MensagemCidadao { get; private set; } = string.Empty;
    public string ModoIa { get; private set; } = string.Empty;

    private EventoSeguranca() { } // EF Core

    public EventoSeguranca(DateTime ocorridoEm, TipoEventoSeguranca tipo, string rota, IEnumerable<string> tiposDeDado,
        string descricaoTecnica, string mensagemCidadao, string modoIa)
    {
        OcorridoEm = ocorridoEm;
        Tipo = tipo;
        Nivel = NivelDe(tipo);
        Rota = Cortar(rota, 200);
        TiposDeDado = Cortar(string.Join(",", tiposDeDado.Distinct().OrderBy(t => t)), 200);
        DescricaoTecnica = Cortar(descricaoTecnica, 500);
        MensagemCidadao = Cortar(mensagemCidadao, 600);
        ModoIa = Cortar(modoIa, 20);
    }

    private static string Cortar(string texto, int limite) =>
        texto.Length <= limite ? texto : texto[..(limite - 3)] + "...";

    /// <summary>Entrada mascarada é o sistema funcionando (verde); log mascarado é um descuido pego a tempo (amarelo);
    /// resposta bloqueada ou exceção com dado pessoal quase saiu para fora (vermelho).</summary>
    public static NivelSeguranca NivelDe(TipoEventoSeguranca tipo) => tipo switch
    {
        TipoEventoSeguranca.PiiNaEntrada => NivelSeguranca.Verde,
        TipoEventoSeguranca.LogMascarado => NivelSeguranca.Amarelo,
        _ => NivelSeguranca.Vermelho
    };
}
