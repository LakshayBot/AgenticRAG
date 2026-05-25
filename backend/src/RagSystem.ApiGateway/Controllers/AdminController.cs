using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using RagSystem.Core.DTOs.Admin;
using RagSystem.Core.Interfaces;

namespace RagSystem.ApiGateway.Controllers;

[Authorize(Policy = "AdminOnly")]
[ApiController]
[Route("api/[controller]")]
public class AdminController : ControllerBase
{
    private readonly IAdminService _adminService;
    private readonly ILogger<AdminController> _logger;

    public AdminController(IAdminService adminService, ILogger<AdminController> logger)
    {
        _adminService = adminService;
        _logger = logger;
    }

    /// <summary>
    /// Get comprehensive system statistics
    /// </summary>
    [HttpGet("stats")]
    [ProducesResponseType(typeof(SystemStatsResponse), StatusCodes.Status200OK)]
    public async Task<ActionResult<SystemStatsResponse>> GetSystemStats()
    {
        try
        {
            var stats = await _adminService.GetSystemStatsAsync();
            return Ok(stats);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting system stats");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    /// <summary>
    /// Get list of all users with pagination
    /// </summary>
    [HttpGet("users")]
    [ProducesResponseType(typeof(UserListResponse), StatusCodes.Status200OK)]
    public async Task<ActionResult<UserListResponse>> GetUsers([FromQuery] int page = 1, [FromQuery] int pageSize = 50)
    {
        try
        {
            var response = await _adminService.GetUsersAsync(page, pageSize);
            return Ok(response);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting users");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    /// <summary>
    /// Disable a user account
    /// </summary>
    [HttpPost("users/{userId}/disable")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> DisableUser(Guid userId)
    {
        try
        {
            var success = await _adminService.DisableUserAsync(userId);
            if (!success)
            {
                return NotFound(new { error = "User not found" });
            }

            return Ok(new { message = "User disabled successfully" });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error disabling user");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    /// <summary>
    /// Enable a user account
    /// </summary>
    [HttpPost("users/{userId}/enable")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> EnableUser(Guid userId)
    {
        try
        {
            var success = await _adminService.EnableUserAsync(userId);
            if (!success)
            {
                return NotFound(new { error = "User not found" });
            }

            return Ok(new { message = "User enabled successfully" });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error enabling user");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    /// <summary>
    /// Get comprehensive health check including Python services
    /// </summary>
    [HttpGet("health")]
    [ProducesResponseType(typeof(Dictionary<string, object>), StatusCodes.Status200OK)]
    public async Task<ActionResult<Dictionary<string, object>>> GetHealthCheck()
    {
        try
        {
            var health = await _adminService.GetHealthCheckAsync();
            return Ok(health);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting health check");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }
}
