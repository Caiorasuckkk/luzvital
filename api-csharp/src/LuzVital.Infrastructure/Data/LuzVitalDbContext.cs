using LuzVital.Domain;
using LuzVital.Domain.Entities;
using Microsoft.EntityFrameworkCore;

namespace LuzVital.Infrastructure.Data;

public class LuzVitalDbContext : DbContext
{
    public LuzVitalDbContext(DbContextOptions<LuzVitalDbContext> options) : base(options) { }

    public DbSet<Pessoa> Pessoas => Set<Pessoa>();
    public DbSet<Cidadao> Cidadaos => Set<Cidadao>();
    public DbSet<Voluntario> Voluntarios => Set<Voluntario>();
    public DbSet<PrevisaoRisco> Previsoes => Set<PrevisaoRisco>();
    public DbSet<Alerta> Alertas => Set<Alerta>();
    public DbSet<CheckIn> CheckIns => Set<CheckIn>();

    protected override void OnModelCreating(ModelBuilder mb)
    {
        // Herança em uma tabela só (TPH), com coluna "Tipo" dizendo quem é quem.
        mb.Entity<Pessoa>(e =>
        {
            e.ToTable("Pessoas");
            e.HasDiscriminator<string>("Tipo")
                .HasValue<Cidadao>("CIDADAO")
                .HasValue<Voluntario>("VOLUNTARIO");
            e.Property(p => p.Nome).HasMaxLength(120).IsRequired();
            e.Property(p => p.Telefone).HasMaxLength(11).IsRequired();
            e.Property(p => p.Bairro).HasMaxLength(80).IsRequired();
            e.HasIndex(p => p.Bairro);
        });

        mb.Entity<Cidadao>(e =>
        {
            e.Property(c => c.Cpf).HasMaxLength(11).IsRequired();
            e.HasIndex(c => c.Cpf).IsUnique();
            e.Property(c => c.Endereco).HasMaxLength(200).IsRequired();
            e.Property(c => c.Dependencia).HasConversion<string>().HasMaxLength(40);
            e.Ignore(c => c.EhPrioritario);
        });

        mb.Entity<Voluntario>();

        mb.Entity<PrevisaoRisco>(e =>
        {
            e.ToTable("PrevisoesRisco");
            e.HasIndex(p => p.Data);
            e.Property(p => p.Nivel).HasConversion<string>().HasMaxLength(20);
            e.Property(p => p.VersaoModelo).HasMaxLength(40);
            e.Ignore(p => p.DeveGerarAlerta);
        });

        mb.Entity<Alerta>(e =>
        {
            e.ToTable("Alertas");
            e.Property(a => a.Nivel).HasConversion<string>().HasMaxLength(20);
            e.Property(a => a.Bairro).HasMaxLength(80);
            e.Property(a => a.Mensagem).HasMaxLength(300).IsRequired();
            e.HasOne(a => a.Previsao).WithMany().HasForeignKey(a => a.PrevisaoRiscoId);
            e.HasMany(a => a.CheckIns).WithOne().HasForeignKey(c => c.AlertaId);
            e.Navigation(a => a.CheckIns).UsePropertyAccessMode(PropertyAccessMode.Field);
        });

        mb.Entity<CheckIn>(e =>
        {
            e.ToTable("CheckIns");
            e.Property(c => c.Situacao).HasConversion<string>().HasMaxLength(20);
            e.Property(c => c.Observacao).HasMaxLength(300);
            e.HasOne(c => c.Voluntario).WithMany().HasForeignKey(c => c.VoluntarioId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne(c => c.Cidadao).WithMany().HasForeignKey(c => c.CidadaoId).OnDelete(DeleteBehavior.Restrict);
            e.Ignore(c => c.PedeAjuda);
        });
    }
}
