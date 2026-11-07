using LuzVital.Domain;
using LuzVital.Domain.Entities;
using Microsoft.EntityFrameworkCore;

namespace LuzVital.Infrastructure.Data;

/// <summary>Dados fictícios para demonstração: nomes inventados, CPFs gerados só para passar na validação e telefones 119000000xx.</summary>
public static class SeedDados
{
    public static async Task PopularAsync(LuzVitalDbContext db, CancellationToken ct = default)
    {
        if (await db.Pessoas.AnyAsync(ct))
            return;

        var cidadaos = new[]
        {
            new Cidadao("Maria Aparecida (fictícia)", Cpf.ComDigitos("100000001"), "11900000001",
                "Rua Exemplo, 100", "Bela Vista", TipoDependencia.OxigenioDomiciliar, 2),
            new Cidadao("José Carlos (fictício)", Cpf.ComDigitos("100000002"), "11900000002",
                "Rua Exemplo, 200", "Bela Vista", TipoDependencia.MedicamentoRefrigerado, 8),
            new Cidadao("Ana Lúcia (fictícia)", Cpf.ComDigitos("100000003"), "11900000003",
                "Rua Modelo, 50", "Mooca", TipoDependencia.AcamadoComEquipamento, 3),
            new Cidadao("Pedro Henrique (fictício)", Cpf.ComDigitos("100000004"), "11900000004",
                "Rua Modelo, 75", "Mooca", TipoDependencia.CadeiraMotorizada, 12),
        };

        var voluntarios = new[]
        {
            new Voluntario("Carla Souza (fictícia)", "11900000011", "Bela Vista"),
            new Voluntario("Rafael Lima (fictício)", "11900000012", "Mooca"),
        };

        db.Cidadaos.AddRange(cidadaos);
        db.Voluntarios.AddRange(voluntarios);
        await db.SaveChangesAsync(ct);
    }
}
