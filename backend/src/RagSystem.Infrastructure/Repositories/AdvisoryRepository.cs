using Microsoft.EntityFrameworkCore;
using RagSystem.Core.Entities;
using RagSystem.Core.Interfaces;
using RagSystem.Infrastructure.Data;

namespace RagSystem.Infrastructure.Repositories;

/// <summary>
/// Repository for GitHub Security Advisory operations
/// </summary>
public class AdvisoryRepository : IAdvisoryRepository
{
    private readonly ApplicationDbContext _context;

    public AdvisoryRepository(ApplicationDbContext context)
    {
        _context = context;
    }

    public async Task<Advisory?> GetByIdAsync(Guid id)
    {
        return await _context.Advisories.FindAsync(id);
    }

    public async Task<Advisory?> GetByGhsaIdAsync(string ghsaId)
    {
        return await _context.Advisories
            .FirstOrDefaultAsync(a => a.GhsaId == ghsaId);
    }

    public async Task<Advisory?> GetByCveIdAsync(string cveId)
    {
        return await _context.Advisories
            .FirstOrDefaultAsync(a => a.CveId == cveId);
    }

    public async Task<IEnumerable<Advisory>> GetRecentAsync(
        int limit = 10,
        string? severity = null,
        string? ecosystem = null)
    {
        var query = _context.Advisories.AsQueryable();

        if (!string.IsNullOrEmpty(severity))
        {
            query = query.Where(a => a.Severity.ToLower() == severity.ToLower());
        }

        if (!string.IsNullOrEmpty(ecosystem))
        {
            query = query.Where(a => a.AffectedEcosystems != null && 
                                   a.AffectedEcosystems.Contains(ecosystem));
        }

        return await query
            .OrderByDescending(a => a.PublishedAt)
            .Take(limit)
            .ToListAsync();
    }

    public async Task<IEnumerable<Advisory>> GetByDateRangeAsync(
        DateTime fromDate,
        DateTime toDate,
        string? severity = null)
    {
        var query = _context.Advisories
            .Where(a => a.PublishedAt >= fromDate && a.PublishedAt <= toDate);

        if (!string.IsNullOrEmpty(severity))
        {
            query = query.Where(a => a.Severity.ToLower() == severity.ToLower());
        }

        return await query
            .OrderByDescending(a => a.PublishedAt)
            .ToListAsync();
    }

    public async Task<int> GetCountAsync(string? severity = null)
    {
        var query = _context.Advisories.AsQueryable();

        if (!string.IsNullOrEmpty(severity))
        {
            query = query.Where(a => a.Severity.ToLower() == severity.ToLower());
        }

        return await query.CountAsync();
    }

    public async Task<Dictionary<string, int>> GetCountBySeverityAsync()
    {
        return await _context.Advisories
            .GroupBy(a => a.Severity.ToLower())
            .Select(g => new { Severity = g.Key, Count = g.Count() })
            .ToDictionaryAsync(x => x.Severity, x => x.Count);
    }

    public async Task<IEnumerable<Advisory>> GetUnindexedCriticalAsync(int limit = 100)
    {
        return await _context.Advisories
            .Where(a => !a.Indexed && 
                       (a.Severity.ToLower() == "critical" || a.Severity.ToLower() == "high"))
            .OrderByDescending(a => a.PublishedAt)
            .Take(limit)
            .ToListAsync();
    }

    public async Task<IEnumerable<Advisory>> GetAllAsync(int limit = 1000)
    {
        return await _context.Advisories
            .OrderByDescending(a => a.PublishedAt)
            .Take(limit)
            .ToListAsync();
    }

    public async Task<IEnumerable<Advisory>> GetUnindexedAsync(int limit = 1000)
    {
        return await _context.Advisories
            .Where(a => !a.Indexed)
            .OrderByDescending(a => a.PublishedAt)
            .Take(limit)
            .ToListAsync();
    }

    public async Task<Advisory> UpsertAsync(Advisory advisory)
    {
        var existing = await GetByGhsaIdAsync(advisory.GhsaId);

        if (existing != null)
        {
            // Update existing
            existing.CveId = advisory.CveId;
            existing.Summary = advisory.Summary;
            existing.Description = advisory.Description;
            existing.Severity = advisory.Severity;
            existing.CvssScore = advisory.CvssScore;
            existing.Type = advisory.Type;
            existing.AffectedEcosystems = advisory.AffectedEcosystems;
            existing.AffectedPackages = advisory.AffectedPackages;
            existing.Vulnerabilities = advisory.Vulnerabilities;
            existing.CweIds = advisory.CweIds;
            existing.Cwes = advisory.Cwes;
            existing.ReferenceUrls = advisory.ReferenceUrls;
            existing.GithubUrl = advisory.GithubUrl;
            existing.PublishedAt = advisory.PublishedAt;
            existing.UpdatedAt = advisory.UpdatedAt;
            existing.WithdrawnAt = advisory.WithdrawnAt;
            existing.ModifiedAt = DateTime.UtcNow;

            _context.Advisories.Update(existing);
            await _context.SaveChangesAsync();
            return existing;
        }
        else
        {
            // Insert new
            _context.Advisories.Add(advisory);
            await _context.SaveChangesAsync();
            return advisory;
        }
    }

    public async Task MarkAsIndexedAsync(string ghsaId)
    {
        var advisory = await GetByGhsaIdAsync(ghsaId);
        if (advisory != null)
        {
            advisory.Indexed = true;
            advisory.IndexedAt = DateTime.UtcNow;
            _context.Advisories.Update(advisory);
            await _context.SaveChangesAsync();
        }
    }

    public async Task<int> BulkInsertAsync(IEnumerable<Advisory> advisories)
    {
        int count = 0;
        foreach (var advisory in advisories)
        {
            await UpsertAsync(advisory);
            count++;
        }
        return count;
    }

    public async Task<bool> DeleteAsync(string ghsaId)
    {
        var advisory = await GetByGhsaIdAsync(ghsaId);
        if (advisory != null)
        {
            _context.Advisories.Remove(advisory);
            await _context.SaveChangesAsync();
            return true;
        }
        return false;
    }
}
