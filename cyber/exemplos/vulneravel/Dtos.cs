using System.ComponentModel.DataAnnotations;
using LuzVital.Domain;
using LuzVital.Domain.Entities;

namespace LuzVital.Api.Dtos;

// Cidadãos

public record CidadaoRequest(
    [Required, StringLength(120, MinimumLength = 3)] string Nome,
    [Required] string Cpf,
    [Required] string Telefone,
    [Required, StringLength(200)] string Endereco,
    [Required, StringLength(80)] string Bairro,
    [Required] TipoDependencia Dependencia,
    [Range(0, 72)] int AutonomiaHoras);

// EXEMPLO VULNERÁVEL DE PROPÓSITO (cópia alterada de api-csharp). Não usar na API.
// Alteração: o DTO de resposta devolve o CPF cru, sem Cpf.Mascarar.
public record CidadaoResponse(int Id, string Nome, string Cpf, string TelefoneMascarado, string Bairro,
    TipoDependencia Dependencia, int AutonomiaHoras, bool Prioritario)
{
    public static CidadaoResponse De(Cidadao c) => new(c.Id, c.Nome, c.Cpf, // VULNERÁVEL: CPF inteiro
        Mascara.Telefone(c.Telefone), c.Bairro, c.Dependencia, c.AutonomiaHoras, c.EhPrioritario);
}

// Voluntários

public record VoluntarioRequest(
    [Required, StringLength(120, MinimumLength = 3)] string Nome,
    [Required] string Telefone,
    [Required, StringLength(80)] string Bairro);

public record DisponibilidadeRequest(bool Disponivel);

public record VoluntarioResponse(int Id, string Nome, string TelefoneMascarado, string Bairro, bool Disponivel)
{
    public static VoluntarioResponse De(Voluntario v) =>
        new(v.Id, v.Nome, Mascara.Telefone(v.Telefone), v.Bairro, v.Disponivel);
}

// Previsões (vêm do ML)

public record PrevisaoRequest(
    [Required] DateOnly Data,
    [Range(0.0, 1.0)] double Probabilidade,
    [Required, StringLength(40)] string VersaoModelo);

public record PrevisaoResponse(int Id, DateOnly Data, double Probabilidade, NivelRisco Nivel, string VersaoModelo,
    int? AlertaId, int PessoasNotificadas);

// Alertas

public record AlertaManualRequest(
    [Required] DateOnly Data,
    [Required] NivelRisco Nivel,
    [Required, StringLength(80)] string Bairro,
    [Required, StringLength(300)] string Mensagem);

public record AlertaResponse(int Id, DateOnly Data, NivelRisco Nivel, string? Bairro, string Mensagem, bool Ativo)
{
    public static AlertaResponse De(Alerta a) => new(a.Id, a.Data, a.Nivel, a.Bairro, a.Mensagem, a.Ativo);
}

// Check-ins

public record CheckInRequest(
    [Range(1, int.MaxValue)] int AlertaId,
    [Range(1, int.MaxValue)] int VoluntarioId,
    [Range(1, int.MaxValue)] int CidadaoId,
    [Required] SituacaoCheckIn Situacao,
    [StringLength(300)] string? Observacao);

public record CheckInResponse(int Id, int AlertaId, int VoluntarioId, int CidadaoId, SituacaoCheckIn Situacao,
    string? Observacao, DateTime RegistradoEm)
{
    public static CheckInResponse De(CheckIn c) =>
        new(c.Id, c.AlertaId, c.VoluntarioId, c.CidadaoId, c.Situacao, c.Observacao, c.RegistradoEm);
}
