using RagSystem.Core.DTOs.Search;

namespace RagSystem.Core.Interfaces;

public interface ISearchService
{
    Task<SearchResponse> HybridSearchAsync(SearchRequest request);
    Task<SearchResponse> BM25SearchAsync(SearchRequest request);
    Task<SearchResponse> VectorSearchAsync(SearchRequest request);
}
