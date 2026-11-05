namespace LuzVital.Domain.Entities;

/// <summary>Pessoa que depende de energia em casa e precisa ser avisada e checada.</summary>
public class Cidadao : Pessoa
{
    /// <summary>Até quantas horas sem energia a pessoa aguenta com segurança.</summary>
    public const int LimitePrioridadeHoras = 4;

    public string Cpf { get; private set; } = string.Empty;
    public string Endereco { get; private set; } = string.Empty;
    public TipoDependencia Dependencia { get; private set; }
    public int AutonomiaHoras { get; private set; }

    private Cidadao() { } // EF Core

    public Cidadao(string nome, string cpf, string telefone, string endereco, string bairro,
        TipoDependencia dependencia, int autonomiaHoras)
        : base(nome, telefone, bairro)
    {
        if (!Domain.Cpf.EhValido(cpf))
            throw new DomainException("CPF inválido.");

        Cpf = Domain.Cpf.SomenteDigitos(cpf);
        AtualizarNecessidade(endereco, dependencia, autonomiaHoras);
    }

    public void AtualizarNecessidade(string endereco, TipoDependencia dependencia, int autonomiaHoras)
    {
        if (string.IsNullOrWhiteSpace(endereco))
            throw new DomainException("Endereço é obrigatório.");

        if (autonomiaHoras is < 0 or > 72)
            throw new DomainException("Autonomia deve ficar entre 0 e 72 horas.");

        if (!Enum.IsDefined(dependencia))
            throw new DomainException("Tipo de dependência inválido.");

        Endereco = endereco.Trim();
        Dependencia = dependencia;
        AutonomiaHoras = autonomiaHoras;
    }

    /// <summary>Quem aguenta pouco tempo sem energia é avisado e checado primeiro.</summary>
    public bool EhPrioritario => AutonomiaHoras <= LimitePrioridadeHoras;

    public override string SaudacaoAlerta() =>
        EhPrioritario
            ? $"{Nome}, PRIORIDADE: risco de falta de energia. Deixe o equipamento carregado e confira seu ponto de apoio."
            : $"{Nome}, há risco de falta de energia. Deixe celular e equipamentos carregados.";
}
