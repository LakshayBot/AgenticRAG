using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using RagSystem.Core.DTOs.RAG;
using RagSystem.Core.Interfaces;

namespace RagSystem.ApiGateway.Controllers;

/// <summary>
/// Controller for chatting with specific uploaded PDFs
/// </summary>
[Authorize]
[ApiController]
[Route("api/[controller]")]
public class PDFChatController : ControllerBase
{
    private readonly IRAGService _ragService;
    private readonly IUploadService _uploadService;
    private readonly ILogger<PDFChatController> _logger;

    public PDFChatController(
        IRAGService ragService,
        IUploadService uploadService,
        ILogger<PDFChatController> logger)
    {
        _ragService = ragService;
        _uploadService = uploadService;
        _logger = logger;
    }

    /// <summary>
    /// Ask a question about a specific PDF
    /// </summary>
    /// <param name="fileId">The uploaded file ID</param>
    /// <param name="request">The question and search parameters</param>
    [HttpPost("{fileId}/ask")]
    [ProducesResponseType(typeof(RAGResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<RAGResponse>> AskPDF(Guid fileId, [FromBody] PDFChatRequest request)
    {
        try
        {
            var userId = GetUserIdFromToken();
            if (userId == null)
            {
                return Unauthorized(new { error = "Invalid token" });
            }

            // Verify user owns this file and it's indexed
            Core.DTOs.Upload.UploadStatusResponse uploadStatus;
            try
            {
                uploadStatus = await _uploadService.GetUploadStatusAsync(fileId, userId.Value);
            }
            catch (KeyNotFoundException)
            {
                return NotFound(new { error = "PDF not found or access denied" });
            }

            // Check if document is ready for querying
            if (uploadStatus.Status == "processing" || uploadStatus.Status == "uploaded")
            {
                return BadRequest(new { error = "Document is still being processed. Please wait a moment and try again." });
            }

            if (uploadStatus.Status == "failed")
            {
                return BadRequest(new { error = $"Document processing failed: {uploadStatus.ErrorMessage}" });
            }

            if (!uploadStatus.Indexed)
            {
                return BadRequest(new { error = "Document is not indexed yet. Please wait a moment and try again." });
            }

            // Create RAG request with file filter
            var ragRequest = new RAGRequest
            {
                Question = request.Question,
                TopK = request.TopK,
                UseHybrid = request.UseHybrid,
                UseAgentic = request.UseAgentic,
                Model = request.Model,
                FileIds = new List<Guid> { fileId }
            };

            var response = await _ragService.AskAgenticAsync(ragRequest, userId);
            return Ok(response);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error asking question about PDF {FileId}", fileId);
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    /// <summary>
    /// Ask a question about multiple PDFs
    /// </summary>
    [HttpPost("ask-multiple")]
    [ProducesResponseType(typeof(RAGResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<RAGResponse>> AskMultiplePDFs([FromBody] MultiplePDFChatRequest request)
    {
        try
        {
            var userId = GetUserIdFromToken();
            if (userId == null)
            {
                return Unauthorized(new { error = "Invalid token" });
            }

            if (request.FileIds == null || request.FileIds.Count == 0)
            {
                return BadRequest(new { error = "At least one file ID must be provided" });
            }

            // Verify user owns all files and they are indexed
            foreach (var fileId in request.FileIds)
            {
                Core.DTOs.Upload.UploadStatusResponse uploadStatus;
                try
                {
                    uploadStatus = await _uploadService.GetUploadStatusAsync(fileId, userId.Value);
                }
                catch (KeyNotFoundException)
                {
                    return NotFound(new { error = $"PDF {fileId} not found or access denied" });
                }

                // Check if document is ready
                if (uploadStatus.Status == "processing" || uploadStatus.Status == "uploaded")
                {
                    return BadRequest(new { error = $"Document {uploadStatus.FileName} is still being processed." });
                }

                if (uploadStatus.Status == "failed")
                {
                    return BadRequest(new { error = $"Document {uploadStatus.FileName} processing failed: {uploadStatus.ErrorMessage}" });
                }

                if (!uploadStatus.Indexed)
                {
                    return BadRequest(new { error = $"Document {uploadStatus.FileName} is not indexed yet." });
                }
            }

            // Create RAG request with file filters
            var ragRequest = new RAGRequest
            {
                Question = request.Question,
                TopK = request.TopK,
                UseHybrid = request.UseHybrid,
                UseAgentic = request.UseAgentic,
                Model = request.Model,
                FileIds = request.FileIds
            };

            var response = await _ragService.AskAgenticAsync(ragRequest, userId);
            return Ok(response);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error asking question about multiple PDFs");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    /// <summary>
    /// Stream responses for a question about a specific PDF
    /// </summary>
    [HttpPost("{fileId}/ask-stream")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task AskPDFStream(Guid fileId, [FromBody] PDFChatRequest request)
    {
        try
        {
            var userId = GetUserIdFromToken();
            if (userId == null)
            {
                Response.StatusCode = 401;
                await Response.WriteAsJsonAsync(new { error = "Invalid token" });
                return;
            }

            // Verify user owns this file
            try
            {
                await _uploadService.GetUploadStatusAsync(fileId, userId.Value);
            }
            catch (KeyNotFoundException)
            {
                Response.StatusCode = 404;
                await Response.WriteAsJsonAsync(new { error = "PDF not found or access denied" });
                return;
            }

            Response.ContentType = "text/event-stream";
            Response.Headers["Cache-Control"] = "no-cache";
            Response.Headers["Connection"] = "keep-alive";

            // Create RAG request with file filter
            var ragRequest = new RAGRequest
            {
                Question   = request.Question,
                TopK       = request.TopK,
                UseHybrid  = request.UseHybrid,
                UseAgentic = request.UseAgentic,
                Model      = request.Model,
                FileIds    = new List<Guid> { fileId }
            };

            await foreach (var chunk in _ragService.AskStreamAsync(ragRequest, userId))
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
            _logger.LogError(ex, "Error in streaming PDF chat");
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

/// <summary>
/// Request for chatting with a single PDF
/// </summary>
public class PDFChatRequest
{
    public string Question { get; set; } = string.Empty;
    public int TopK { get; set; } = 5;
    public bool UseHybrid { get; set; } = true;
    public bool UseAgentic { get; set; } = true;
    public string? Model { get; set; }
}

/// <summary>
/// Request for chatting with multiple PDFs
/// </summary>
public class MultiplePDFChatRequest
{
    public string Question { get; set; } = string.Empty;
    public List<Guid> FileIds { get; set; } = new();
    public int TopK { get; set; } = 5;
    public bool UseHybrid { get; set; } = true;
    public bool UseAgentic { get; set; } = true;
    public string? Model { get; set; }
}
