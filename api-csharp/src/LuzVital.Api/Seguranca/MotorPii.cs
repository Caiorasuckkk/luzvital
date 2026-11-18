using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using LuzVital.Domain;

namespace LuzVital.Api.Seguranca;

public enum CategoriaPii
{
    Identificacao,
    Contato,
    Localizacao,
    Saude,
    Segredo
}

/// <summary>Um dado pessoal encontrado. <see cref="Mascarado"/> é a única forma do valor que sai do motor.</summary>
public sealed record AchadoPii(string Tipo, CategoriaPii Categoria, string Mascarado, string? Campo)
{
    /// <summary>Identificadores e segredos: se aparecerem inteiros numa resposta, a resposta é bloqueada.</summary>
    public bool EhIdentificador => Categoria is CategoriaPii.Identificacao or CategoriaPii.Contato
        or CategoriaPii.Localizacao or CategoriaPii.Segredo;
}

public sealed record ResultadoJson(IReadOnlyList<AchadoPii> Achados, string JsonMascarado);

/// <summary>
/// Motor de regras PII em tempo real: regex sobre o valor e regras pelo nome do campo.
/// Mesmas regras do motor estático em cyber/pii/regras.py, para a auditoria e o runtime concordarem.
/// </summary>
public static class MotorPii
{
    private sealed record Regra(string Tipo, CategoriaPii Categoria, Regex Padrao, Func<string, string> Mascarar,
        Func<string, bool>? Validar = null);

    private const RegexOptions Opcoes = RegexOptions.Compiled | RegexOptions.CultureInvariant;

    // O JSON mascarado só vai para o log, nunca para HTML: acentos legíveis em vez de í.
    private static readonly System.Text.Json.JsonSerializerOptions JsonParaLog = new()
        { Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping };

    // Os termos de saúde vêm do próprio enum, para não divergir quando um tipo novo for criado.
    private static readonly string TermosDependencia = string.Join("|",
        Enum.GetNames<TipoDependencia>().Where(n => n != nameof(TipoDependencia.Outro)));

    private static readonly Regra[] Regras =
    {
        new("CPF", CategoriaPii.Identificacao,
            new Regex(@"(?<![\d*])\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?![\d*])", Opcoes),
            v => Cpf.Mascarar(v), v => Cpf.EhValido(v)),
        new("RG", CategoriaPii.Identificacao,
            new Regex(@"(?<![\d*])\d{1,2}\.\d{3}\.\d{3}-[\dXx](?![\d*])", Opcoes),
            v => $"{v[..2]}.***.***-*"),
        new("Telefone", CategoriaPii.Contato,
            new Regex(@"(?<![\d*])(?:\+?55[\s-]?)?\(?[1-9][1-9]\)?[\s-]?(?:9\d{4}|[2-5]\d{3})[\s-]?\d{4}(?![\d*])", Opcoes),
            MascararTelefone),
        new("E-mail", CategoriaPii.Contato,
            new Regex(@"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", Opcoes),
            v => $"{v[..1]}***@{v[(v.IndexOf('@') + 1)..]}"),
        new("Endereço", CategoriaPii.Localizacao,
            new Regex(@"\b(?:Rua|R\.|Avenida|Av\.|Alameda|Al\.|Travessa|Tv\.|Estrada|Rodovia|Praça)\s+[A-Za-zÀ-ÿ0-9'. ]{2,60}?,?\s*(?:n[º°o]\.?\s*)?\d{1,5}\b", Opcoes),
            v => $"{v.Split(' ')[0]} ***, nº ***"),
        new("Saúde", CategoriaPii.Saude,
            new Regex(@"(?i)\b(?:" + TermosDependencia + @"|concentrador de oxig[eê]nio|oxig[eê]nio|insulin[a]|acamad[oa]s?|di[aá]lise|laudo|diagn[oó]stico)\b", Opcoes),
            v => $"{v[..3]}***"),
        new("CID-10", CategoriaPii.Saude,
            new Regex(@"\b[A-TV-Z]\d{2}\.\d\b", Opcoes),
            v => $"{v[0]}**.*"),
        new("Senha", CategoriaPii.Segredo,
            new Regex(@"(?i)\b(?:password|pwd|senha|token)\s*[=:]\s*[""']?(?!\*)[^;""'\s,}]+", Opcoes),
            v => $"{Regex.Match(v, @"^\s*[A-Za-z]+").Value.Trim()}=***"),
    };

    // Campos que são dado pessoal pelo nome, mesmo quando o valor não casa com nenhum regex.
    private static readonly Dictionary<string, (string Tipo, CategoriaPii Categoria)> CamposSensiveis =
        new(StringComparer.OrdinalIgnoreCase)
        {
            ["cpf"] = ("CPF", CategoriaPii.Identificacao),
            ["rg"] = ("RG", CategoriaPii.Identificacao),
            ["telefone"] = ("Telefone", CategoriaPii.Contato),
            ["celular"] = ("Telefone", CategoriaPii.Contato),
            ["email"] = ("E-mail", CategoriaPii.Contato),
            ["endereco"] = ("Endereço", CategoriaPii.Localizacao),
            ["logradouro"] = ("Endereço", CategoriaPii.Localizacao),
            ["senha"] = ("Senha", CategoriaPii.Segredo),
            ["password"] = ("Senha", CategoriaPii.Segredo),
            ["token"] = ("Senha", CategoriaPii.Segredo),
            ["laudo"] = ("Saúde", CategoriaPii.Saude),
            ["diagnostico"] = ("Saúde", CategoriaPii.Saude),
            ["cid"] = ("CID-10", CategoriaPii.Saude),
            ["dependencia"] = ("Saúde", CategoriaPii.Saude),
        };

    private static string MascararTelefone(string valor)
    {
        var digitos = Cpf.SomenteDigitos(valor);
        return Mascara.Telefone(digitos.Length > 11 && digitos.StartsWith("55") ? digitos[2..] : digitos);
    }

    /// <summary>Valor que já saiu mascarado (529.***.***-25, (11) *****-0001) não conta como dado inteiro.</summary>
    public static bool EstaMascarado(string valor) => valor.Contains('*');

    /// <summary>Procura dado pessoal num texto livre (mensagem de log, mensagem de exceção).</summary>
    public static IReadOnlyList<AchadoPii> Analisar(string? texto, string? campo = null) =>
        Varrer(texto, campo).Select(a => a.Achado).ToList();

    /// <summary>Devolve o texto com cada dado pessoal inteiro trocado pela versão mascarada.</summary>
    public static string Mascarar(string? texto)
    {
        if (string.IsNullOrEmpty(texto))
            return texto ?? string.Empty;

        // Do fim para o começo, para as posições continuarem valendo depois de cada troca.
        var resultado = texto;
        foreach (var (achado, inicio, tamanho) in Varrer(texto, null).OrderByDescending(a => a.Inicio))
            resultado = resultado[..inicio] + achado.Mascarado + resultado[(inicio + tamanho)..];
        return resultado;
    }

    /// <summary>Analisa um JSON campo a campo: regras pelo nome do campo e pelo valor. Devolve o JSON mascarado.</summary>
    public static ResultadoJson AnalisarJson(string json)
    {
        JsonNode? raiz;
        try
        {
            raiz = JsonNode.Parse(json);
        }
        catch (System.Text.Json.JsonException)
        {
            var achados = Analisar(json);
            return new ResultadoJson(achados, Mascarar(json));
        }

        var lista = new List<AchadoPii>();
        raiz = Percorrer(raiz, null, lista);
        return new ResultadoJson(lista, raiz?.ToJsonString(JsonParaLog) ?? "null");
    }

    private static JsonNode? Percorrer(JsonNode? no, string? campo, List<AchadoPii> achados)
    {
        switch (no)
        {
            case JsonObject obj:
                foreach (var (nome, filho) in obj.ToList())
                    obj[nome] = Percorrer(filho, nome, achados);
                return obj;

            case JsonArray arr:
                for (var i = 0; i < arr.Count; i++)
                    arr[i] = Percorrer(arr[i]?.DeepClone(), campo, achados);
                return arr;

            case JsonValue val:
                var texto = val.ToString();
                if (string.IsNullOrWhiteSpace(texto) || EstaMascarado(texto))
                    return val.DeepClone();

                var porValor = Analisar(texto, campo);
                if (porValor.Count > 0)
                {
                    achados.AddRange(porValor);
                    return JsonValue.Create(Mascarar(texto));
                }

                if (campo is not null && CamposSensiveis.TryGetValue(campo, out var regra))
                {
                    achados.Add(new AchadoPii(regra.Tipo, regra.Categoria, "***", campo));
                    return JsonValue.Create("***");
                }

                return val.DeepClone();

            default:
                return no;
        }
    }

    private static IEnumerable<(AchadoPii Achado, int Inicio, int Tamanho)> Varrer(string? texto, string? campo)
    {
        if (string.IsNullOrEmpty(texto))
            yield break;

        var ocupado = new bool[texto.Length];
        foreach (var regra in Regras)
        {
            foreach (Match m in regra.Padrao.Matches(texto))
            {
                if (Enumerable.Range(m.Index, m.Length).Any(i => ocupado[i]))
                    continue;
                if (regra.Validar is not null && !regra.Validar(m.Value))
                    continue;

                for (var i = m.Index; i < m.Index + m.Length; i++)
                    ocupado[i] = true;

                yield return (new AchadoPii(regra.Tipo, regra.Categoria, regra.Mascarar(m.Value), campo), m.Index, m.Length);
            }
        }
    }
}
