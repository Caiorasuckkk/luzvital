using System.Threading.Channels;
using LuzVital.Domain;
using LuzVital.Domain.Entities;
using LuzVital.Infrastructure.Data;

namespace LuzVital.Api.Seguranca;

/// <summary>Evento ainda sem a mensagem para o cidadão. A descrição técnica já chega mascarada.</summary>
public sealed record EventoPendente(DateTime OcorridoEm, TipoEventoSeguranca Tipo, string Rota,
    IReadOnlyList<string> TiposDeDado, string DescricaoTecnica);

/// <summary>
/// Ponto único por onde middlewares, log e tratamento de erros registram eventos de segurança.
/// Só enfileira: a tradução pela IA e a gravação no banco rodam em segundo plano, fora da requisição.
/// </summary>
public sealed class FilaEventosSeguranca
{
    // Limitada e descartando os mais antigos: um ataque que gere milhares de eventos não derruba a API.
    private readonly Channel<EventoPendente> _canal = Channel.CreateBounded<EventoPendente>(
        new BoundedChannelOptions(1000) { FullMode = BoundedChannelFullMode.DropOldest, SingleReader = true });

    public ChannelReader<EventoPendente> Leitor => _canal.Reader;

    public void Registrar(TipoEventoSeguranca tipo, string rota, IEnumerable<AchadoPii> achados, string descricaoTecnica)
    {
        var tipos = achados.Select(a => a.Tipo).Distinct().ToList();
        _canal.Writer.TryWrite(new EventoPendente(DateTime.UtcNow, tipo, rota, tipos, descricaoTecnica));
    }
}

/// <summary>Lê a fila, pede a tradução para o cidadão e grava o evento.</summary>
public sealed class ProcessadorEventosSeguranca : BackgroundService
{
    private readonly FilaEventosSeguranca _fila;
    private readonly IServiceScopeFactory _escopos;
    private readonly ILogger<ProcessadorEventosSeguranca> _logger;

    public ProcessadorEventosSeguranca(FilaEventosSeguranca fila, IServiceScopeFactory escopos,
        ILogger<ProcessadorEventosSeguranca> logger)
    {
        _fila = fila;
        _escopos = escopos;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        await foreach (var pendente in _fila.Leitor.ReadAllAsync(ct))
        {
            try
            {
                using var escopo = _escopos.CreateScope();
                var tradutor = escopo.ServiceProvider.GetRequiredService<ITradutorRisco>();
                var traducao = await tradutor.TraduzirAsync(pendente.Tipo, pendente.DescricaoTecnica, ct);

                var db = escopo.ServiceProvider.GetRequiredService<LuzVitalDbContext>();
                db.EventosSeguranca.Add(new EventoSeguranca(pendente.OcorridoEm, pendente.Tipo, pendente.Rota,
                    pendente.TiposDeDado, pendente.DescricaoTecnica, traducao.Mensagem, traducao.Modo));
                await db.SaveChangesAsync(ct);
            }
            catch (OperationCanceledException) when (ct.IsCancellationRequested)
            {
                return;
            }
            catch (Exception ex)
            {
                _logger.LogError("Não foi possível gravar o evento de segurança {Tipo}: {Erro}", pendente.Tipo, ex.Message);
            }
        }
    }
}
