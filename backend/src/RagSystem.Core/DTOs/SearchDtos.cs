using System.ComponentModel.DataAnnotations;

namespace RagSystem.Core.DTOs.Search;

public class SearchRequest
{
    [Required]
    [MaxLength(1000)]
    public string Query { get; set; } = string.Empty;

    [Range(1, 50)]
    public int TopK { get; set; } = 5;

    public bool UseHybrid { get; set; } = true;

    public string? Category { get; set; }

    public DateTime? DateFrom { get; set; }

    public DateTime? DateTo { get; set; }
}

public class SearchResponse
{
    public string Query { get; set; } = string.Empty;
    public List<SearchResult> Results { get; set; } = new();
    public int TotalResults { get; set; }
    public string SearchType { get; set; } = string.Empty;
    public double QueryTimeMs { get; set; }
}

public class SearchResult
{
    public Guid Id { get; set; }
    public string SourceId { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public string? Abstract { get; set; }
    public List<string>? Authors { get; set; }
    public DateTime? PublishedDate { get; set; }
    public double Score { get; set; }
    public string? Snippet { get; set; }
    public string? ChunkText { get; set; }
    public int? ChunkIndex { get; set; }
}
