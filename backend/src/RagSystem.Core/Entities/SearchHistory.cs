using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace RagSystem.Core.Entities;

/// <summary>
/// Stores search and RAG query history
/// </summary>
[Table("search_history", Schema = "dotnet_app")]
public class SearchHistory
{
    [Key]
    public long Id { get; set; }

    public Guid? UserId { get; set; }

    [Required]
    public string Question { get; set; } = string.Empty;

    public string? Answer { get; set; }

    [Column(TypeName = "jsonb")]
    public List<Dictionary<string, object>>? Sources { get; set; }

    [MaxLength(50)]
    public string SearchType { get; set; } = "hybrid"; // bm25, vector, hybrid, agentic

    public int ResultCount { get; set; }

    public double? ResponseTimeMs { get; set; }

    public bool Cached { get; set; } = false;

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [Column(TypeName = "jsonb")]
    public Dictionary<string, object>? Metadata { get; set; }

    // Navigation property
    [ForeignKey("UserId")]
    public virtual User? User { get; set; }
}
