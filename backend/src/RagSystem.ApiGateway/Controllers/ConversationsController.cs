using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using RagSystem.Core.DTOs.Conversation;
using RagSystem.Core.Interfaces;

namespace RagSystem.ApiGateway.Controllers;

[Authorize]
[ApiController]
[Route("api/[controller]")]
public class ConversationsController : ControllerBase
{
    private readonly IConversationService _conversationService;
    private readonly ILogger<ConversationsController> _logger;

    public ConversationsController(IConversationService conversationService, ILogger<ConversationsController> logger)
    {
        _conversationService = conversationService;
        _logger = logger;
    }

    [HttpGet]
    [ProducesResponseType(typeof(List<ConversationDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<List<ConversationDto>>> GetConversations([FromQuery] int take = 20, [FromQuery] int skip = 0)
    {
        try
        {
            var userId = GetUserId();
            var conversations = await _conversationService.GetConversationsAsync(userId, take, skip);
            return Ok(conversations);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error listing conversations");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpPost]
    [ProducesResponseType(typeof(ConversationDto), StatusCodes.Status201Created)]
    public async Task<ActionResult<ConversationDto>> CreateConversation([FromBody] CreateConversationRequest? request)
    {
        try
        {
            var userId = GetUserId();
            var conversation = await _conversationService.CreateConversationAsync(userId, request?.Title);
            return CreatedAtAction(nameof(GetConversation), new { id = conversation.Id }, conversation);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating conversation");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpGet("{id:guid}")]
    [ProducesResponseType(typeof(ConversationDetailDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<ConversationDetailDto>> GetConversation(Guid id)
    {
        try
        {
            var userId = GetUserId();
            var conversation = await _conversationService.GetConversationAsync(id, userId);
            if (conversation == null) return NotFound(new { error = "Conversation not found" });
            return Ok(conversation);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting conversation {Id}", id);
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpPatch("{id:guid}")]
    [ProducesResponseType(typeof(ConversationDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<ConversationDto>> RenameConversation(Guid id, [FromBody] RenameConversationRequest request)
    {
        try
        {
            var userId = GetUserId();
            var conversation = await _conversationService.RenameConversationAsync(id, userId, request.Title);
            if (conversation == null) return NotFound(new { error = "Conversation not found" });
            return Ok(conversation);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error renaming conversation {Id}", id);
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpDelete("{id:guid}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> DeleteConversation(Guid id)
    {
        try
        {
            var userId = GetUserId();
            var deleted = await _conversationService.DeleteConversationAsync(id, userId);
            if (!deleted) return NotFound(new { error = "Conversation not found" });
            return NoContent();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error deleting conversation {Id}", id);
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    private Guid GetUserId()
    {
        var subClaim = User.FindFirst("sub")?.Value;
        if (!string.IsNullOrEmpty(subClaim) && Guid.TryParse(subClaim, out var userGuid))
            return userGuid;

        throw new UnauthorizedAccessException("User ID not found in token");
    }
}
