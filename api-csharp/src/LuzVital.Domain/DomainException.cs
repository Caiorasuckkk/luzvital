namespace LuzVital.Domain;

/// <summary>Regra de negócio violada. A API converte em 400 ou 422.</summary>
public class DomainException : Exception
{
    public DomainException(string mensagem) : base(mensagem) { }
}
