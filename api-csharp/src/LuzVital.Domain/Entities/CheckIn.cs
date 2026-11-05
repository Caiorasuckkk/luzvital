namespace LuzVital.Domain.Entities;

/// <summary>Registro de que um voluntário checou um cidadão durante um alerta.</summary>
public class CheckIn
{
    public int Id { get; private set; }
    public int AlertaId { get; private set; }
    public int VoluntarioId { get; private set; }
    public Voluntario? Voluntario { get; private set; }
    public int CidadaoId { get; private set; }
    public Cidadao? Cidadao { get; private set; }
    public SituacaoCheckIn Situacao { get; private set; }
    public string? Observacao { get; private set; }
    public DateTime RegistradoEm { get; private set; }

    private CheckIn() { } // EF Core

    private CheckIn(Alerta alerta, Voluntario voluntario, Cidadao cidadao, SituacaoCheckIn situacao, string? observacao)
    {
        AlertaId = alerta.Id;
        Voluntario = voluntario;
        VoluntarioId = voluntario.Id;
        Cidadao = cidadao;
        CidadaoId = cidadao.Id;
        Situacao = situacao;
        Observacao = string.IsNullOrWhiteSpace(observacao) ? null : observacao.Trim();
        RegistradoEm = DateTime.UtcNow;
    }

    public static CheckIn Registrar(Alerta alerta, Voluntario voluntario, Cidadao cidadao,
        SituacaoCheckIn situacao, string? observacao)
    {
        if (!alerta.Ativo)
            throw new DomainException("Esse alerta já foi encerrado.");

        if (!alerta.Abrange(cidadao.Bairro))
            throw new DomainException("O cidadão não está na área desse alerta.");

        if (!voluntario.PodeAtender(cidadao))
            throw new DomainException("Voluntário indisponível ou de outro bairro.");

        if (!Enum.IsDefined(situacao))
            throw new DomainException("Situação inválida.");

        if (situacao == SituacaoCheckIn.PrecisaDeAjuda && string.IsNullOrWhiteSpace(observacao))
            throw new DomainException("Descreva que ajuda a pessoa precisa.");

        return new CheckIn(alerta, voluntario, cidadao, situacao, observacao);
    }

    public bool PedeAjuda => Situacao is SituacaoCheckIn.PrecisaDeAjuda or SituacaoCheckIn.SemResposta;
}
