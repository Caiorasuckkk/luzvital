namespace LuzVital.Domain;

/// <summary>Validação e máscara de CPF. Os dados do projeto são simulados.</summary>
public static class Cpf
{
    public static string SomenteDigitos(string? valor) =>
        new((valor ?? string.Empty).Where(char.IsDigit).ToArray());

    public static bool EhValido(string? valor)
    {
        var cpf = SomenteDigitos(valor);
        if (cpf.Length != 11 || cpf.Distinct().Count() == 1)
            return false;

        return cpf[9] - '0' == Digito(cpf, 9) && cpf[10] - '0' == Digito(cpf, 10);
    }

    /// <summary>Monta um CPF válido a partir de 9 dígitos (usado só no seed de dados fictícios).</summary>
    public static string ComDigitos(string noveDigitos)
    {
        if (noveDigitos.Length != 9 || !noveDigitos.All(char.IsDigit))
            throw new ArgumentException("Informe exatamente 9 dígitos.", nameof(noveDigitos));

        var parcial = noveDigitos + Digito(noveDigitos, 9);
        return parcial + Digito(parcial, 10);
    }

    /// <summary>Mostra só os 3 primeiros e os 2 últimos dígitos: 123.***.***-09</summary>
    public static string Mascarar(string? valor)
    {
        var cpf = SomenteDigitos(valor);
        return cpf.Length == 11 ? $"{cpf[..3]}.***.***-{cpf[9..]}" : "***";
    }

    private static int Digito(string numeros, int tamanho)
    {
        var soma = 0;
        for (var i = 0; i < tamanho; i++)
            soma += (numeros[i] - '0') * (tamanho + 1 - i);

        var resto = soma % 11;
        return resto < 2 ? 0 : 11 - resto;
    }
}
