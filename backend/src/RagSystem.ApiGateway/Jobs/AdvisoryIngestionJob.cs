using RagSystem.Core.Entities;
using RagSystem.Core.Interfaces;

namespace RagSystem.ApiGateway.Jobs;

/// <summary>
/// Hangfire background job for ingesting GitHub Security Advisories
/// </summary>
public class AdvisoryIngestionJob
{
    private readonly IAdvisoryRepository _advisoryRepository;
    private readonly IAdvisoryServiceClient _advisoryServiceClient;
    private readonly ILogger<AdvisoryIngestionJob> _logger;

    public AdvisoryIngestionJob(
        IAdvisoryRepository advisoryRepository,
        IAdvisoryServiceClient advisoryServiceClient,
        ILogger<AdvisoryIngestionJob> logger)
    {
        _advisoryRepository = advisoryRepository;
        _advisoryServiceClient = advisoryServiceClient;
        _logger = logger;
    }

    /// <summary>
    /// Execute the advisory ingestion job
    /// </summary>
    public async Task ExecuteAsync()
    {
        try
        {
            _logger.LogInformation("Starting scheduled advisory ingestion job");

            // Fetch advisories modified in the last 7 days
            var sevenDaysAgo = DateTime.UtcNow.AddDays(-7).ToString("yyyy-MM-dd");

            var fetchRequest = new AdvisoryFetchRequest
            {
                MaxResults = 100, // Configurable
                ModifiedSince = sevenDaysAgo
            };

            // Step 1: Fetch advisories from GitHub via Python service
            var fetchResult = await _advisoryServiceClient.FetchAdvisoriesAsync(fetchRequest);
            _logger.LogInformation("Fetched {Count} advisories from GitHub", fetchResult.TotalFetched);

            if (fetchResult.TotalFetched == 0)
            {
                _logger.LogInformation("No new advisories to process");
                return;
            }

            // Step 2: Store advisories in PostgreSQL
            int stored = 0;
            int updated = 0;
            int newCount = 0;
            var advisoryItems = new List<AdvisoryDataItem>();

            foreach (var dto in fetchResult.Advisories)
            {
                var existing = await _advisoryRepository.GetByGhsaIdAsync(dto.GhsaId);
                bool isNew = existing == null;

                var advisory = new Advisory
                {
                    GhsaId = dto.GhsaId,
                    CveId = dto.CveId,
                    Summary = dto.Summary,
                    Description = dto.Description,
                    Severity = dto.Severity,
                    CvssScore = dto.CvssScore,
                    Type = dto.Type,
                    AffectedEcosystems = dto.AffectedEcosystems.ToArray(),
                    AffectedPackages = dto.AffectedPackages.ToArray(),
                    Vulnerabilities = dto.Vulnerabilities,
                    CweIds = dto.CweIds.ToArray(),
                    Cwes = dto.Cwes,
                    ReferenceUrls = dto.ReferenceUrls.ToArray(),
                    GithubUrl = dto.GithubUrl,
                    PublishedAt = ToUtc(dto.PublishedAt),
                    UpdatedAt = ToUtc(dto.UpdatedAt),
                    WithdrawnAt = ToUtc(dto.WithdrawnAt)
                };

                await _advisoryRepository.UpsertAsync(advisory);
                stored++;
                advisoryItems.Add(new AdvisoryDataItem
                {
                    GhsaId = dto.GhsaId,
                    Summary = dto.Summary,
                    Description = dto.Description ?? string.Empty,
                    Severity = dto.Severity,
                    CveId = dto.CveId,
                    CvssScore = dto.CvssScore.HasValue ? (float?)((float)dto.CvssScore.Value) : null,
                    AffectedEcosystems = dto.AffectedEcosystems,
                    AffectedPackages = dto.AffectedPackages,
                    CweIds = dto.CweIds,
                    PublishedAt = dto.PublishedAt?.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                    UpdatedAt = dto.UpdatedAt?.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                    WithdrawnAt = dto.WithdrawnAt?.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                });

                if (isNew)
                    newCount++;
                else
                    updated++;
            }

            _logger.LogInformation("Stored {Stored} advisories ({New} new, {Updated} updated)", stored, newCount, updated);

            // Step 3: Process and index to OpenSearch via Python service
            if (advisoryItems.Any())
            {
                var processRequest = new AdvisoryProcessRequest
                {
                    Advisories = advisoryItems,
                    ReplaceExisting = true
                };

                var processResult = await _advisoryServiceClient.ProcessAdvisoriesAsync(processRequest);
                _logger.LogInformation("Indexed {Indexed} chunks for {Count} advisories", processResult.ChunksIndexed, processResult.AdvisoriesProcessed);

                // Mark as indexed
                foreach (var item in advisoryItems)
                {
                    await _advisoryRepository.MarkAsIndexedAsync(item.GhsaId);
                }
            }

            _logger.LogInformation("Advisory ingestion job completed successfully");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Advisory ingestion job failed");
            throw; // Re-throw to let Hangfire handle retry
        }
    }

    /// <summary>
    /// Backfill job: Fetch all advisories (no date filter)
    /// </summary>
    public async Task BackfillAsync(int maxResults = 1000, string? severity = null, string? ecosystem = null)
    {
        try
        {
            _logger.LogInformation("Starting advisory backfill job: MaxResults={MaxResults}, Severity={Severity}, Ecosystem={Ecosystem}",
                maxResults, severity, ecosystem);

            var fetchRequest = new AdvisoryFetchRequest
            {
                MaxResults = maxResults,
                Severity = severity,
                Ecosystem = ecosystem
                // No ModifiedSince - fetch all
            };

            // Step 1: Fetch advisories from GitHub
            var fetchResult = await _advisoryServiceClient.FetchAdvisoriesAsync(fetchRequest);
            _logger.LogInformation("Fetched {Count} advisories from GitHub", fetchResult.TotalFetched);

            if (fetchResult.TotalFetched == 0)
            {
                _logger.LogInformation("No advisories to process");
                return;
            }

            // Step 2: Bulk insert into PostgreSQL
            var advisories = fetchResult.Advisories.Select(dto => new Advisory
            {
                GhsaId = dto.GhsaId,
                CveId = dto.CveId,
                Summary = dto.Summary,
                Description = dto.Description,
                Severity = dto.Severity,
                CvssScore = dto.CvssScore,
                Type = dto.Type,
                AffectedEcosystems = dto.AffectedEcosystems.ToArray(),
                AffectedPackages = dto.AffectedPackages.ToArray(),
                Vulnerabilities = dto.Vulnerabilities,
                CweIds = dto.CweIds.ToArray(),
                Cwes = dto.Cwes,
                ReferenceUrls = dto.ReferenceUrls.ToArray(),
                GithubUrl = dto.GithubUrl,
                PublishedAt = ToUtc(dto.PublishedAt),
                UpdatedAt = ToUtc(dto.UpdatedAt),
                WithdrawnAt = ToUtc(dto.WithdrawnAt)
            }).ToList();

            await _advisoryRepository.BulkInsertAsync(advisories);
            _logger.LogInformation("Bulk inserted {Count} advisories", advisories.Count);

            // Step 3: Process and index to OpenSearch
            var advisoryItems = fetchResult.Advisories.Select(dto => new AdvisoryDataItem
            {
                GhsaId = dto.GhsaId,
                Summary = dto.Summary,
                Description = dto.Description ?? string.Empty,
                Severity = dto.Severity,
                CveId = dto.CveId,
                CvssScore = dto.CvssScore.HasValue ? (float?)((float)dto.CvssScore.Value) : null,
                AffectedEcosystems = dto.AffectedEcosystems,
                AffectedPackages = dto.AffectedPackages,
                CweIds = dto.CweIds,
                PublishedAt = dto.PublishedAt?.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                UpdatedAt = dto.UpdatedAt?.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                WithdrawnAt = dto.WithdrawnAt?.ToString("yyyy-MM-ddTHH:mm:ssZ"),
            }).ToList();
            var processRequest = new AdvisoryProcessRequest
            {
                Advisories = advisoryItems,
                ReplaceExisting = true
            };

            var processResult = await _advisoryServiceClient.ProcessAdvisoriesAsync(processRequest);
            _logger.LogInformation("Indexed {Indexed} chunks for {Count} advisories", processResult.ChunksIndexed, processResult.AdvisoriesProcessed);

            // Mark as indexed
            foreach (var item in advisoryItems)
            {
                await _advisoryRepository.MarkAsIndexedAsync(item.GhsaId);
            }

            _logger.LogInformation("Advisory backfill job completed successfully");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Advisory backfill job failed");
            throw;
        }
    }

    /// <summary>
    /// Re-index existing advisories to OpenSearch
    /// </summary>
    public async Task ReindexAsync(bool unindexedOnly = false)
    {
        try
        {
            _logger.LogInformation("Starting advisory re-index job: UnindexedOnly={UnindexedOnly}", unindexedOnly);

            // Get advisories to re-index
            var advisories = unindexedOnly
                ? await _advisoryRepository.GetUnindexedAsync(limit: 1000)
                : await _advisoryRepository.GetAllAsync(limit: 1000);

            if (!advisories.Any())
            {
                _logger.LogInformation("No advisories to re-index");
                return;
            }

            var advisoryList = advisories.ToList();
            _logger.LogInformation("Re-indexing {Count} advisories", advisoryList.Count);

            var reindexItems = advisoryList.Select(a => new AdvisoryDataItem
            {
                GhsaId = a.GhsaId,
                Summary = a.Summary,
                Description = a.Description ?? string.Empty,
                Severity = a.Severity,
                CveId = a.CveId,
                CvssScore = a.CvssScore.HasValue ? (float?)((float)a.CvssScore.Value) : null,
                AffectedEcosystems = a.AffectedEcosystems?.ToList() ?? new List<string>(),
                AffectedPackages = a.AffectedPackages?.ToList() ?? new List<string>(),
                CweIds = a.CweIds?.ToList() ?? new List<string>(),
                PublishedAt = a.PublishedAt?.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                UpdatedAt = a.UpdatedAt?.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                WithdrawnAt = a.WithdrawnAt?.ToString("yyyy-MM-ddTHH:mm:ssZ"),
            }).ToList();
            var processRequest = new AdvisoryProcessRequest
            {
                Advisories = reindexItems,
                ReplaceExisting = true
            };

            var processResult = await _advisoryServiceClient.ProcessAdvisoriesAsync(processRequest);
            _logger.LogInformation("Indexed {Indexed} chunks for {Count} advisories", processResult.ChunksIndexed, processResult.AdvisoriesProcessed);

            // Mark as indexed
            foreach (var item in reindexItems)
            {
                await _advisoryRepository.MarkAsIndexedAsync(item.GhsaId);
            }

            _logger.LogInformation("Advisory re-index job completed successfully");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Advisory re-index job failed");
            throw;
        }
    }

    /// <summary>
    /// Ensures a DateTime is UTC. Treats Unspecified kind (from JSON without tz) as UTC.
    /// </summary>
    private static DateTime? ToUtc(DateTime? dt)
    {
        if (dt is null) return null;
        return dt.Value.Kind == DateTimeKind.Local
            ? dt.Value.ToUniversalTime()
            : DateTime.SpecifyKind(dt.Value, DateTimeKind.Utc);
    }
}
