using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using RagSystem.Core.DTOs.Upload;
using RagSystem.Core.Interfaces;

namespace RagSystem.ApiGateway.Controllers;

[Authorize]
[ApiController]
[Route("api/[controller]")]
public class UploadController : ControllerBase
{
    private readonly IUploadService _uploadService;
    private readonly ILogger<UploadController> _logger;
    private readonly IServiceScopeFactory _serviceScopeFactory;

    public UploadController(
        IUploadService uploadService, 
        ILogger<UploadController> logger,
        IServiceScopeFactory serviceScopeFactory)
    {
        _uploadService = uploadService;
        _logger = logger;
        _serviceScopeFactory = serviceScopeFactory;
    }

    /// <summary>
    /// Upload a PDF file for processing
    /// </summary>
    [HttpPost]
    [RequestSizeLimit(20 * 1024 * 1024)] // 20MB
    [ProducesResponseType(typeof(UploadResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<UploadResponse>> UploadFile(IFormFile file)
    {
        try
        {
            var userId = GetUserIdFromToken();
            if (userId == null)
            {
                return Unauthorized(new { error = "Invalid token" });
            }

            using var stream = file.OpenReadStream();
            var response = await _uploadService.UploadFileAsync(
                stream, 
                file.FileName, 
                file.Length, 
                file.ContentType, 
                userId.Value);
            return Ok(response);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error uploading file");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    /// <summary>
    /// Get upload status by ID
    /// </summary>
    [HttpGet("{uploadId}")]
    [ProducesResponseType(typeof(UploadStatusResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<UploadStatusResponse>> GetUploadStatus(Guid uploadId)
    {
        try
        {
            var userId = GetUserIdFromToken();
            if (userId == null)
            {
                return Unauthorized(new { error = "Invalid token" });
            }

            var response = await _uploadService.GetUploadStatusAsync(uploadId, userId.Value);
            return Ok(response);
        }
        catch (KeyNotFoundException)
        {
            return NotFound(new { error = "Upload not found" });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting upload status");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    /// <summary>
    /// Get all uploads for current user
    /// </summary>
    [HttpGet]
    [ProducesResponseType(typeof(UploadListResponse), StatusCodes.Status200OK)]
    public async Task<ActionResult<UploadListResponse>> GetUserUploads([FromQuery] int page = 1, [FromQuery] int pageSize = 20)
    {
        try
        {
            var userId = GetUserIdFromToken();
            if (userId == null)
            {
                return Unauthorized(new { error = "Invalid token" });
            }

            var response = await _uploadService.GetUserUploadsAsync(userId.Value, page, pageSize);
            return Ok(response);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting user uploads");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    /// <summary>
    /// Delete an uploaded file
    /// </summary>
    [HttpDelete("{uploadId}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> DeleteUpload(Guid uploadId)
    {
        try
        {
            var userId = GetUserIdFromToken();
            if (userId == null)
            {
                return Unauthorized(new { error = "Invalid token" });
            }

            var success = await _uploadService.DeleteUploadAsync(uploadId, userId.Value);
            if (!success)
            {
                return NotFound(new { error = "Upload not found" });
            }

            return NoContent();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error deleting upload");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    /// <summary>
    /// Manually trigger processing for an uploaded file
    /// </summary>
    [HttpPost("{uploadId}/process")]
    [ProducesResponseType(StatusCodes.Status202Accepted)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> ProcessUpload(Guid uploadId)
    {
        try
        {
            var userId = GetUserIdFromToken();
            if (userId == null)
            {
                return Unauthorized(new { error = "Invalid token" });
            }

            var userRole = User.FindFirst("role")?.Value;
            
            // For non-admin users, verify they own the file
            if (userRole != "admin")
            {
                var status = await _uploadService.GetUploadStatusAsync(uploadId, userId.Value);
                if (status == null)
                {
                    return NotFound(new { error = "Upload not found or access denied" });
                }
            }

            // Get file status (admins can access any file)
            var fileStatus = await _uploadService.GetUploadStatusAsync(uploadId, null);
            if (fileStatus == null)
            {
                return NotFound(new { error = "Upload not found" });
            }

            // Check if already processing or completed
            if (fileStatus.Status == "processing")
            {
                return BadRequest(new { error = "File is already being processed" });
            }

            if (fileStatus.Status == "completed" && fileStatus.Indexed)
            {
                return BadRequest(new { error = "File has already been processed and indexed" });
            }

            // Trigger processing
            _ = Task.Run(async () =>
            {
                using var scope = _serviceScopeFactory.CreateScope();
                var uploadService = scope.ServiceProvider.GetRequiredService<IUploadService>();
                await uploadService.ProcessUploadAsync(uploadId);
            });

            return Accepted(new { message = "Processing started", uploadId });
        }
        catch (KeyNotFoundException)
        {
            return NotFound(new { error = "Upload not found" });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error triggering processing for upload");
            return StatusCode(500, new { error = "Internal server error" });
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
