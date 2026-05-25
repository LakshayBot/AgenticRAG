using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using RagSystem.Core.DTOs.Admin;
using RagSystem.Core.Interfaces;
using RagSystem.Infrastructure.Data;

namespace RagSystem.Infrastructure.Services;

public class AdminService : IAdminService
{
    private readonly ApplicationDbContext _context;
    private readonly IPdfServiceClient _pdfClient;
    private readonly IEmbeddingsServiceClient _embeddingsClient;
    private readonly ISearchServiceClient _searchClient;
    private readonly IAgenticRAGServiceClient _agenticClient;
    private readonly ILogger<AdminService> _logger;

    public AdminService(
        ApplicationDbContext context,
        IPdfServiceClient pdfClient,
        IEmbeddingsServiceClient embeddingsClient,
        ISearchServiceClient searchClient,
        IAgenticRAGServiceClient agenticClient,
        ILogger<AdminService> logger)
    {
        _context = context;
        _pdfClient = pdfClient;
        _embeddingsClient = embeddingsClient;
        _searchClient = searchClient;
        _agenticClient = agenticClient;
        _logger = logger;
    }

    public async Task<SystemStatsResponse> GetSystemStatsAsync()
    {
        var today = DateTime.UtcNow.Date;

        var response = new SystemStatsResponse
        {
            Database = new DatabaseStats
            {
                TotalUsers = await _context.Users.CountAsync(),
                TotalAdvisories = await _context.Advisories.CountAsync(),
                TotalUploadedFiles = await _context.UploadedFiles.CountAsync(),
                TotalSearches = await _context.SearchHistories.CountAsync()
            },
            Search = new SearchStats
            {
                TodaySearches = await _context.SearchHistories
                    .Where(h => h.CreatedAt >= today)
                    .CountAsync(),
                AverageResponseTimeMs = await _context.SearchHistories
                    .Where(h => h.ResponseTimeMs.HasValue)
                    .Select(h => (double?)h.ResponseTimeMs)
                    .AverageAsync() ?? 0,
                SearchTypeDistribution = await _context.SearchHistories
                    .GroupBy(h => h.SearchType)
                    .Select(g => new { Type = g.Key, Count = g.Count() })
                    .ToDictionaryAsync(x => x.Type, x => x.Count)
            },
            Cache = new CacheStats
            {
                // In real scenario, query Redis for these stats
                TotalKeys = 0,
                UsedMemoryBytes = 0,
                HitRate = 0.0
            },
            Services = await GetServiceHealthAsync()
        };

        return response;
    }

    public async Task<UserListResponse> GetUsersAsync(int page = 1, int pageSize = 50)
    {
        var query = _context.Users.OrderByDescending(u => u.CreatedAt);

        var totalCount = await query.CountAsync();
        var users = await query
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .Include(u => u.UploadedFiles)
            .Include(u => u.SearchHistories)
            .ToListAsync();

        return new UserListResponse
        {
            Users = users.Select(u => new UserAdminDto
            {
                Id = u.Id,
                Email = u.Email,
                FirstName = u.FirstName,
                LastName = u.LastName,
                Role = u.Role,
                IsActive = u.IsActive,
                CreatedAt = u.CreatedAt,
                LastLoginAt = u.LastLoginAt,
                UploadCount = u.UploadedFiles.Count,
                SearchCount = u.SearchHistories.Count
            }).ToList(),
            TotalCount = totalCount
        };
    }

    public async Task<bool> DisableUserAsync(Guid userId)
    {
        var user = await _context.Users.FindAsync(userId);
        if (user == null) return false;

        user.IsActive = false;
        await _context.SaveChangesAsync();

        _logger.LogInformation("User disabled: {UserId}", userId);
        return true;
    }

    public async Task<bool> EnableUserAsync(Guid userId)
    {
        var user = await _context.Users.FindAsync(userId);
        if (user == null) return false;

        user.IsActive = true;
        await _context.SaveChangesAsync();

        _logger.LogInformation("User enabled: {UserId}", userId);
        return true;
    }

    public async Task<Dictionary<string, object>> GetHealthCheckAsync()
    {
        var health = new Dictionary<string, object>
        {
            ["timestamp"] = DateTime.UtcNow,
            ["database"] = await CheckDatabaseHealthAsync(),
            ["pythonServices"] = await GetServiceHealthAsync()
        };

        return health;
    }

    private async Task<bool> CheckDatabaseHealthAsync()
    {
        try
        {
            await _context.Database.CanConnectAsync();
            return true;
        }
        catch
        {
            return false;
        }
    }

    private async Task<ServiceHealthStats> GetServiceHealthAsync()
    {
        var stats = new ServiceHealthStats
        {
            DatabaseHealthy = await CheckDatabaseHealthAsync(),
            CacheHealthy = true, // Assume Redis is healthy if app is running
            PythonServices = new Dictionary<string, ServiceHealth>()
        };

        // Check each Python service
        stats.PythonServices["PdfService"] = await CheckServiceHealthAsync(
            "PDF Processing",
            () => _pdfClient.HealthCheckAsync());

        stats.PythonServices["EmbeddingsService"] = await CheckServiceHealthAsync(
            "Embeddings",
            () => _embeddingsClient.HealthCheckAsync());

        stats.PythonServices["SearchService"] = await CheckServiceHealthAsync(
            "Search",
            () => _searchClient.HealthCheckAsync());

        stats.PythonServices["AgenticRAGService"] = await CheckServiceHealthAsync(
            "Agentic RAG",
            () => _agenticClient.HealthCheckAsync());

        return stats;
    }

    private async Task<ServiceHealth> CheckServiceHealthAsync(string name, Func<Task<bool>> healthCheck)
    {
        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
        
        try
        {
            var healthy = await healthCheck();
            stopwatch.Stop();

            return new ServiceHealth
            {
                Name = name,
                Healthy = healthy,
                ResponseTimeMs = stopwatch.ElapsedMilliseconds
            };
        }
        catch (Exception ex)
        {
            stopwatch.Stop();
            _logger.LogError(ex, "Health check failed for service: {ServiceName}", name);

            return new ServiceHealth
            {
                Name = name,
                Healthy = false,
                ResponseTimeMs = stopwatch.ElapsedMilliseconds,
                ErrorMessage = ex.Message
            };
        }
    }
}
