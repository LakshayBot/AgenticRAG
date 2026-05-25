using System.Text.Json.Serialization;

namespace RagSystem.Core.Interfaces;

/// <summary>
/// Client for Python PDF Processing Service
/// </summary>
public interface IPdfServiceClient
{
    Task<PdfParseResult> ParsePdfAsync(byte[] fileContent, string fileName);
    Task<bool> HealthCheckAsync();
}

public class PdfParseResult
{
    public string Text { get; set; } = string.Empty;
    public List<string> Chunks { get; set; } = new();
    public Dictionary<string, object>? Metadata { get; set; }
    public int PageCount { get; set; }
}

/// <summary>
/// Client for Python Embeddings Service
/// </summary>
public interface IEmbeddingsServiceClient
{
    Task<EmbeddingsResult> GenerateEmbeddingsAsync(List<string> texts);
    Task<bool> HealthCheckAsync();
}

public class EmbeddingsResult
{
    public List<List<float>> Embeddings { get; set; } = new();
    public int Dimension { get; set; }
    public string Model { get; set; } = string.Empty;
}

/// <summary>
/// Client for Python Advisory Processing Service
/// Handles GitHub Advisory fetching, chunking, and indexing
/// </summary>
public interface IAdvisoryServiceClient
{
    /// <summary>
    /// Fetch advisories from GitHub and return as JSON
    /// </summary>
    Task<AdvisoryFetchResult> FetchAdvisoriesAsync(AdvisoryFetchRequest request);

    /// <summary>
    /// Process and index advisories to OpenSearch
    /// </summary>
    Task<AdvisoryProcessResult> ProcessAdvisoriesAsync(AdvisoryProcessRequest request);

    /// <summary>
    /// Ask a question about security advisories using RAG + Llama
    /// </summary>
    Task<AdvisoryAskResult> AskAsync(AdvisoryAskRequest request);

    /// <summary>
    /// Health check
    /// </summary>
    Task<bool> HealthCheckAsync();
}

public class AdvisoryAskRequest
{
    [JsonPropertyName("query")]
    public string Query { get; set; } = string.Empty;

    [JsonPropertyName("use_hybrid")]
    public bool UseHybrid { get; set; } = true;

    [JsonPropertyName("top_k")]
    public int TopK { get; set; } = 5;
}

public class AdvisoryAskResult
{
    [JsonPropertyName("query")]
    public string Query { get; set; } = string.Empty;

    [JsonPropertyName("answer")]
    public string Answer { get; set; } = string.Empty;

    [JsonPropertyName("sources")]
    public List<string> Sources { get; set; } = new();

    [JsonPropertyName("chunks_used")]
    public int ChunksUsed { get; set; }

    [JsonPropertyName("search_mode")]
    public string? SearchMode { get; set; }
}

public class AdvisoryFetchRequest
{
    [JsonPropertyName("max_results")]
    public int? MaxResults { get; set; }

    [JsonPropertyName("severity")]
    public string? Severity { get; set; }

    [JsonPropertyName("ecosystem")]
    public string? Ecosystem { get; set; }

    [JsonPropertyName("modified_since")]
    public string? ModifiedSince { get; set; }
}

public class AdvisoryFetchResult
{
    [JsonPropertyName("advisories")]
    public List<GitHubAdvisoryDto> Advisories { get; set; } = new();

    [JsonPropertyName("total_fetched")]
    public int TotalFetched { get; set; }

    [JsonPropertyName("severity_breakdown")]
    public Dictionary<string, int> SeverityBreakdown { get; set; } = new();

    [JsonPropertyName("ecosystem_breakdown")]
    public Dictionary<string, int> EcosystemBreakdown { get; set; } = new();
}

public class GitHubAdvisoryDto
{
    [JsonPropertyName("ghsa_id")]
    public string GhsaId { get; set; } = string.Empty;

    [JsonPropertyName("cve_id")]
    public string? CveId { get; set; }

    [JsonPropertyName("summary")]
    public string Summary { get; set; } = string.Empty;

    [JsonPropertyName("description")]
    public string? Description { get; set; }

    [JsonPropertyName("severity")]
    public string Severity { get; set; } = string.Empty;

    [JsonPropertyName("cvss_score")]
    public decimal? CvssScore { get; set; }

    [JsonPropertyName("type")]
    public string? Type { get; set; }

    [JsonPropertyName("affected_ecosystems")]
    public List<string> AffectedEcosystems { get; set; } = new();

    [JsonPropertyName("affected_packages")]
    public List<string> AffectedPackages { get; set; } = new();

    [JsonPropertyName("vulnerabilities")]
    public List<Dictionary<string, object>>? Vulnerabilities { get; set; }

    [JsonPropertyName("cwe_ids")]
    public List<string> CweIds { get; set; } = new();

    [JsonPropertyName("cwes")]
    public List<Dictionary<string, object>>? Cwes { get; set; }

    [JsonPropertyName("reference_urls")]
    public List<string> ReferenceUrls { get; set; } = new();

    [JsonPropertyName("github_url")]
    public string? GithubUrl { get; set; }

    [JsonPropertyName("published_at")]
    public DateTime? PublishedAt { get; set; }

    [JsonPropertyName("updated_at")]
    public DateTime? UpdatedAt { get; set; }

    [JsonPropertyName("withdrawn_at")]
    public DateTime? WithdrawnAt { get; set; }
}

public class AdvisoryDataItem
{
    [JsonPropertyName("ghsa_id")]
    public string GhsaId { get; set; } = string.Empty;

    [JsonPropertyName("summary")]
    public string Summary { get; set; } = string.Empty;

    [JsonPropertyName("description")]
    public string Description { get; set; } = string.Empty;

    [JsonPropertyName("severity")]
    public string Severity { get; set; } = string.Empty;

    [JsonPropertyName("cve_id")]
    public string? CveId { get; set; }

    [JsonPropertyName("cvss_score")]
    public float? CvssScore { get; set; }

    [JsonPropertyName("affected_ecosystems")]
    public List<string> AffectedEcosystems { get; set; } = new();

    [JsonPropertyName("affected_packages")]
    public List<string> AffectedPackages { get; set; } = new();

    [JsonPropertyName("cwe_ids")]
    public List<string> CweIds { get; set; } = new();

    [JsonPropertyName("published_at")]
    public string? PublishedAt { get; set; }

    [JsonPropertyName("updated_at")]
    public string? UpdatedAt { get; set; }

    [JsonPropertyName("withdrawn_at")]
    public string? WithdrawnAt { get; set; }

    [JsonPropertyName("metadata")]
    public Dictionary<string, object>? Metadata { get; set; }
}

public class AdvisoryProcessRequest
{
    [JsonPropertyName("advisories")]
    public List<AdvisoryDataItem> Advisories { get; set; } = new();

    [JsonPropertyName("replace_existing")]
    public bool ReplaceExisting { get; set; } = true;
}

public class AdvisoryProcessResult
{
    [JsonPropertyName("advisories_processed")]
    public int AdvisoriesProcessed { get; set; }

    [JsonPropertyName("chunks_created")]
    public int ChunksCreated { get; set; }

    [JsonPropertyName("chunks_indexed")]
    public int ChunksIndexed { get; set; }

    [JsonPropertyName("errors")]
    public List<string> Errors { get; set; } = new();
}

/// <summary>
/// Client for Python Search Service
/// </summary>
public interface ISearchServiceClient
{
    Task<PythonSearchResponse> HybridSearchAsync(PythonSearchRequest request);
    Task<PythonSearchResponse> BM25SearchAsync(PythonSearchRequest request);
    Task<PythonSearchResponse> VectorSearchAsync(PythonSearchRequest request);
    Task<bool> IndexChunksAsync(IndexRequest request);
    Task<AdvisoryChunkCountsResult> GetAdvisoryChunkCountsAsync(int limit = 30);
    Task<bool> HealthCheckAsync();
}

public class AdvisoryChunkCountsResult
{
    public List<AdvisoryChunkCount> Counts { get; set; } = new();
    public int TotalAdvisories { get; set; }
    public int TotalChunks { get; set; }
}

public class AdvisoryChunkCount
{
    public string GhsaId { get; set; } = string.Empty;
    public int ChunkCount { get; set; }
}

public class PythonSearchRequest
{
    [JsonPropertyName("query")]
    public string Query { get; set; } = string.Empty;

    [JsonPropertyName("top_k")]
    public int TopK { get; set; } = 5;

    [JsonPropertyName("category")]
    public string? Category { get; set; }
}

public class PythonSearchResponse
{
    [JsonPropertyName("results")]
    public List<PythonSearchResult> Results { get; set; } = new();

    [JsonPropertyName("total_results")]
    public int TotalResults { get; set; }

    [JsonPropertyName("query_time_ms")]
    public double QueryTimeMs { get; set; }
}

public class PythonSearchResult
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("source_id")]
    public string SourceId { get; set; } = string.Empty;

    [JsonPropertyName("title")]
    public string Title { get; set; } = string.Empty;

    [JsonPropertyName("snippet")]
    public string? Abstract { get; set; }

    [JsonPropertyName("authors")]
    public List<string>? Authors { get; set; }

    [JsonPropertyName("chunk_text")]
    public string? ChunkText { get; set; }

    [JsonPropertyName("chunk_index")]
    public int ChunkIndex { get; set; }

    [JsonPropertyName("score")]
    public double Score { get; set; }

    [JsonPropertyName("published_date")]
    public string? PublishedDate { get; set; }
}

public class IndexRequest
{
    public Guid PaperId { get; set; }
    public string SourceId { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public List<ChunkData> Chunks { get; set; } = new();
}

public class ChunkData
{
    public string Text { get; set; } = string.Empty;
    public List<float> Embedding { get; set; } = new();
    public int ChunkIndex { get; set; }
}

/// <summary>
/// Client for Python Agentic RAG Service
/// </summary>
public interface IAgenticRAGServiceClient
{
    Task<AgenticRAGResponse> AskAsync(AgenticRAGRequest request);
    Task<bool> HealthCheckAsync();
}

public class AgenticRAGRequest
{
    [System.Text.Json.Serialization.JsonPropertyName("question")]
    public string Question { get; set; } = string.Empty;
    
    [System.Text.Json.Serialization.JsonPropertyName("top_k")]
    public int TopK {get; set; } = 5;
    
    [System.Text.Json.Serialization.JsonPropertyName("use_hybrid")]
    public bool UseHybrid { get; set; } = true;
    
    [System.Text.Json.Serialization.JsonPropertyName("model")]
    public string Model { get; set; } = "llama3.2:1b";
    
    [System.Text.Json.Serialization.JsonPropertyName("file_ids")]
    public List<string>? FileIds { get; set; }

    [System.Text.Json.Serialization.JsonPropertyName("advisory_ids")]
    public List<string>? AdvisoryIds { get; set; }

    [System.Text.Json.Serialization.JsonPropertyName("session_id")]
    public string? SessionId { get; set; }

    [System.Text.Json.Serialization.JsonPropertyName("conversation_history")]
    public List<ConversationTurnDto>? ConversationHistory { get; set; }
}

public class ConversationTurnDto
{
    [System.Text.Json.Serialization.JsonPropertyName("role")]
    public string Role { get; set; } = string.Empty;

    [System.Text.Json.Serialization.JsonPropertyName("content")]
    public string Content { get; set; } = string.Empty;
}

public class AgenticRAGResponse
{
    public string Answer { get; set; } = string.Empty;
    public List<AgenticSource> Sources { get; set; } = new();
    public List<string> ReasoningSteps { get; set; } = new();
}

public class AgenticSource
{
    public string SourceId { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public List<string>? Authors { get; set; }
    public string? ChunkText { get; set; }
    public int ChunkIndex { get; set; }
    public double Score { get; set; }
}
