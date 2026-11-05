namespace LuzVital.Domain.Entities;

/// <summary>Base comum de quem é cadastrado no sistema (cidadão ou voluntário).</summary>
public abstract class Pessoa
{
    public int Id { get; private set; }
    public string Nome { get; private set; } = string.Empty;
    public string Telefone { get; private set; } = string.Empty;
    public string Bairro { get; private set; } = string.Empty;
    public DateTime CriadoEm { get; private set; }

    protected Pessoa() { } // EF Core

    protected Pessoa(string nome, string telefone, string bairro)
    {
        AtualizarContato(nome, telefone, bairro);
        CriadoEm = DateTime.UtcNow;
    }

    public void AtualizarContato(string nome, string telefone, string bairro)
    {
        if (string.IsNullOrWhiteSpace(nome) || nome.Trim().Length < 3)
            throw new DomainException("Nome precisa ter pelo menos 3 letras.");

        var digitos = new string((telefone ?? string.Empty).Where(char.IsDigit).ToArray());
        if (digitos.Length is < 10 or > 11)
            throw new DomainException("Telefone precisa ter DDD + número (10 ou 11 dígitos).");

        if (string.IsNullOrWhiteSpace(bairro))
            throw new DomainException("Bairro é obrigatório.");

        Nome = nome.Trim();
        Telefone = digitos;
        Bairro = NormalizarBairro(bairro);
    }

    /// <summary>Cada tipo de pessoa diz como prefere ser chamada no alerta.</summary>
    public abstract string SaudacaoAlerta();

    public static string NormalizarBairro(string bairro) => bairro.Trim().ToUpperInvariant();
}
