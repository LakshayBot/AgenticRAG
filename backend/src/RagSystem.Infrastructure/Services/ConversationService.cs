using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using RagSystem.Core.DTOs.Conversation;
using RagSystem.Core.Entities;
using RagSystem.Core.Interfaces;
using RagSystem.Infrastructure.Data;

namespace RagSystem.Infrastructure.Services;

public class ConversationService : IConversationService
{
    private readonly ApplicationDbContext _context;
    private readonly ILogger<ConversationService> _logger;

    public ConversationService(ApplicationDbContext context, ILogger<ConversationService> logger)
    {
        _context = context;
        _logger = logger;
    }

    public async Task<List<ConversationDto>> GetConversationsAsync(Guid userId, int take = 20, int skip = 0)
    {
        return await _context.Conversations
            .Where(c => c.UserId == userId)
            .OrderByDescending(c => c.UpdatedAt)
            .Skip(skip)
            .Take(take)
            .Select(c => new ConversationDto
            {
                Id = c.Id,
                Title = c.Title,
                MessageCount = c.Messages.Count,
                LastMessagePreview = c.Messages
                    .OrderByDescending(m => m.CreatedAt)
                    .Select(m => m.Content)
                    .FirstOrDefault(),
                CreatedAt = c.CreatedAt,
                UpdatedAt = c.UpdatedAt
            })
            .ToListAsync();
    }

    public async Task<ConversationDetailDto?> GetConversationAsync(Guid id, Guid userId)
    {
        var conversation = await _context.Conversations
            .Include(c => c.Messages.OrderBy(m => m.CreatedAt))
            .FirstOrDefaultAsync(c => c.Id == id && c.UserId == userId);

        if (conversation == null) return null;

        return new ConversationDetailDto
        {
            Id = conversation.Id,
            Title = conversation.Title,
            Messages = conversation.Messages.Select(m => new ChatMessageDto
            {
                Id = m.Id,
                Role = m.Role,
                Content = m.Content,
                Sources = m.Sources,
                ResponseTimeMs = m.ResponseTimeMs,
                CreatedAt = m.CreatedAt
            }).ToList(),
            CreatedAt = conversation.CreatedAt,
            UpdatedAt = conversation.UpdatedAt
        };
    }

    public async Task<ConversationDto> CreateConversationAsync(Guid userId, string? title = null)
    {
        var conversation = new Conversation
        {
            Id = Guid.NewGuid(),
            UserId = userId,
            Title = title ?? "New chat",
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };

        _context.Conversations.Add(conversation);
        await _context.SaveChangesAsync();

        return new ConversationDto
        {
            Id = conversation.Id,
            Title = conversation.Title,
            MessageCount = 0,
            CreatedAt = conversation.CreatedAt,
            UpdatedAt = conversation.UpdatedAt
        };
    }

    public async Task<ConversationDto?> RenameConversationAsync(Guid id, Guid userId, string title)
    {
        var conversation = await _context.Conversations
            .FirstOrDefaultAsync(c => c.Id == id && c.UserId == userId);

        if (conversation == null) return null;

        conversation.Title = title;
        conversation.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();

        return new ConversationDto
        {
            Id = conversation.Id,
            Title = conversation.Title,
            MessageCount = await _context.ChatMessages.CountAsync(m => m.ConversationId == conversation.Id),
            CreatedAt = conversation.CreatedAt,
            UpdatedAt = conversation.UpdatedAt
        };
    }

    public async Task<bool> DeleteConversationAsync(Guid id, Guid userId)
    {
        var conversation = await _context.Conversations
            .Include(c => c.Messages)
            .FirstOrDefaultAsync(c => c.Id == id && c.UserId == userId);

        if (conversation == null) return false;

        _context.ChatMessages.RemoveRange(conversation.Messages);
        _context.Conversations.Remove(conversation);
        await _context.SaveChangesAsync();

        return true;
    }

    public async Task SaveMessageAsync(Guid conversationId, string role, string content, List<Dictionary<string, object>>? sources = null, double? responseTimeMs = null)
    {
        var conversation = await _context.Conversations
            .FirstOrDefaultAsync(c => c.Id == conversationId);

        if (conversation == null)
        {
            _logger.LogWarning("Conversation {ConversationId} not found, skipping message save", conversationId);
            return;
        }

        var message = new ChatMessage
        {
            ConversationId = conversationId,
            Role = role,
            Content = content,
            Sources = sources,
            ResponseTimeMs = responseTimeMs,
            CreatedAt = DateTime.UtcNow
        };

        _context.ChatMessages.Add(message);

        // Auto-generate title from first user message (first ~60 chars)
        if (role == "user" && conversation.Title == "New chat")
        {
            conversation.Title = content.Length > 60
                ? content[..60] + "..."
                : content;
        }

        conversation.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();
    }
}
