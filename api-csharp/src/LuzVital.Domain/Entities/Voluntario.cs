namespace LuzVital.Domain.Entities;

/// <summary>Vizinho que se oferece para checar os cidadãos do mesmo bairro durante um apagão.</summary>
public class Voluntario : Pessoa
{
    public bool Disponivel { get; private set; } = true;

    private Voluntario() { } // EF Core

    public Voluntario(string nome, string telefone, string bairro) : base(nome, telefone, bairro) { }

    public void DefinirDisponibilidade(bool disponivel) => Disponivel = disponivel;

    /// <summary>Voluntário só checa quem mora no mesmo bairro e só quando está disponível.</summary>
    public bool PodeAtender(Cidadao cidadao) => Disponivel && cidadao.Bairro == Bairro;

    public override string SaudacaoAlerta() =>
        $"{Nome}, há risco de apagão no seu bairro. Fique de olho no app para os check-ins.";
}
