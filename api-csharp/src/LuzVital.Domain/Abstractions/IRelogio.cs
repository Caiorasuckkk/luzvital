namespace LuzVital.Domain.Abstractions;

/// <summary>Abstrai a data atual para os testes conseguirem controlar o "hoje".</summary>
public interface IRelogio
{
    DateOnly Hoje { get; }
}
