using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace RagSystem.Core.Entities;

/// <summary>
/// Represents a GitHub Security Advisory in the system.
/// Stores vulnerability information fetched from GitHub Security Advisories API.
/// </summary>
[Table("advisories", Schema = "dotnet_app")]
public class Advisory
{
    /// <summary>
    /// Primary key - auto-generated UUID
    /// </summary>
    [Key]
    public Guid Id { get; set; } = Guid.NewGuid();

    /// <summary>
    /// GitHub Security Advisory ID (e.g., GHSA-xxxx-xxxx-xxxx)
    /// </summary>
    [Required]
    [MaxLength(50)]
    public string GhsaId { get; set; } = string.Empty;

    /// <summary>
    /// CVE identifier if available (e.g., CVE-2024-12345)
    /// </summary>
    [MaxLength(50)]
    public string? CveId { get; set; }

    /// <summary>
    /// Brief summary of the vulnerability
    /// </summary>
    [Required]
    public string Summary { get; set; } = string.Empty;

    /// <summary>
    /// Detailed description of the vulnerability
    /// </summary>
    public string? Description { get; set; }

    /// <summary>
    /// Severity level: critical, high, medium, low
    /// </summary>
    [Required]
    [MaxLength(20)]
    public string Severity { get; set; } = string.Empty;

    /// <summary>
    /// CVSS score (0.0 to 10.0)
    /// </summary>
    public decimal? CvssScore { get; set; }

    /// <summary>
    /// Advisory type (e.g., reviewed, unreviewed)
    /// </summary>
    [MaxLength(50)]
    public string? Type { get; set; }

    /// <summary>
    /// JSON array of affected ecosystems (npm, pip, go, etc.)
    /// </summary>
    public string[]? AffectedEcosystems { get; set; }

    /// <summary>
    /// JSON array of affected package names
    /// </summary>
    public string[]? AffectedPackages { get; set; }

    /// <summary>
    /// JSONB field containing detailed vulnerability information
    /// Structure: [{ "package": {...}, "ecosystem": "...", "vulnerable_version_range": "...", "patched_versions": [...] }]
    /// </summary>
    [Column(TypeName = "jsonb")]
    public List<Dictionary<string, object>>? Vulnerabilities { get; set; }

    /// <summary>
    /// JSON array of CWE identifiers (e.g., ["CWE-79", "CWE-89"])
    /// </summary>
    public string[]? CweIds { get; set; }

    /// <summary>
    /// JSONB field containing detailed CWE information
    /// Structure: [{ "cwe_id": "CWE-79", "name": "..." }]
    /// </summary>
    [Column(TypeName = "jsonb")]
    public List<Dictionary<string, object>>? Cwes { get; set; }

    /// <summary>
    /// Array of reference URLs
    /// </summary>
    public string[]? ReferenceUrls { get; set; }

    /// <summary>
    /// GitHub advisory URL
    /// </summary>
    [MaxLength(500)]
    public string? GithubUrl { get; set; }

    /// <summary>
    /// When the advisory was first published
    /// </summary>
    public DateTime? PublishedAt { get; set; }

    /// <summary>
    /// When the advisory was last updated
    /// </summary>
    public DateTime? UpdatedAt { get; set; }

    /// <summary>
    /// When the advisory was withdrawn (if applicable)
    /// </summary>
    public DateTime? WithdrawnAt { get; set; }

    /// <summary>
    /// Whether the advisory has been indexed to OpenSearch
    /// </summary>
    public bool Indexed { get; set; } = false;

    /// <summary>
    /// When the advisory was indexed
    /// </summary>
    public DateTime? IndexedAt { get; set; }

    /// <summary>
    /// When this record was created in our database
    /// </summary>
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    /// <summary>
    /// When this record was last updated in our database
    /// </summary>
    public DateTime? ModifiedAt { get; set; }
}
