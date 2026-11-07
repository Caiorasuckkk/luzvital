using System.Reflection;
using System.Text.Json.Serialization;
using LuzVital.Api;
using LuzVital.Domain.Abstractions;
using LuzVital.Infrastructure.Data;
using LuzVital.Infrastructure.Notificacao;
using LuzVital.Infrastructure.Servicos;
using Microsoft.EntityFrameworkCore;
using Microsoft.OpenApi.Models;

var builder = WebApplication.CreateBuilder(args);

// Banco: SQLite para rodar em qualquer máquina sem instalar nada.
builder.Services.AddDbContext<LuzVitalDbContext>(opt =>
    opt.UseSqlite(builder.Configuration.GetConnectionString("LuzVital") ?? "Data Source=luzvital.db"));

builder.Services.AddScoped<IServicoAlertas, ServicoAlertas>();
builder.Services.AddScoped<IServicoPainel, ServicoPainel>();
builder.Services.AddSingleton<IRelogio, RelogioSistema>();
builder.Services.AddScoped<INotificador, SmsNotificadorSimulado>();
builder.Services.AddScoped<INotificador, WhatsAppNotificadorSimulado>();

builder.Services.AddExceptionHandler<TratamentoDeErros>();
builder.Services.AddProblemDetails();

builder.Services.AddControllers()
    .AddJsonOptions(o => o.JsonSerializerOptions.Converters.Add(new JsonStringEnumConverter()));

// O app Expo roda em outra origem durante o desenvolvimento.
builder.Services.AddCors(o => o.AddDefaultPolicy(p => p.AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod()));

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo
    {
        Title = "Luz Vital API",
        Version = "v1",
        Description = "Alerta de risco de apagão e rede de vizinhos para quem depende de energia em casa. " +
                      "Global Solution CitizenTech, FIAP 2026. Todos os dados de exemplo são fictícios."
    });

    var xml = Path.Combine(AppContext.BaseDirectory, $"{Assembly.GetExecutingAssembly().GetName().Name}.xml");
    if (File.Exists(xml))
        c.IncludeXmlComments(xml);
});

var app = builder.Build();

// Cria/atualiza o banco ao subir e coloca os dados fictícios.
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<LuzVitalDbContext>();
    if (db.Database.GetMigrations().Any())
        await db.Database.MigrateAsync();
    else
        await db.Database.EnsureCreatedAsync();

    await SeedDados.PopularAsync(db);
}

app.UseExceptionHandler();
app.UseCors();
app.UseSwagger();
app.UseSwaggerUI(c => c.DocumentTitle = "Luz Vital API");

app.MapControllers();
app.MapGet("/", () => Results.Redirect("/swagger")).ExcludeFromDescription();

app.Run();

/// <summary>Exposto para os testes de integração.</summary>
public partial class Program { }
