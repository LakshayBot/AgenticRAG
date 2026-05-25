namespace RagSystem.Core.DTOs.Admin;

public class SystemStatsResponse
{
    public DatabaseStats Database { get; set; } = new();
    public SearchStats Search { get; set; } = new();
    public CacheStats Cache { get; set; } = new();
    public ServiceHealthStats Services { get; set; } = new();
}

public class DatabaseStats
{
    public int TotalUsers { get; set; }
    public int TotalAdvisories { get; set; }
    public int TotalUploadedFiles { get; set; }
    public int TotalSearches { get; set; }
}

public class SearchStats
{
    public int TodaySearches { get; set; }
    public double AverageResponseTimeMs { get; set; }
    public Dictionary<string, int> SearchTypeDistribution { get; set; } = new();
}

public class CacheStats
{
    public long TotalKeys { get; set; }
    public long UsedMemoryBytes { get; set; }
    public double HitRate { get; set; }
}

public class ServiceHealthStats
{
    public Dictionary<string, ServiceHealth> PythonServices { get; set; } = new();
    public bool DatabaseHealthy { get; set; }
    public bool CacheHealthy { get; set; }
}

public class ServiceHealth
{
    public string Name { get; set; } = string.Empty;
    public bool Healthy { get; set; }
    public double ResponseTimeMs { get; set; }
    public string? ErrorMessage { get; set; }
}

public class UserListResponse
{
    public List<UserAdminDto> Users { get; set; } = new();
    public int TotalCount { get; set; }
}

public class UserAdminDto
{
    public Guid Id { get; set; }
    public string Email { get; set; } = string.Empty;
    public string? FirstName { get; set; }
    public string? LastName { get; set; }
    public string Role { get; set; } = string.Empty;
    public bool IsActive { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime? LastLoginAt { get; set; }
    public int UploadCount { get; set; }
    public int SearchCount { get; set; }
}
