using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using RagSystem.Core.Entities;
using RagSystem.Core.Interfaces;
using RagSystem.ApiGateway.Jobs;
using Hangfire;

namespace RagSystem.ApiGateway.Controllers;

[Authorize]
[ApiController]
[Route("api/[controller]")]
public class AdvisoriesController : ControllerBase
{
    private readonly IAdvisoryRepository _advisoryRepository;
    private readonly IAdvisoryServiceClient _advisoryServiceClient;
    private readonly AdvisoryIngestionJob _ingestionJob;
    private readonly IBackgroundJobClient _backgroundJobClient;
    private readonly ILogger<AdvisoriesController> _logger;

    public AdvisoriesController(
        IAdvisoryRepository advisoryRepository,
        IAdvisoryServiceClient advisoryServiceClient,
        AdvisoryIngestionJob ingestionJob,
        IBackgroundJobClient backgroundJobClient,
        ILogger<AdvisoriesController> logger)
    {
        _advisoryRepository = advisoryRepository;
        _advisoryServiceClient = advisoryServiceClient;
        _ingestionJob = ingestionJob;
        _backgroundJobClient = backgroundJobClient;
        _logger = logger;
    }

    /// <summary>
    /// Manually trigger advisory ingestion from GitHub
    /// </summary>
    [HttpPost("ingest")]
    [ProducesResponseType(typeof(IngestionResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status500InternalServerError)]
    public async Task<ActionResult<IngestionResponse>> IngestAdvisories([FromBody] IngestionRequest request)
    {
        try
        {
            _logger.LogInformation(
                "Manual advisory ingestion triggered: MaxResults={MaxResults}, Severity={Severity}, Ecosystem={Ecosystem}",
                request.MaxResults,
                request.Severity,
                request.Ecosystem
            );

            // Step 1: Fetch advisories from GitHub via Python service
            var fetchRequest = new AdvisoryFetchRequest
            {
                MaxResults = request.MaxResults,
                Severity = request.Severity,
                Ecosystem = request.Ecosystem,
                ModifiedSince = request.ModifiedSince
            };

            var fetchResult = await _advisoryServiceClient.FetchAdvisoriesAsync(fetchRequest);

            _logger.LogInformation("Fetched {Count} advisories from GitHub", fetchResult.TotalFetched);

            // Step 2: Store advisories in PostgreSQL
            int stored = 0;
            int updated = 0;
            int newCount = 0;

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
                    PublishedAt = dto.PublishedAt,
                    UpdatedAt = dto.UpdatedAt,
                    WithdrawnAt = dto.WithdrawnAt
                };

                await _advisoryRepository.UpsertAsync(advisory);
                stored++;

                if (isNew)
                    newCount++;
                else
                    updated++;
            }

            _logger.LogInformation("Stored {Stored} advisories ({New} new, {Updated} updated)", stored, newCount, updated);

            // Step 3: Optionally index to OpenSearch via Python service
            int indexed = 0;
            if (request.IndexToOpenSearch && stored > 0)
            {
                var processRequest = new AdvisoryProcessRequest
                {
                    Advisories = fetchResult.Advisories.Select(a => new AdvisoryDataItem
                    {
                        GhsaId = a.GhsaId,
                        Summary = a.Summary,
                        Description = a.Description ?? string.Empty,
                        Severity = a.Severity,
                        CveId = a.CveId,
                        CvssScore = a.CvssScore.HasValue ? (float?)((float)a.CvssScore.Value) : null,
                        AffectedEcosystems = a.AffectedEcosystems,
                        AffectedPackages = a.AffectedPackages,
                        CweIds = a.CweIds,
                        PublishedAt = a.PublishedAt?.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                        UpdatedAt = a.UpdatedAt?.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                        WithdrawnAt = a.WithdrawnAt?.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                    }).ToList(),
                    ReplaceExisting = true
                };

                var processResult = await _advisoryServiceClient.ProcessAdvisoriesAsync(processRequest);
                indexed = processResult.ChunksIndexed;

                // Mark as indexed
                foreach (var a in fetchResult.Advisories)
                {
                    await _advisoryRepository.MarkAsIndexedAsync(a.GhsaId);
                }

                _logger.LogInformation("Indexed {Indexed} chunks for {Count} advisories", indexed, processResult.AdvisoriesProcessed);
            }

            return Ok(new IngestionResponse
            {
                Status = "success",
                AdvisoriesFetched = fetchResult.TotalFetched,
                AdvisoriesStored = stored,
                AdvisoriesNew = newCount,
                AdvisoriesUpdated = updated,
                ChunksIndexed = indexed,
                SeverityBreakdown = fetchResult.SeverityBreakdown,
                EcosystemBreakdown = fetchResult.EcosystemBreakdown
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Advisory ingestion failed");
            return StatusCode(500, new { error = ex.Message });
        }
    }

    /// <summary>
    /// List advisories with optional severity filter, text search, and pagination
    /// </summary>
    [HttpGet]
    [AllowAnonymous]
    [ProducesResponseType(typeof(AdvisoryListResponse), StatusCodes.Status200OK)]
    public async Task<ActionResult<AdvisoryListResponse>> ListAdvisories(
        [FromQuery] string? severity = null,
        [FromQuery] string? search = null,
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 50)
    {
        try
        {
            // Normalise severity — treat "all" the same as null
            var sev = string.IsNullOrWhiteSpace(severity) || severity.Equals("all", StringComparison.OrdinalIgnoreCase)
                ? null : severity.Trim().ToLowerInvariant();

            // Fetch from DB (limit generous; in-memory text filter below)
            var limit = Math.Clamp(pageSize * page + pageSize, 200, 2000);
            var advisories = await _advisoryRepository.GetRecentAsync(limit: limit, severity: sev);

            // Optional text search (summary / GHSA ID / CVE ID)
            if (!string.IsNullOrWhiteSpace(search))
            {
                var term = search.Trim().ToLowerInvariant();
                advisories = advisories.Where(a =>
                    (a.Summary?.ToLowerInvariant().Contains(term) ?? false) ||
                    (a.GhsaId?.ToLowerInvariant().Contains(term) ?? false) ||
                    (a.CveId?.ToLowerInvariant().Contains(term) ?? false));
            }

            var list = advisories.ToList();
            var total = list.Count;
            var paged = list
                .Skip((page - 1) * pageSize)
                .Take(pageSize)
                .Select(a => new AdvisorySummary
                {
                    GhsaId = a.GhsaId,
                    Severity = a.Severity,
                    Summary = a.Summary.Length > 120 ? a.Summary.Substring(0, 120) + "..." : a.Summary,
                    PublishedAt = a.PublishedAt
                })
                .ToList();

            return Ok(new AdvisoryListResponse
            {
                Total = total,
                Page = page,
                PageSize = pageSize,
                Advisories = paged
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error listing advisories");
            return StatusCode(500, new { error = ex.Message });
        }
    }

    /// <summary>
    /// Get advisory statistics
    /// </summary>
    [HttpGet("stats")]
    [AllowAnonymous]
    [ProducesResponseType(typeof(AdvisoryStatsResponse), StatusCodes.Status200OK)]
    public async Task<ActionResult<AdvisoryStatsResponse>> GetStats()
    {
        try
        {
            var total = await _advisoryRepository.GetCountAsync();
            var severityBreakdown = await _advisoryRepository.GetCountBySeverityAsync();
            var recent = await _advisoryRepository.GetRecentAsync(limit: 10);

            return Ok(new AdvisoryStatsResponse
            {
                TotalAdvisories = total,
                SeverityBreakdown = severityBreakdown,
                RecentAdvisories = recent.Select(a => new AdvisorySummary
                {
                    GhsaId = a.GhsaId,
                    Severity = a.Severity,
                    Summary = a.Summary.Length > 100 ? a.Summary.Substring(0, 100) + "..." : a.Summary,
                    PublishedAt = a.PublishedAt
                }).ToList()
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting advisory stats");
            return StatusCode(500, new { error = ex.Message });
        }
    }

    /// <summary>
    /// Get specific advisory by GHSA ID
    /// </summary>
    [HttpGet("{ghsaId}")]
    [ProducesResponseType(typeof(Advisory), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<Advisory>> GetAdvisory(string ghsaId)
    {
        try
        {
            var advisory = await _advisoryRepository.GetByGhsaIdAsync(ghsaId);

            if (advisory == null)
                return NotFound(new { error = $"Advisory {ghsaId} not found" });

            return Ok(advisory);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting advisory {GhsaId}", ghsaId);
            return StatusCode(500, new { error = ex.Message });
        }
    }

    /// <summary>
    /// Ask a question about security advisories using RAG + Llama
    /// </summary>
    [HttpPost("ask")]
    [ProducesResponseType(typeof(AdvisoryAskResult), StatusCodes.Status200OK)]
    public async Task<ActionResult<AdvisoryAskResult>> Ask([FromBody] AdvisoryAskRequest request)
    {
        try
        {
            _logger.LogInformation("Advisory RAG ask: {Query}", request.Query);
            var result = await _advisoryServiceClient.AskAsync(request);
            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error answering advisory question");
            return StatusCode(500, new { error = ex.Message });
        }
    }

    /// <summary>
    /// Re-index advisories from PostgreSQL into OpenSearch.
    /// Use this after recreating the OpenSearch index or when advisories are missing from search.
    /// </summary>
    [HttpPost("reindex")]
    [ProducesResponseType(typeof(ReindexResponse), StatusCodes.Status202Accepted)]
    [ProducesResponseType(StatusCodes.Status500InternalServerError)]
    public ActionResult<ReindexResponse> Reindex([FromBody] ReindexRequest request)
    {
        try
        {
            bool unindexedOnly = request.UnindexedOnly;
            _logger.LogInformation("Manual reindex enqueued: UnindexedOnly={UnindexedOnly}", unindexedOnly);
            _backgroundJobClient.Enqueue<AdvisoryIngestionJob>(job => job.ReindexAsync(unindexedOnly));
            return Accepted(new ReindexResponse { Status = "enqueued", Message = "Reindex job enqueued. Check Hangfire dashboard for progress." });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to enqueue reindex job");
            return StatusCode(500, new { error = ex.Message });
        }
    }
}

// DTOs
public class IngestionRequest
{
    public int? MaxResults { get; set; }
    public string? Severity { get; set; }
    public string? Ecosystem { get; set; }
    public string? ModifiedSince { get; set; }
    public bool IndexToOpenSearch { get; set; } = true;
}

public class IngestionResponse
{
    public string Status { get; set; } = string.Empty;
    public int AdvisoriesFetched { get; set; }
    public int AdvisoriesStored { get; set; }
    public int AdvisoriesNew { get; set; }
    public int AdvisoriesUpdated { get; set; }
    public int ChunksIndexed { get; set; }
    public Dictionary<string, int> SeverityBreakdown { get; set; } = new();
    public Dictionary<string, int> EcosystemBreakdown { get; set; } = new();
}

public class AdvisoryStatsResponse
{
    public int TotalAdvisories { get; set; }
    public Dictionary<string, int> SeverityBreakdown { get; set; } = new();
    public List<AdvisorySummary> RecentAdvisories { get; set; } = new();
}

public class AdvisorySummary
{
    public string GhsaId { get; set; } = string.Empty;
    public string Severity { get; set; } = string.Empty;
    public string Summary { get; set; } = string.Empty;
    public DateTime? PublishedAt { get; set; }
}

public class ReindexRequest
{
    /// <summary>
    /// If true, only re-index advisories not yet indexed. If false, re-index all.
    /// </summary>
    public bool UnindexedOnly { get; set; } = false;
}

public class ReindexResponse
{
    public string Status { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
}

public class AdvisoryListResponse
{
    public int Total { get; set; }
    public int Page { get; set; }
    public int PageSize { get; set; }
    public List<AdvisorySummary> Advisories { get; set; } = new();
}
