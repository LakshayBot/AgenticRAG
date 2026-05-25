using RagSystem.Core.DTOs.RAG;

namespace RagSystem.Core.Interfaces;

public interface IRAGService
{
    Task<RAGResponse> AskAsync(RAGRequest request, Guid? userId = null);
    Task<RAGResponse> AskAgenticAsync(RAGRequest request, Guid? userId = null);
    IAsyncEnumerable<string> AskStreamAsync(RAGRequest request, Guid? userId = null);
}
