using System.Diagnostics;
using Microsoft.Extensions.Logging;
using RagSystem.Core.DTOs.Search;
using RagSystem.Core.Interfaces;

namespace RagSystem.Infrastructure.Services;

public class SearchService : ISearchService
{
    private readonly ISearchServiceClient _searchClient;
    private readonly ICacheService _cache;
    private readonly ILogger<SearchService> _logger;

    public SearchService(
        ISearchServiceClient searchClient,
        ICacheService cache,
        ILogger<SearchService> logger)
    {
        _searchClient = searchClient;
        _cache = cache;
        _logger = logger;
    }

    public async Task<SearchResponse> HybridSearchAsync(SearchRequest request)
    {
        return await ExecuteSearchAsync(request, "hybrid", async (req) =>
            await _searchClient.HybridSearchAsync(req));
    }

    public async Task<SearchResponse> BM25SearchAsync(SearchRequest request)
    {
        return await ExecuteSearchAsync(request, "bm25", async (req) =>
            await _searchClient.BM25SearchAsync(req));
    }

    public async Task<SearchResponse> VectorSearchAsync(SearchRequest request)
    {
        return await ExecuteSearchAsync(request, "vector", async (req) =>
            await _searchClient.VectorSearchAsync(req));
    }

    private async Task<SearchResponse> ExecuteSearchAsync(
        SearchRequest request,
        string searchType,
        Func<PythonSearchRequest, Task<PythonSearchResponse>> searchFunc)
    {
        var stopwatch = Stopwatch.StartNew();

        try
        {
            // Check cache first
            var cacheKey = $"search:{searchType}:{request.Query}:{request.TopK}";
            var cached = await _cache.GetAsync<SearchResponse>(cacheKey);
            if (cached != null)
            {
                _logger.LogInformation("Cache hit for search query: {Query}", request.Query);
                cached.QueryTimeMs = stopwatch.ElapsedMilliseconds;
                return cached;
            }

            // Call Python search service
            var pythonRequest = new PythonSearchRequest
            {
                Query = request.Query,
                TopK = request.TopK,
                Category = request.Category
            };

            var pythonResponse = await searchFunc(pythonRequest);

            // Map to .NET response
            var response = new SearchResponse
            {
                Query = request.Query,
                Results = pythonResponse.Results.Select(r => new SearchResult
                {
                    Id = Guid.TryParse(r.Id, out var id) ? id : Guid.NewGuid(),
                    SourceId = r.SourceId,
                    Title = r.Title,
                    Abstract = r.Abstract,
                    Authors = r.Authors,
                    Score = r.Score,
                    ChunkText = r.ChunkText,
                    ChunkIndex = r.ChunkIndex,
                    Snippet = r.ChunkText,
                    PublishedDate = r.PublishedDate != null ? DateTime.TryParse(r.PublishedDate, out var pd) ? pd : null : null,
                }).ToList(),
                TotalResults = pythonResponse.TotalResults,
                SearchType = searchType,
                QueryTimeMs = stopwatch.ElapsedMilliseconds
            };

            // Cache the result for 1 hour
            await _cache.SetAsync(cacheKey, response, TimeSpan.FromHours(1));

            _logger.LogInformation(
                "Search completed: Type={SearchType}, Query={Query}, Results={ResultCount}, Time={TimeMs}ms",
                searchType, request.Query, response.TotalResults, response.QueryTimeMs);

            return response;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error executing search: {SearchType}, Query: {Query}", searchType, request.Query);
            throw;
        }
        finally
        {
            stopwatch.Stop();
        }
    }
}
