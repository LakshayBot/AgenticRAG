using Dapper;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using RagSystem.Core.Interfaces;
using RagSystem.Infrastructure.Data;

namespace RagSystem.ApiGateway.Controllers;

/// <summary>
/// Analytics endpoints — aggregates SearchHistory and Advisory data.
/// Admin users see platform-wide data; regular users see only their own data.
/// </summary>
[Authorize]
[ApiController]
[Route("api/[controller]")]
public class AnalyticsController : ControllerBase
{
    private readonly ApplicationDbContext _db;
    private readonly ISearchServiceClient _searchServiceClient;
    private readonly ILogger<AnalyticsController> _logger;

    public AnalyticsController(
        ApplicationDbContext db,
        ISearchServiceClient searchServiceClient,
        ILogger<AnalyticsController> logger)
    {
        _db = db;
        _searchServiceClient = searchServiceClient;
        _logger = logger;
    }

    // ─── Helpers ────────────────────────────────────────────────────────────────

    private bool IsAdmin => User.IsInRole("Admin") ||
        User.Claims.Any(c => c.Type == "role" && c.Value.Equals("Admin", StringComparison.OrdinalIgnoreCase));

    private Guid? CurrentUserId
    {
        get
        {
            var raw = User.Claims.FirstOrDefault(c =>
                c.Type == System.Security.Claims.ClaimTypes.NameIdentifier ||
                c.Type == "sub" || c.Type == "userId")?.Value;
            return Guid.TryParse(raw, out var id) ? id : null;
        }
    }

    private IQueryable<RagSystem.Core.Entities.SearchHistory> ScopedHistory()
    {
        var q = _db.SearchHistories.AsNoTracking();
        if (!IsAdmin && CurrentUserId.HasValue)
            q = q.Where(h => h.UserId == CurrentUserId.Value);
        return q;
    }

    // ─── GET /api/analytics/overview ───────────────────────────────────────────

    /// <summary>
    /// Top-level KPIs: total queries, average response time, cache hit rate, total advisories.
    /// Admin also gets unique active users and total users.
    /// </summary>
    [HttpGet("overview")]
    [ProducesResponseType(typeof(AnalyticsOverviewResponse), StatusCodes.Status200OK)]
    public async Task<ActionResult<AnalyticsOverviewResponse>> GetOverview()
    {
        try
        {
            var history = await ScopedHistory()
                .Select(h => new { h.ResponseTimeMs, h.Cached })
                .ToListAsync();

            var totalAdvisories = await _db.Advisories.CountAsync();
            var indexedAdvisories = await _db.Advisories.CountAsync(a => a.Indexed);

            var totalQueries = history.Count;
            var avgResponseMs = history.Count > 0
                ? history.Where(h => h.ResponseTimeMs.HasValue).Select(h => h.ResponseTimeMs!.Value).DefaultIfEmpty(0).Average()
                : 0;
            var cacheHits = history.Count(h => h.Cached);
            var cacheHitRate = totalQueries > 0 ? Math.Round((double)cacheHits / totalQueries * 100, 1) : 0;

            var resp = new AnalyticsOverviewResponse
            {
                TotalQueries = totalQueries,
                AvgResponseTimeMs = Math.Round(avgResponseMs, 0),
                CacheHitRate = cacheHitRate,
                TotalAdvisories = totalAdvisories,
                IndexedAdvisories = indexedAdvisories,
            };

            if (IsAdmin)
            {
                resp.TotalUsers = await _db.Users.CountAsync();
                resp.ActiveUsers = await _db.Users.CountAsync(u => u.IsActive);
                resp.UniqueQueryingUsers = await _db.SearchHistories
                    .Where(h => h.UserId != null)
                    .Select(h => h.UserId)
                    .Distinct()
                    .CountAsync();
            }

            return Ok(resp);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting analytics overview");
            return StatusCode(500, new { error = ex.Message });
        }
    }

    // ─── GET /api/analytics/queries/timeline ───────────────────────────────────

    /// <summary>Queries per calendar day for the last N days.</summary>
    [HttpGet("queries/timeline")]
    [ProducesResponseType(typeof(List<TimelinePoint>), StatusCodes.Status200OK)]
    public async Task<ActionResult<List<TimelinePoint>>> GetQueryTimeline([FromQuery] int days = 30)
    {
        try
        {
            var since = DateTime.UtcNow.Date.AddDays(-days + 1);
            var raw = await ScopedHistory()
                .Where(h => h.CreatedAt >= since)
                .GroupBy(h => h.CreatedAt.Date)
                .Select(g => new { Date = g.Key, Count = g.Count() })
                .ToListAsync();

            // Fill missing days with 0
            var lookup = raw.ToDictionary(r => r.Date, r => r.Count);
            var result = Enumerable.Range(0, days)
                .Select(i => since.AddDays(i))
                .Select(d => new TimelinePoint
                {
                    Date = d.ToString("yyyy-MM-dd"),
                    Count = lookup.TryGetValue(d, out var c) ? c : 0
                })
                .ToList();

            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting query timeline");
            return StatusCode(500, new { error = ex.Message });
        }
    }

    // ─── GET /api/analytics/queries/response-times ─────────────────────────────

    /// <summary>Average, P95, min, max response time per search type.</summary>
    [HttpGet("queries/response-times")]
    [ProducesResponseType(typeof(List<ResponseTimeStats>), StatusCodes.Status200OK)]
    public async Task<ActionResult<List<ResponseTimeStats>>> GetResponseTimes()
    {
        try
        {
            var rows = await ScopedHistory()
                .Where(h => h.ResponseTimeMs.HasValue)
                .Select(h => new { h.SearchType, Ms = h.ResponseTimeMs!.Value })
                .ToListAsync();

            var result = rows
                .GroupBy(r => r.SearchType)
                .Select(g =>
                {
                    var sorted = g.Select(x => x.Ms).OrderBy(x => x).ToList();
                    var p95Idx = (int)Math.Ceiling(sorted.Count * 0.95) - 1;
                    return new ResponseTimeStats
                    {
                        SearchType = g.Key,
                        AvgMs = Math.Round(sorted.Average(), 0),
                        P95Ms = Math.Round(sorted[Math.Max(0, p95Idx)], 0),
                        MinMs = Math.Round(sorted.First(), 0),
                        MaxMs = Math.Round(sorted.Last(), 0),
                        Count = sorted.Count
                    };
                })
                .OrderBy(x => x.SearchType)
                .ToList();

            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting response time stats");
            return StatusCode(500, new { error = ex.Message });
        }
    }

    // ─── GET /api/analytics/queries/by-type ────────────────────────────────────

    /// <summary>Query count broken down by search type.</summary>
    [HttpGet("queries/by-type")]
    [ProducesResponseType(typeof(List<TypeBreakdown>), StatusCodes.Status200OK)]
    public async Task<ActionResult<List<TypeBreakdown>>> GetQueryByType()
    {
        try
        {
            var result = await ScopedHistory()
                .GroupBy(h => h.SearchType)
                .Select(g => new TypeBreakdown { Type = g.Key, Count = g.Count() })
                .ToListAsync();

            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting query type breakdown");
            return StatusCode(500, new { error = ex.Message });
        }
    }

    // ─── GET /api/analytics/queries/top ────────────────────────────────────────

    /// <summary>Top 20 most-asked questions with frequency and average response time.</summary>
    [HttpGet("queries/top")]
    [ProducesResponseType(typeof(List<TopQuestion>), StatusCodes.Status200OK)]
    public async Task<ActionResult<List<TopQuestion>>> GetTopQuestions([FromQuery] int limit = 20)
    {
        try
        {
            var result = await ScopedHistory()
                .GroupBy(h => h.Question)
                .Select(g => new TopQuestion
                {
                    Question = g.Key,
                    Count = g.Count(),
                    AvgResponseMs = g.Average(h => (double?)h.ResponseTimeMs) ?? 0
                })
                .OrderByDescending(q => q.Count)
                .Take(limit)
                .ToListAsync();

            // Round after projection (EF can't call Math.Round in SQL)
            result.ForEach(r => r.AvgResponseMs = Math.Round(r.AvgResponseMs, 0));

            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting top questions");
            return StatusCode(500, new { error = ex.Message });
        }
    }

    // ─── GET /api/analytics/queries/cache-performance ──────────────────────────

    /// <summary>Cached vs. uncached query counts per day for the last N days.</summary>
    [HttpGet("queries/cache-performance")]
    [ProducesResponseType(typeof(List<CachePoint>), StatusCodes.Status200OK)]
    public async Task<ActionResult<List<CachePoint>>> GetCachePerformance([FromQuery] int days = 30)
    {
        try
        {
            var since = DateTime.UtcNow.Date.AddDays(-days + 1);
            var raw = await ScopedHistory()
                .Where(h => h.CreatedAt >= since)
                .Select(h => new { Date = h.CreatedAt.Date, h.Cached })
                .ToListAsync();

            var byDay = raw
                .GroupBy(r => r.Date)
                .ToDictionary(
                    g => g.Key,
                    g => new { Cached = g.Count(x => x.Cached), Uncached = g.Count(x => !x.Cached) }
                );

            var result = Enumerable.Range(0, days)
                .Select(i => since.AddDays(i))
                .Select(d => new CachePoint
                {
                    Date = d.ToString("yyyy-MM-dd"),
                    Cached = byDay.TryGetValue(d, out var v) ? v.Cached : 0,
                    Uncached = byDay.TryGetValue(d, out var v2) ? v2.Uncached : 0
                })
                .ToList();

            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting cache performance");
            return StatusCode(500, new { error = ex.Message });
        }
    }

    // ─── GET /api/analytics/advisories/timeline ────────────────────────────────

    /// <summary>Advisories published per month (last 12 months by default).</summary>
    [HttpGet("advisories/timeline")]
    [ProducesResponseType(typeof(List<TimelinePoint>), StatusCodes.Status200OK)]
    public async Task<ActionResult<List<TimelinePoint>>> GetAdvisoryTimeline([FromQuery] int months = 12)
    {
        try
        {
            var since = new DateTime(DateTime.UtcNow.Year, DateTime.UtcNow.Month, 1, 0, 0, 0, DateTimeKind.Utc).AddMonths(-months + 1);
            var raw = await _db.Advisories.AsNoTracking()
                .Where(a => a.PublishedAt >= since)
                .Select(a => new { Year = a.PublishedAt!.Value.Year, Month = a.PublishedAt.Value.Month })
                .ToListAsync();

            var lookup = raw
                .GroupBy(r => new { r.Year, r.Month })
                .ToDictionary(g => g.Key, g => g.Count());

            var result = Enumerable.Range(0, months)
                .Select(i => since.AddMonths(i))
                .Select(d => new TimelinePoint
                {
                    Date = d.ToString("yyyy-MM"),
                    Count = lookup.TryGetValue(new { Year = d.Year, Month = d.Month }, out var c) ? c : 0
                })
                .ToList();

            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting advisory timeline");
            return StatusCode(500, new { error = ex.Message });
        }
    }

    // ─── GET /api/analytics/advisories/ecosystems ──────────────────────────────

    /// <summary>Top affected ecosystems across all advisories (unnested from array).</summary>
    [HttpGet("advisories/ecosystems")]
    [ProducesResponseType(typeof(List<EcosystemCount>), StatusCodes.Status200OK)]
    public async Task<ActionResult<List<EcosystemCount>>> GetEcosystems([FromQuery] int limit = 15)
    {
        try
        {
            // Pull AffectedEcosystems arrays from DB and flatten in memory
            var arrays = await _db.Advisories.AsNoTracking()
                .Where(a => a.AffectedEcosystems != null)
                .Select(a => a.AffectedEcosystems!)
                .ToListAsync();

            var result = arrays
                .SelectMany(arr => arr)
                .Where(e => !string.IsNullOrWhiteSpace(e))
                .GroupBy(e => e.Trim().ToLowerInvariant())
                .Select(g => new EcosystemCount { Ecosystem = g.Key, Count = g.Count() })
                .OrderByDescending(e => e.Count)
                .Take(limit)
                .ToList();

            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting ecosystem breakdown");
            return StatusCode(500, new { error = ex.Message });
        }
    }

    // ─── GET /api/analytics/advisories/cvss-distribution ──────────────────────

    /// <summary>CVSS score distribution across 4 buckets: low / medium / high / critical.</summary>
    [HttpGet("advisories/cvss-distribution")]
    [ProducesResponseType(typeof(List<CvssDistributionItem>), StatusCodes.Status200OK)]
    public async Task<ActionResult<List<CvssDistributionItem>>> GetCvssDistribution()
    {
        try
        {
            var scores = await _db.Advisories.AsNoTracking()
                .Where(a => a.CvssScore.HasValue)
                .Select(a => a.CvssScore!.Value)
                .ToListAsync();

            var result = new List<CvssDistributionItem>
            {
                new() { Range = "Low (0–3.9)",      Min = 0m,  Max = 3.9m,  Count = scores.Count(s => s >= 0m && s <= 3.9m) },
                new() { Range = "Medium (4.0–6.9)", Min = 4m,  Max = 6.9m,  Count = scores.Count(s => s >= 4m && s <= 6.9m) },
                new() { Range = "High (7.0–8.9)",   Min = 7m,  Max = 8.9m,  Count = scores.Count(s => s >= 7m && s <= 8.9m) },
                new() { Range = "Critical (9–10)",  Min = 9m,  Max = 10m,   Count = scores.Count(s => s >= 9m && s <= 10m) },
            };

            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting CVSS distribution");
            return StatusCode(500, new { error = ex.Message });
        }
    }

    // ─── GET /api/analytics/advisories/cwe-breakdown ───────────────────────────

    /// <summary>Top CWE IDs by frequency.</summary>
    [HttpGet("advisories/cwe-breakdown")]
    [ProducesResponseType(typeof(List<CweCount>), StatusCodes.Status200OK)]
    public async Task<ActionResult<List<CweCount>>> GetCweBreakdown([FromQuery] int limit = 15)
    {
        try
        {
            var arrays = await _db.Advisories.AsNoTracking()
                .Where(a => a.CweIds != null)
                .Select(a => a.CweIds!)
                .ToListAsync();

            var result = arrays
                .SelectMany(arr => arr)
                .Where(c => !string.IsNullOrWhiteSpace(c))
                .GroupBy(c => c.Trim().ToUpperInvariant())
                .Select(g => new CweCount { CweId = g.Key, Count = g.Count() })
                .OrderByDescending(c => c.Count)
                .Take(limit)
                .ToList();

            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting CWE breakdown");
            return StatusCode(500, new { error = ex.Message });
        }
    }

    // ─── GET /api/analytics/advisories/trending ────────────────────────────────

    /// <summary>
    /// Most-queried advisories — parsed from the Sources JSONB array in search_history.
    /// Uses raw SQL for the jsonb unnest + group-by.
    /// </summary>
    [HttpGet("advisories/trending")]
    [ProducesResponseType(typeof(List<TrendingAdvisory>), StatusCodes.Status200OK)]
    public async Task<ActionResult<List<TrendingAdvisory>>> GetTrendingAdvisories([FromQuery] int limit = 10)
    {
        try
        {
            // Extract sourceId values from the sources JSONB array in search_history
            // Each element is an object; we look for "sourceId" or "SourceId" keys
            var scopeCondition = IsAdmin
                ? ""
                : CurrentUserId.HasValue
                    ? $"AND sh.\"UserId\" = '{CurrentUserId.Value}'"
                    : "AND 1=0"; // no user — return empty

            var sql = $"""
                SELECT
                    src->>'sourceId' AS ghsa_id,
                    COUNT(*)::int AS query_count
                FROM dotnet_app.search_history sh,
                     jsonb_array_elements(sh."Sources") AS src
                WHERE sh."Sources" IS NOT NULL
                  AND src->>'sourceId' LIKE 'GHSA-%'
                  {scopeCondition}
                GROUP BY src->>'sourceId'
                ORDER BY query_count DESC
                LIMIT {limit}
                """;

            var connection = _db.Database.GetDbConnection();
            var rows = (await connection.QueryAsync<TrendingRaw>(sql)).ToList();

            // Enrich with severity + summary from the advisories table
            var ghsaIds = rows.Select(r => r.ghsa_id).ToList();
            var advisories = await _db.Advisories.AsNoTracking()
                .Where(a => ghsaIds.Contains(a.GhsaId))
                .Select(a => new { a.GhsaId, a.Severity, a.Summary })
                .ToListAsync();

            var lookup = advisories.ToDictionary(a => a.GhsaId);

            var result = rows.Select(r =>
            {
                lookup.TryGetValue(r.ghsa_id, out var info);
                return new TrendingAdvisory
                {
                    GhsaId = r.ghsa_id,
                    QueryCount = r.query_count,
                    Severity = info?.Severity ?? "unknown",
                    Summary = info?.Summary != null && info.Summary.Length > 100
                        ? info.Summary[..100] + "..."
                        : info?.Summary ?? r.ghsa_id
                };
            }).ToList();

            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting trending advisories");
            return StatusCode(500, new { error = ex.Message });
        }
    }

    // ─── GET /api/analytics/chunks/per-advisory ────────────────────────────────

    /// <summary>Chunk counts per advisory from OpenSearch (top N by count).</summary>
    [HttpGet("chunks/per-advisory")]
    [ProducesResponseType(typeof(AdvisoryChunkCountsResult), StatusCodes.Status200OK)]
    public async Task<ActionResult<AdvisoryChunkCountsResult>> GetChunksPerAdvisory([FromQuery] int limit = 30)
    {
        try
        {
            var result = await _searchServiceClient.GetAdvisoryChunkCountsAsync(limit);
            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error fetching chunk counts per advisory");
            return StatusCode(500, new { error = ex.Message });
        }
    }
}

// ─── Projection type for raw SQL trending query ─────────────────────────────
// EF Core SqlQueryRaw requires a keyless entity or a class with matching property names
file class TrendingRaw
{
    public string ghsa_id { get; set; } = string.Empty;
    public int query_count { get; set; }
}

// ─── DTOs ────────────────────────────────────────────────────────────────────

public class AnalyticsOverviewResponse
{
    public int TotalQueries { get; set; }
    public double AvgResponseTimeMs { get; set; }
    public double CacheHitRate { get; set; }
    public int TotalAdvisories { get; set; }
    public int IndexedAdvisories { get; set; }
    // Admin-only fields (null for regular users)
    public int? TotalUsers { get; set; }
    public int? ActiveUsers { get; set; }
    public int? UniqueQueryingUsers { get; set; }
}

public class TimelinePoint
{
    public string Date { get; set; } = string.Empty;
    public int Count { get; set; }
}

public class ResponseTimeStats
{
    public string SearchType { get; set; } = string.Empty;
    public double AvgMs { get; set; }
    public double P95Ms { get; set; }
    public double MinMs { get; set; }
    public double MaxMs { get; set; }
    public int Count { get; set; }
}

public class TypeBreakdown
{
    public string Type { get; set; } = string.Empty;
    public int Count { get; set; }
}

public class TopQuestion
{
    public string Question { get; set; } = string.Empty;
    public int Count { get; set; }
    public double AvgResponseMs { get; set; }
}

public class CachePoint
{
    public string Date { get; set; } = string.Empty;
    public int Cached { get; set; }
    public int Uncached { get; set; }
}

public class EcosystemCount
{
    public string Ecosystem { get; set; } = string.Empty;
    public int Count { get; set; }
}

public class CvssDistributionItem
{
    public string Range { get; set; } = string.Empty;
    public decimal Min { get; set; }
    public decimal Max { get; set; }
    public int Count { get; set; }
}

public class CweCount
{
    public string CweId { get; set; } = string.Empty;
    public int Count { get; set; }
}

public class TrendingAdvisory
{
    public string GhsaId { get; set; } = string.Empty;
    public int QueryCount { get; set; }
    public string Severity { get; set; } = string.Empty;
    public string Summary { get; set; } = string.Empty;
}
