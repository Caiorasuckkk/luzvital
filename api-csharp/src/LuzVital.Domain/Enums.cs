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

public enum TipoEventoSeguranca
{
    PiiNaEntrada = 1,
    LogMascarado = 2,
    RespostaBloqueada = 3,
    ExcecaoMascarada = 4
}

/// <summary>Cor do farol de segurança. A ordem importa: o farol mostra o pior nível.</summary>
public enum NivelSeguranca
{
    Verde = 0,
    Amarelo = 1,
    Vermelho = 2
}
