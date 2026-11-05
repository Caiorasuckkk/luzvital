namespace LuzVital.Domain.Entities;

/// <summary>Aviso emitido para um dia de risco. Bairro nulo = vale para a cidade toda.</summary>
public class Alerta
{
    public int Id { get; private set; }
    public int? PrevisaoRiscoId { get; private set; }
    public PrevisaoRisco? Previsao { get; private set; }
    public DateOnly Data { get; private set; }
    public NivelRisco Nivel { get; private set; }
    public string? Bairro { get; private set; }
    public string Mensagem { get; private set; } = string.Empty;
    public bool Ativo { get; private set; }
    public DateTime CriadoEm { get; private set; }

    private readonly List<CheckIn> _checkIns = new();
    public IReadOnlyCollection<CheckIn> CheckIns => _checkIns;

    private Alerta() { } // EF Core

    private Alerta(DateOnly data, NivelRisco nivel, string? bairro, string mensagem, PrevisaoRisco? previsao)
    {
        Data = data;
        Nivel = nivel;
        Bairro = string.IsNullOrWhiteSpace(bairro) ? null : Pessoa.NormalizarBairro(bairro);
        Mensagem = mensagem;
        Previsao = previsao;
        Ativo = true;
        CriadoEm = DateTime.UtcNow;
    }

    public static Alerta APartirDaPrevisao(PrevisaoRisco previsao)
    {
        if (!previsao.DeveGerarAlerta)
            throw new DomainException("Previsão de risco baixo não gera alerta.");

        var mensagem = previsao.Nivel == NivelRisco.Alto
            ? $"Risco ALTO de apagão em {previsao.Data:dd/MM}. Carregue equipamentos e combine um plano com seu voluntário."
            : $"Atenção: risco de apagão em {previsao.Data:dd/MM}. Deixe celular e equipamentos carregados.";

        return new Alerta(previsao.Data, previsao.Nivel, null, mensagem, previsao);
    }

    /// <summary>Alerta aberto à mão, por exemplo quando a luz já caiu num bairro.</summary>
    public static Alerta Manual(DateOnly data, NivelRisco nivel, string bairro, string mensagem)
    {
        if (string.IsNullOrWhiteSpace(mensagem))
            throw new DomainException("Mensagem do alerta é obrigatória.");

        return new Alerta(data, nivel, bairro, mensagem.Trim(), null);
    }

    public bool Abrange(string bairro) => Bairro is null || Bairro == Pessoa.NormalizarBairro(bairro);

    public void Encerrar() => Ativo = false;
}
