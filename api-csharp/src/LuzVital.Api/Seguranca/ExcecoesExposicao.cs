namespace LuzVital.Api.Seguranca;

/// <summary>Campo sensível que pode sair em certas rotas, com o motivo registrado.</summary>
public sealed class ExcecaoExposicao
{
    public string Campo { get; set; } = string.Empty;
    public List<string> Rotas { get; set; } = new();
    public string Motivo { get; set; } = string.Empty;
}

/// <summary>
/// Seção "Seguranca:ExcecoesExposicao" do appsettings.json. Espelha cyber/taint/excecoes.json,
/// para a auditoria estática e o guarda em tempo real aceitarem as mesmas exposições.
/// </summary>
public sealed class OpcoesSeguranca
{
    public List<ExcecaoExposicao> ExcecoesExposicao { get; set; } = new();

    public bool Permitido(PathString rota, string? campo) =>
        campo is not null && ExcecoesExposicao.Any(e =>
            string.Equals(e.Campo, campo, StringComparison.OrdinalIgnoreCase) &&
            e.Rotas.Any(r => rota.StartsWithSegments(r, StringComparison.OrdinalIgnoreCase)));
}
