using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.WebUtilities;
using RagSystem.Core.DTOs.Auth;
using RagSystem.Core.Interfaces;

namespace RagSystem.ApiGateway.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AuthController : ControllerBase
{
    private readonly IAuthService _authService;
    private readonly ILogger<AuthController> _logger;
    private readonly IConfiguration _configuration;

    // Google OAuth endpoints
    private const string GoogleAuthUrl    = "https://accounts.google.com/o/oauth2/v2/auth";
    private const string GoogleScopes     = "openid email profile";

    // GitHub OAuth endpoints
    private const string GitHubAuthUrl    = "https://github.com/login/oauth/authorize";
    private const string GitHubScopes     = "read:user user:email";

    public AuthController(IAuthService authService, ILogger<AuthController> logger, IConfiguration configuration)
    {
        _authService   = authService;
        _logger        = logger;
        _configuration = configuration;
    }

    /// <summary>Register a new user</summary>
    [HttpPost("register")]
    [ProducesResponseType(typeof(AuthResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<AuthResponse>> Register([FromBody] RegisterRequest request)
    {
        try
        {
            var response = await _authService.RegisterAsync(request);
            return Ok(response);
        }
        catch (ArgumentException ex)        { return BadRequest(new { error = ex.Message }); }
        catch (InvalidOperationException ex){ return BadRequest(new { error = ex.Message }); }
    }

    /// <summary>Login with email and password</summary>
    [HttpPost("login")]
    [ProducesResponseType(typeof(AuthResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<ActionResult<AuthResponse>> Login([FromBody] LoginRequest request)
    {
        try
        {
            var response = await _authService.LoginAsync(request);
            return Ok(response);
        }
        catch (UnauthorizedAccessException ex) { return Unauthorized(new { error = ex.Message }); }
    }

    /// <summary>Refresh access token using refresh token</summary>
    [HttpPost("refresh")]
    [ProducesResponseType(typeof(AuthResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<ActionResult<AuthResponse>> RefreshToken([FromBody] RefreshTokenRequest request)
    {
        try
        {
            var response = await _authService.RefreshTokenAsync(request.RefreshToken);
            return Ok(response);
        }
        catch (UnauthorizedAccessException ex) { return Unauthorized(new { error = ex.Message }); }
    }

    /// <summary>Get current user information</summary>
    [Authorize]
    [HttpGet("me")]
    [ProducesResponseType(typeof(UserDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<ActionResult<UserDto>> GetCurrentUser()
    {
        var userId = User.FindFirst("sub")?.Value;
        if (string.IsNullOrEmpty(userId) || !Guid.TryParse(userId, out var userGuid))
            return Unauthorized(new { error = "Invalid token" });

        var email     = User.FindFirst("email")?.Value;
        var firstName = User.FindFirst("firstName")?.Value;
        var lastName  = User.FindFirst("lastName")?.Value;
        var role      = User.FindFirst("role")?.Value;

        return Ok(new UserDto
        {
            Id        = userGuid,
            Email     = email     ?? "",
            FirstName = firstName ?? "",
            LastName  = lastName  ?? "",
            Role      = role      ?? "user"
        });
    }

    // ─── OAuth: Initiate ─────────────────────────────────────────────────────────

    /// <summary>
    /// Redirects the browser to the OAuth provider's consent screen.
    /// Supported providers: "google", "github"
    /// </summary>
    [HttpGet("oauth/{provider}")]
    public IActionResult OAuthRedirect([FromRoute] string provider)
    {
        var redirectUri = GetCallbackUrl(provider);
        string authUrl;

        switch (provider.ToLowerInvariant())
        {
            case "google":
                var googleClientId = _configuration["OAuth:Google:ClientId"]
                    ?? throw new InvalidOperationException("Google ClientId not configured");
                authUrl = QueryHelpers.AddQueryString(GoogleAuthUrl, new Dictionary<string, string?>
                {
                    ["client_id"]     = googleClientId,
                    ["redirect_uri"]  = redirectUri,
                    ["response_type"] = "code",
                    ["scope"]         = GoogleScopes,
                    ["access_type"]   = "offline",
                    ["prompt"]        = "select_account"
                });
                break;

            case "github":
                var githubClientId = _configuration["OAuth:GitHub:ClientId"]
                    ?? throw new InvalidOperationException("GitHub ClientId not configured");
                authUrl = QueryHelpers.AddQueryString(GitHubAuthUrl, new Dictionary<string, string?>
                {
                    ["client_id"]    = githubClientId,
                    ["redirect_uri"] = redirectUri,
                    ["scope"]        = GitHubScopes
                });
                break;

            default:
                return BadRequest(new { error = $"Unsupported OAuth provider: {provider}" });
        }

        return Redirect(authUrl);
    }

    // ─── OAuth: Callback ─────────────────────────────────────────────────────────

    /// <summary>
    /// Handles the OAuth provider callback. Exchanges the code for tokens,
    /// upserts the user, issues CyberGuard JWT + refresh token, and redirects
    /// to the frontend /oauth-callback page with tokens in the query string.
    /// </summary>
    [HttpGet("oauth/{provider}/callback")]
    public async Task<IActionResult> OAuthCallback(
        [FromRoute] string provider,
        [FromQuery] string? code,
        [FromQuery] string? error)
    {
        var frontendBase = _configuration["OAuth:RedirectBaseUrl"] ?? "http://localhost:3000";

        if (!string.IsNullOrEmpty(error) || string.IsNullOrEmpty(code))
        {
            _logger.LogWarning("OAuth callback error for {Provider}: {Error}", provider, error);
            return Redirect($"{frontendBase}/login?error=oauth_denied");
        }

        try
        {
            var redirectUri = GetCallbackUrl(provider);
            var ipAddress   = HttpContext.Connection.RemoteIpAddress?.ToString() ?? string.Empty;

            var authResponse = await _authService.OAuthLoginAsync(provider, code, redirectUri, ipAddress);

            // Redirect to frontend OAuth callback page — tokens travel in the URL fragment
            // (short-lived access token only; refresh token goes as a query param so the
            //  frontend page can persist it to localStorage just like a normal login)
            var callbackUrl = QueryHelpers.AddQueryString(
                $"{frontendBase}/oauth-callback",
                new Dictionary<string, string?>
                {
                    ["token"]        = authResponse.AccessToken,
                    ["refreshToken"] = authResponse.RefreshToken,
                    ["expiresAt"]    = authResponse.ExpiresAt.ToString("o")
                });

            return Redirect(callbackUrl);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "OAuth login failed for provider {Provider}", provider);
            var frontendErr = $"{frontendBase}/login?error=oauth_failed";
            return Redirect(frontendErr);
        }
    }

    // ─── Helpers ─────────────────────────────────────────────────────────────────

    private string GetCallbackUrl(string provider)
    {
        // The backend's own public URL — defaults to localhost:8000 in development
        var backendBase = $"{Request.Scheme}://{Request.Host}";
        return $"{backendBase}/api/auth/oauth/{provider.ToLowerInvariant()}/callback";
    }
}
