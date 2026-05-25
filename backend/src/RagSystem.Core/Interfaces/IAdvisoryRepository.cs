using RagSystem.Core.Entities;

namespace RagSystem.Core.Interfaces;

/// <summary>
/// Repository interface for GitHub Security Advisory operations
/// </summary>
public interface IAdvisoryRepository
{
    /// <summary>
    /// Get advisory by ID
    /// </summary>
    Task<Advisory?> GetByIdAsync(Guid id);

    /// <summary>
    /// Get advisory by GHSA ID
    /// </summary>
    Task<Advisory?> GetByGhsaIdAsync(string ghsaId);

    /// <summary>
    /// Get advisory by CVE ID
    /// </summary>
    Task<Advisory?> GetByCveIdAsync(string cveId);

    /// <summary>
    /// Get recent advisories with optional filters
    /// </summary>
    Task<IEnumerable<Advisory>> GetRecentAsync(
        int limit = 10,
        string? severity = null,
        string? ecosystem = null);

    /// <summary>
    /// Get advisories by date range
    /// </summary>
    Task<IEnumerable<Advisory>> GetByDateRangeAsync(
        DateTime fromDate,
        DateTime toDate,
        string? severity = null);

    /// <summary>
    /// Get total count of advisories
    /// </summary>
    Task<int> GetCountAsync(string? severity = null);

    /// <summary>
    /// Get count of advisories by severity
    /// </summary>
    Task<Dictionary<string, int>> GetCountBySeverityAsync();

    /// <summary>
    /// Get critical/high severity advisories that haven't been indexed
    /// </summary>
    Task<IEnumerable<Advisory>> GetUnindexedCriticalAsync(int limit = 100);

    /// <summary>
    /// Get all advisories with optional limit
    /// </summary>
    Task<IEnumerable<Advisory>> GetAllAsync(int limit = 1000);

    /// <summary>
    /// Get advisories that haven't been indexed to OpenSearch
    /// </summary>
    Task<IEnumerable<Advisory>> GetUnindexedAsync(int limit = 1000);

    /// <summary>
    /// Insert or update advisory (upsert by GHSA ID)
    /// </summary>
    Task<Advisory> UpsertAsync(Advisory advisory);

    /// <summary>
    /// Mark advisory as indexed
    /// </summary>
    Task MarkAsIndexedAsync(string ghsaId);

    /// <summary>
    /// Bulk insert advisories
    /// </summary>
    Task<int> BulkInsertAsync(IEnumerable<Advisory> advisories);

    /// <summary>
    /// Delete advisory
    /// </summary>
    Task<bool> DeleteAsync(string ghsaId);
}
