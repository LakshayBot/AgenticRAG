using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using RagSystem.Core.DTOs.RAG;
using RagSystem.Core.Interfaces;

namespace RagSystem.ApiGateway.Controllers;

[Authorize]
[ApiController]
[Route("api/[controller]")]
public class RAGController : ControllerBase
{
    private readonly IRAGService _ragService;
    private readonly ILogger<RAGController> _logger;

    public RAGController(IRAGService ragService, ILogger<RAGController> logger)
    {
        _ragService = ragService;
        _logger = logger;
    }

    /// <summary>
    /// Ask a question using basic RAG
    /// </summary>
    [HttpPost("ask")]
    [ProducesResponseType(typeof(RAGResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<RAGResponse>> Ask([FromBody] RAGRequest request)
    {
        try
        {
            var userId = GetUserIdFromToken();
            var response = await _ragService.AskAsync(request, userId);
            return Ok(response);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error in RAG ask");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    /// <summary>
    /// Ask a question using agentic RAG with reasoning
    /// </summary>
    [HttpPost("ask-agentic")]
    [ProducesResponseType(typeof(RAGResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<RAGResponse>> AskAgentic([FromBody] RAGRequest request)
    {
        try
        {
            var userId = GetUserIdFromToken();
            var response = await _ragService.AskAgenticAsync(request, userId);
            return Ok(response);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error in agentic RAG ask");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    /// <summary>
    /// Ask a question with streaming response
    /// </summary>
    [HttpPost("ask-stream")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task AskStream([FromBody] RAGRequest request)
    {
        try
        {
            var userId = GetUserIdFromToken();
            
            Response.ContentType = "text/event-stream";
            Response.Headers["Cache-Control"] = "no-cache";
            Response.Headers["Connection"] = "keep-alive";

            await foreach (var chunk in _ragService.AskStreamAsync(request, userId))
            {
                var message = $"data: {chunk}\n\n";
                await Response.WriteAsync(message);
                await Response.Body.FlushAsync();
            }

            await Response.WriteAsync("data: [DONE]\n\n");
            await Response.Body.FlushAsync();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error in streaming RAG ask");
            if (!Response.HasStarted)
            {
                Response.StatusCode = 500;
                await Response.WriteAsJsonAsync(new { error = "Internal server error" });
            }
        }
    }

    private Guid? GetUserIdFromToken()
    {
        var userId = User.FindFirst("sub")?.Value;
        if (!string.IsNullOrEmpty(userId) && Guid.TryParse(userId, out var userGuid))
        {
            return userGuid;
        }
        return null;
    }
}
