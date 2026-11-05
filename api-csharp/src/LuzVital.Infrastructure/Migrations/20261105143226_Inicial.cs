using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace LuzVital.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class Inicial : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "Pessoas",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    Nome = table.Column<string>(type: "TEXT", maxLength: 120, nullable: false),
                    Telefone = table.Column<string>(type: "TEXT", maxLength: 11, nullable: false),
                    Bairro = table.Column<string>(type: "TEXT", maxLength: 80, nullable: false),
                    CriadoEm = table.Column<DateTime>(type: "TEXT", nullable: false),
                    Tipo = table.Column<string>(type: "TEXT", maxLength: 13, nullable: false),
                    Cpf = table.Column<string>(type: "TEXT", maxLength: 11, nullable: true),
                    Endereco = table.Column<string>(type: "TEXT", maxLength: 200, nullable: true),
                    Dependencia = table.Column<string>(type: "TEXT", maxLength: 40, nullable: true),
                    AutonomiaHoras = table.Column<int>(type: "INTEGER", nullable: true),
                    Disponivel = table.Column<bool>(type: "INTEGER", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Pessoas", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "PrevisoesRisco",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    Data = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    Probabilidade = table.Column<double>(type: "REAL", nullable: false),
                    Nivel = table.Column<string>(type: "TEXT", maxLength: 20, nullable: false),
                    VersaoModelo = table.Column<string>(type: "TEXT", maxLength: 40, nullable: false),
                    RecebidaEm = table.Column<DateTime>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_PrevisoesRisco", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "Alertas",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    PrevisaoRiscoId = table.Column<int>(type: "INTEGER", nullable: true),
                    Data = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    Nivel = table.Column<string>(type: "TEXT", maxLength: 20, nullable: false),
                    Bairro = table.Column<string>(type: "TEXT", maxLength: 80, nullable: true),
                    Mensagem = table.Column<string>(type: "TEXT", maxLength: 300, nullable: false),
                    Ativo = table.Column<bool>(type: "INTEGER", nullable: false),
                    CriadoEm = table.Column<DateTime>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Alertas", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Alertas_PrevisoesRisco_PrevisaoRiscoId",
                        column: x => x.PrevisaoRiscoId,
                        principalTable: "PrevisoesRisco",
                        principalColumn: "Id");
                });

            migrationBuilder.CreateTable(
                name: "CheckIns",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    AlertaId = table.Column<int>(type: "INTEGER", nullable: false),
                    VoluntarioId = table.Column<int>(type: "INTEGER", nullable: false),
                    CidadaoId = table.Column<int>(type: "INTEGER", nullable: false),
                    Situacao = table.Column<string>(type: "TEXT", maxLength: 20, nullable: false),
                    Observacao = table.Column<string>(type: "TEXT", maxLength: 300, nullable: true),
                    RegistradoEm = table.Column<DateTime>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_CheckIns", x => x.Id);
                    table.ForeignKey(
                        name: "FK_CheckIns_Alertas_AlertaId",
                        column: x => x.AlertaId,
                        principalTable: "Alertas",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_CheckIns_Pessoas_CidadaoId",
                        column: x => x.CidadaoId,
                        principalTable: "Pessoas",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_CheckIns_Pessoas_VoluntarioId",
                        column: x => x.VoluntarioId,
                        principalTable: "Pessoas",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "IX_Alertas_PrevisaoRiscoId",
                table: "Alertas",
                column: "PrevisaoRiscoId");

            migrationBuilder.CreateIndex(
                name: "IX_CheckIns_AlertaId",
                table: "CheckIns",
                column: "AlertaId");

            migrationBuilder.CreateIndex(
                name: "IX_CheckIns_CidadaoId",
                table: "CheckIns",
                column: "CidadaoId");

            migrationBuilder.CreateIndex(
                name: "IX_CheckIns_VoluntarioId",
                table: "CheckIns",
                column: "VoluntarioId");

            migrationBuilder.CreateIndex(
                name: "IX_Pessoas_Bairro",
                table: "Pessoas",
                column: "Bairro");

            migrationBuilder.CreateIndex(
                name: "IX_Pessoas_Cpf",
                table: "Pessoas",
                column: "Cpf",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_PrevisoesRisco_Data",
                table: "PrevisoesRisco",
                column: "Data");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "CheckIns");

            migrationBuilder.DropTable(
                name: "Alertas");

            migrationBuilder.DropTable(
                name: "Pessoas");

            migrationBuilder.DropTable(
                name: "PrevisoesRisco");
        }
    }
}
