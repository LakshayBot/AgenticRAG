using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using RagSystem.Core.Interfaces;

namespace RagSystem.Infrastructure.Services.PythonClients;

public class PdfServiceClient : IPdfServiceClient
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<PdfServiceClient> _logger;

    public PdfServiceClient(HttpClient httpClient, ILogger<PdfServiceClient> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
    }

    public async Task<PdfParseResult> ParsePdfAsync(byte[] fileContent, string fileName)
    {
        try
        {
            using var content = new MultipartFormDataContent();
            content.Add(new ByteArrayContent(fileContent), "file", fileName);

            var response = await _httpClient.PostAsync("/api/v1/parse-pdf", content);
            response.EnsureSuccessStatusCode();

            var result = await response.Content.ReadFromJsonAsync<PdfParseResult>();
            return result ?? throw new InvalidOperationException("Failed to parse PDF response");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error calling PDF service for file {FileName}", fileName);
            throw;
        }
    }

    public async Task<bool> HealthCheckAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync("/health");
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }
}

public class EmbeddingsServiceClient : IEmbeddingsServiceClient
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<EmbeddingsServiceClient> _logger;

    public EmbeddingsServiceClient(HttpClient httpClient, ILogger<EmbeddingsServiceClient> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
    }

    public async Task<EmbeddingsResult> GenerateEmbeddingsAsync(List<string> texts)
    {
        try
        {
            var request = new { texts, model = "jina-embeddings-v3" };
            var response = await _httpClient.PostAsJsonAsync("/api/v1/embed", request);
            response.EnsureSuccessStatusCode();

            var result = await response.Content.ReadFromJsonAsync<EmbeddingsResult>();
            return result ?? throw new InvalidOperationException("Failed to parse embeddings response");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error calling Embeddings service");
            throw;
        }
    }

    public async Task<bool> HealthCheckAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync("/health");
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }
}

public class AdvisoryServiceClient : IAdvisoryServiceClient
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<AdvisoryServiceClient> _logger;

    public AdvisoryServiceClient(HttpClient httpClient, ILogger<AdvisoryServiceClient> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
    }

    public async Task<AdvisoryFetchResult> FetchAdvisoriesAsync(AdvisoryFetchRequest request)
    {
        try
        {
            _logger.LogInformation(
                "Fetching advisories: MaxResults={MaxResults}, Severity={Severity}, Ecosystem={Ecosystem}",
                request.MaxResults,
                request.Severity,
                request.Ecosystem
            );

            var response = await _httpClient.PostAsJsonAsync("/api/v1/advisories/fetch", request);
            response.EnsureSuccessStatusCode();

            var result = await response.Content.ReadFromJsonAsync<AdvisoryFetchResult>();
            return result ?? throw new InvalidOperationException("Failed to parse advisory fetch response");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error fetching advisories from Python service");
            throw;
        }
    }

    public async Task<AdvisoryProcessResult> ProcessAdvisoriesAsync(AdvisoryProcessRequest request)
    {
        try
        {
            _logger.LogInformation(
                "Processing {Count} advisories for indexing",
                request.Advisories.Count
            );

            var response = await _httpClient.PostAsJsonAsync("/api/v1/advisories/process", request);
            response.EnsureSuccessStatusCode();

            var result = await response.Content.ReadFromJsonAsync<AdvisoryProcessResult>();
            return result ?? throw new InvalidOperationException("Failed to parse advisory process response");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing advisories in Python service");
            throw;
        }
    }

    public async Task<AdvisoryAskResult> AskAsync(AdvisoryAskRequest request)
    {
        try
        {
            _logger.LogInformation("Advisory RAG ask: {Query}", request.Query);

            var response = await _httpClient.PostAsJsonAsync("/api/v1/ask", request);
            response.EnsureSuccessStatusCode();

            var result = await response.Content.ReadFromJsonAsync<AdvisoryAskResult>();
            return result ?? throw new InvalidOperationException("Failed to parse advisory ask response");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error asking advisory service");
            throw;
        }
    }

    public async Task<bool> HealthCheckAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync("/api/v1/advisories/health");
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }
}

public class SearchServiceClient : ISearchServiceClient
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<SearchServiceClient> _logger;

    public SearchServiceClient(HttpClient httpClient, ILogger<SearchServiceClient> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
    }

    public async Task<PythonSearchResponse> HybridSearchAsync(PythonSearchRequest request)
    {
        return await ExecuteSearchAsync("/api/v1/search/hybrid", request);
    }

    public async Task<PythonSearchResponse> BM25SearchAsync(PythonSearchRequest request)
    {
        return await ExecuteSearchAsync("/api/v1/search/bm25", request);
    }

    public async Task<PythonSearchResponse> VectorSearchAsync(PythonSearchRequest request)
    {
        return await ExecuteSearchAsync("/api/v1/search/vector", request);
    }

    public async Task<bool> IndexChunksAsync(IndexRequest request)
    {
        try
        {
            var response = await _httpClient.PostAsJsonAsync("/api/v1/index/bulk-insert", request);
            response.EnsureSuccessStatusCode();
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error indexing chunks for paper {PaperId}", request.PaperId);
            return false;
        }
    }

    public async Task<AdvisoryChunkCountsResult> GetAdvisoryChunkCountsAsync(int limit = 30)
    {
        try
        {
            var response = await _httpClient.GetAsync($"/api/v1/chunks/advisory-counts?limit={limit}");
            response.EnsureSuccessStatusCode();
            var opts = new System.Text.Json.JsonSerializerOptions {
                PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.SnakeCaseLower,
                PropertyNameCaseInsensitive = true
            };
            var result = await response.Content.ReadFromJsonAsync<AdvisoryChunkCountsResult>(opts);
            return result ?? new AdvisoryChunkCountsResult();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error fetching advisory chunk counts from search service");
            return new AdvisoryChunkCountsResult();
        }
    }

    public async Task<bool> HealthCheckAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync("/health");
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    private async Task<PythonSearchResponse> ExecuteSearchAsync(string endpoint, PythonSearchRequest request)
    {
        try
        {
            var response = await _httpClient.PostAsJsonAsync(endpoint, request);
            response.EnsureSuccessStatusCode();

            var result = await response.Content.ReadFromJsonAsync<PythonSearchResponse>();
            return result ?? new PythonSearchResponse();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error calling Search service at {Endpoint}", endpoint);
            throw;
        }
    }
}

public class AgenticRAGServiceClient : IAgenticRAGServiceClient
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<AgenticRAGServiceClient> _logger;

    public AgenticRAGServiceClient(HttpClient httpClient, ILogger<AgenticRAGServiceClient> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
    }

    public async Task<AgenticRAGResponse> AskAsync(AgenticRAGRequest request)
    {
        try
        {
            // Log the request for debugging
            var fileIdsInfo = request.FileIds != null && request.FileIds.Any() 
                ? string.Join(", ", request.FileIds) 
                : "none";
            _logger.LogInformation(
                "Sending agentic RAG request: Question={Question}, FileIds=[{FileIds}]",
                request.Question,
                fileIdsInfo
            );

            var response = await _httpClient.PostAsJsonAsync("/api/v1/ask-agentic", request);
            response.EnsureSuccessStatusCode();

            var result = await response.Content.ReadFromJsonAsync<AgenticRAGResponse>();
            return result ?? throw new InvalidOperationException("Failed to parse agentic RAG response");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error calling Agentic RAG service");
            throw;
        }
    }

    public async Task<bool> HealthCheckAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync("/health");
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }
}
