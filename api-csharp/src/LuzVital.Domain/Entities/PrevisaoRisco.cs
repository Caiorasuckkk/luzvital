namespace LuzVital.Domain.Entities;

/// <summary>Resultado do modelo de ML para um dia: chance de apagão em massa na área da Enel SP.</summary>
public class PrevisaoRisco
{
    public const double LimiteAtencao = 0.4;
    public const double LimiteAlto = 0.7;

    public int Id { get; private set; }
    public DateOnly Data { get; private set; }
    public double Probabilidade { get; private set; }
    public NivelRisco Nivel { get; private set; }
    public string VersaoModelo { get; private set; } = string.Empty;
    public DateTime RecebidaEm { get; private set; }

    private PrevisaoRisco() { } // EF Core

    public PrevisaoRisco(DateOnly data, double probabilidade, string versaoModelo, DateOnly hoje)
    {
        if (data < hoje)
            throw new DomainException("Não dá para registrar previsão para uma data que já passou.");

        if (probabilidade is < 0 or > 1 || double.IsNaN(probabilidade))
            throw new DomainException("Probabilidade deve estar entre 0 e 1.");

        if (string.IsNullOrWhiteSpace(versaoModelo))
            throw new DomainException("Informe a versão do modelo que gerou a previsão.");

        Data = data;
        Probabilidade = probabilidade;
        Nivel = Classificar(probabilidade);
        VersaoModelo = versaoModelo.Trim();
        RecebidaEm = DateTime.UtcNow;
    }

    public static NivelRisco Classificar(double probabilidade) => probabilidade switch
    {
        >= LimiteAlto => NivelRisco.Alto,
        >= LimiteAtencao => NivelRisco.Atencao,
        _ => NivelRisco.Baixo
    };

    public bool DeveGerarAlerta => Nivel >= NivelRisco.Atencao;
}
