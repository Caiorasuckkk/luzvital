using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace LuzVital.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class Seguranca : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "EventosSeguranca",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    OcorridoEm = table.Column<DateTime>(type: "TEXT", nullable: false),
                    Tipo = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    Nivel = table.Column<string>(type: "TEXT", maxLength: 10, nullable: false),
                    Rota = table.Column<string>(type: "TEXT", maxLength: 200, nullable: false),
                    TiposDeDado = table.Column<string>(type: "TEXT", maxLength: 200, nullable: false),
                    DescricaoTecnica = table.Column<string>(type: "TEXT", maxLength: 500, nullable: false),
                    MensagemCidadao = table.Column<string>(type: "TEXT", maxLength: 600, nullable: false),
                    ModoIa = table.Column<string>(type: "TEXT", maxLength: 20, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_EventosSeguranca", x => x.Id);
                });

            migrationBuilder.CreateIndex(
                name: "IX_EventosSeguranca_OcorridoEm",
                table: "EventosSeguranca",
                column: "OcorridoEm");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "EventosSeguranca");
        }
    }
}
