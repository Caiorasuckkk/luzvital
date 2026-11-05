namespace LuzVital.Domain;

/// <summary>Equipamento ou necessidade que faz a pessoa depender de energia em casa.</summary>
public enum TipoDependencia
{
    OxigenioDomiciliar = 1,
    MedicamentoRefrigerado = 2,
    CadeiraMotorizada = 3,
    AcamadoComEquipamento = 4,
    Outro = 99
}

public enum NivelRisco
{
    Baixo = 0,
    Atencao = 1,
    Alto = 2
}

public enum SituacaoCheckIn
{
    Ok = 1,
    PrecisaDeAjuda = 2,
    SemResposta = 3
}
