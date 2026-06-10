using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using RagSystem.Core.DTOs.RAG;
using RagSystem.Core.Entities;
using RagSystem.Core.Interfaces;
using RagSystem.Infrastructure.Data;

namespace RagSystem.Infrastructure.Services;

public class RAGService : IRAGService
{
    private readonly IAgenticRAGServiceClient _agenticClient;
    private readonly ICacheService _cache;
    private readonly ApplicationDbContext _context;
    private readonly IConversationService _conversationService;
    private readonly ILogger<RAGService> _logger;

    public RAGService(
        IAgenticRAGServiceClient agenticClient,
        ICacheService cache,
        ApplicationDbContext context,
        IConversationService conversationService,
        ILogger<RAGService> logger)
    {
        _agenticClient = agenticClient;
        _cache = cache;
        _context = context;
        _conversationService = conversationService;
        _logger = logger;
    }

    public async Task<RAGResponse> AskAsync(RAGRequest request, Guid? userId = null)
    {
        // For non-agentic mode, we use the agentic service but with simpler settings
        return await AskAgenticAsync(request, userId);
    }

    public async Task<RAGResponse> AskAgenticAsync(RAGRequest request, Guid? userId = null)
    {
        var stopwatch = Stopwatch.StartNew();

        try
        {
            // Skip cache when conversation history is present — same question can have different
            // answers depending on prior context (e.g. "tell me more" means different things).
            bool hasConversationContext = request.ConversationHistory != null && request.ConversationHistory.Count > 0;

            RAGResponse? cached = null;
            string? cacheKey = null;

            if (!hasConversationContext)
            {
                // Check cache first — include file/advisory scope in key so scoped answers don't
                // collide with all-corpus answers for the same question text.
                var fileScope = request.FileIds != null && request.FileIds.Count > 0
                    ? string.Join(",", request.FileIds.OrderBy(x => x))
                    : "all";
                var advisoryScope = !string.IsNullOrEmpty(request.AdvisoryId) ? request.AdvisoryId : "all";
                cacheKey = $"rag:{ComputeQuestionHash(request.Question)}:{request.TopK}:{fileScope}:{advisoryScope}";
                cached = await _cache.GetAsync<RAGResponse>(cacheKey);
            }

            if (cached != null)
            {
                _logger.LogInformation("Cache hit for RAG question: {Question}", request.Question);
                cached.FromCache = true;
                cached.ResponseTimeMs = stopwatch.ElapsedMilliseconds;
                return cached;
            }

            // Call Python agentic RAG service
            var pythonRequest = new AgenticRAGRequest
            {
                Question = request.Question,
                TopK = request.TopK,
                UseHybrid = request.UseHybrid,
                Model = request.Model ?? "llama3.2:1b",
                FileIds = request.FileIds?.Select(id => $"upload-{id}").ToList(),
                AdvisoryIds = !string.IsNullOrEmpty(request.AdvisoryId) ? new List<string> { request.AdvisoryId } : null,
                SessionId = request.SessionId,
                ConversationHistory = request.ConversationHistory?.Select(t => new ConversationTurnDto
                {
                    Role = t.Role,
                    Content = t.Content
                }).ToList()
            };

            var pythonResponse = await _agenticClient.AskAsync(pythonRequest);

            // Map to .NET response
            var response = new RAGResponse
            {
                Question = request.Question,
                Answer = pythonResponse.Answer,
                Sources = pythonResponse.Sources.Select(s => new SourceDocument
                {
                    SourceId = s.SourceId,
                    Title = s.Title,
                    Authors = s.Authors,
                    ChunkText = s.ChunkText,
                    ChunkIndex = s.ChunkIndex,
                    Score = s.Score
                }).ToList(),
                ChunksUsed = pythonResponse.Sources.Count,
                SearchMode = request.UseHybrid ? "hybrid" : "bm25",
                ReasoningSteps = pythonResponse.ReasoningSteps,
                ResponseTimeMs = stopwatch.ElapsedMilliseconds,
                FromCache = false
            };

            // Save to search history
            if (userId.HasValue)
            {
                var history = new SearchHistory
                {
                    UserId = userId.Value,
                    Question = request.Question,
                    Answer = response.Answer,
                    Sources = response.Sources.Select(s => new Dictionary<string, object>
                    {
                        ["sourceId"] = s.SourceId,
                        ["title"] = s.Title,
                        ["score"] = s.Score
                    }).ToList(),
                    SearchType = request.UseAgentic ? "agentic" : "basic",
                    ResultCount = response.ChunksUsed,
                    ResponseTimeMs = response.ResponseTimeMs,
                    Cached = false
                };

                _context.SearchHistories.Add(history);
                await _context.SaveChangesAsync();

                // Save to conversation chat history (if part of a conversation)
                if (request.ConversationId.HasValue)
                {
                    await _conversationService.SaveMessageAsync(
                        request.ConversationId.Value,
                        "user",
                        request.Question);

                    await _conversationService.SaveMessageAsync(
                        request.ConversationId.Value,
                        "assistant",
                        response.Answer,
                        response.Sources.Select(s => new Dictionary<string, object>
                        {
                            ["sourceId"] = s.SourceId,
                            ["title"] = s.Title,
                            ["score"] = s.Score
                        }).ToList(),
                        response.ResponseTimeMs);
                }
            }

            // Cache the result only for single-turn (non-conversation) queries
            if (!hasConversationContext && cacheKey != null)
            {
                await _cache.SetAsync(cacheKey, response, TimeSpan.FromHours(24));
            }

            _logger.LogInformation(
                "RAG completed: Question={Question}, Sources={SourceCount}, Time={TimeMs}ms, Cached=false",
                request.Question, response.ChunksUsed, response.ResponseTimeMs);

            return response;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error executing RAG for question: {Question}", request.Question);
            throw;
        }
        finally
        {
            stopwatch.Stop();
        }
    }

    public async IAsyncEnumerable<string> AskStreamAsync(RAGRequest request, Guid? userId = null)
    {
        // Get the full response first (Python service does not stream natively)
        var response = await AskAgenticAsync(request, userId);

        // Event 1 — metadata: sources + search context
        var metaEvent = JsonSerializer.Serialize(new
        {
            sources = response.Sources.Select(s => new
            {
                sourceId  = s.SourceId,
                title    = s.Title,
                authors  = s.Authors,
                chunkText = s.ChunkText,
                score    = s.Score
            }),
            chunksUsed = response.ChunksUsed,
            searchMode = response.SearchMode
        });
        yield return metaEvent;

        // Events 2..N — token chunks (word-by-word to simulate streaming)
        var words = response.Answer.Split(' ', StringSplitOptions.None);
        foreach (var word in words)
        {
            var chunkEvent = JsonSerializer.Serialize(new { chunk = word + " " });
            yield return chunkEvent;
            await Task.Delay(8); // reduced from 30ms — LLM is the bottleneck, not streaming
        }

        // Final event — full answer + done flag
        var doneEvent = JsonSerializer.Serialize(new
        {
            answer = response.Answer,
            done   = true
        });
        yield return doneEvent;
    }

    private static string ComputeQuestionHash(string question)
    {
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(question));
        return Convert.ToHexString(bytes)[..16]; // 16-char hex prefix is enough for a cache key
    }
}

