namespace LuzVital.Domain;

/// <summary>Máscaras para não expor dado pessoal em resposta de API nem em log.</summary>
public static class Mascara
{
    /// <summary>(11) *****-4321</summary>
    public static string Telefone(string? telefone)
    {
        var digitos = new string((telefone ?? string.Empty).Where(char.IsDigit).ToArray());
        if (digitos.Length < 10)
            return "***";

        return $"({digitos[..2]}) *****-{digitos[^4..]}";
    }
}
