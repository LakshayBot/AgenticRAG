using RagSystem.Core.DTOs.Conversation;

namespace RagSystem.Core.Interfaces;

public interface IConversationService
{
    Task<List<ConversationDto>> GetConversationsAsync(Guid userId, int take = 20, int skip = 0);
    Task<ConversationDetailDto?> GetConversationAsync(Guid id, Guid userId);
    Task<ConversationDto> CreateConversationAsync(Guid userId, string? title = null);
    Task<ConversationDto?> RenameConversationAsync(Guid id, Guid userId, string title);
    Task<bool> DeleteConversationAsync(Guid id, Guid userId);
    Task SaveMessageAsync(Guid conversationId, string role, string content, List<Dictionary<string, object>>? sources = null, double? responseTimeMs = null);
}
