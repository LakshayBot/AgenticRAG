using System.IdentityModel.Tokens.Jwt;
using System.Net.Http.Headers;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.IdentityModel.Tokens;
using RagSystem.Core.DTOs.Auth;
using RagSystem.Core.Entities;
using RagSystem.Core.Interfaces;
using RagSystem.Infrastructure.Data;

namespace RagSystem.Infrastructure.Services;

public class AuthService : IAuthService
{
    private readonly ApplicationDbContext _context;
    private readonly IConfiguration _configuration;
    private readonly IHttpClientFactory _httpClientFactory;

    public AuthService(ApplicationDbContext context, IConfiguration configuration, IHttpClientFactory httpClientFactory)
    {
        _context = context;
        _configuration = configuration;
        _httpClientFactory = httpClientFactory;
    }

    // ─── Email / Password ────────────────────────────────────────────────────────

    public async Task<AuthResponse> RegisterAsync(RegisterRequest request)
    {
        if (await _context.Users.AnyAsync(u => u.Email == request.Email))
            throw new InvalidOperationException("User with this email already exists");

        var passwordHash = BCrypt.Net.BCrypt.HashPassword(request.Password);

        var user = new User
        {
            Email        = request.Email,
            PasswordHash = passwordHash,
            FirstName    = request.FirstName,
            LastName     = request.LastName,
            Role         = "User",
            IsActive     = true
        };

        _context.Users.Add(user);
        await _context.SaveChangesAsync();

        var accessToken  = GenerateAccessToken(user);
        var refreshToken = await GenerateRefreshTokenAsync(user, string.Empty);

        return new AuthResponse
        {
            AccessToken  = accessToken,
            RefreshToken = refreshToken,
            ExpiresAt    = DateTime.UtcNow.AddMinutes(GetTokenExpirationMinutes()),
            User         = MapToUserDto(user)
        };
    }

    public async Task<AuthResponse> LoginAsync(LoginRequest request)
    {
        var user = await _context.Users.FirstOrDefaultAsync(u => u.Email == request.Email);
        if (user == null || !user.IsActive)
            throw new UnauthorizedAccessException("Invalid email or password");

        // OAuth-only accounts have an empty PasswordHash — block password login for them
        if (string.IsNullOrEmpty(user.PasswordHash) || !BCrypt.Net.BCrypt.Verify(request.Password, user.PasswordHash))
            throw new UnauthorizedAccessException("Invalid email or password");

        user.LastLoginAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();

        var accessToken  = GenerateAccessToken(user);
        var refreshToken = await GenerateRefreshTokenAsync(user, string.Empty);

        return new AuthResponse
        {
            AccessToken  = accessToken,
            RefreshToken = refreshToken,
            ExpiresAt    = DateTime.UtcNow.AddMinutes(GetTokenExpirationMinutes()),
            User         = MapToUserDto(user)
        };
    }

    public async Task<AuthResponse> RefreshTokenAsync(string refreshToken)
    {
        var storedToken = await _context.RefreshTokens
            .Include(rt => rt.User)
            .FirstOrDefaultAsync(rt => rt.Token == refreshToken && !rt.IsRevoked);

        if (storedToken == null || storedToken.ExpiresAt < DateTime.UtcNow)
            throw new UnauthorizedAccessException("Invalid or expired refresh token");

        var user = storedToken.User!;
        if (!user.IsActive)
            throw new UnauthorizedAccessException("User account is disabled");

        storedToken.IsRevoked = true;
        storedToken.RevokedAt = DateTime.UtcNow;

        var accessToken     = GenerateAccessToken(user);
        var newRefreshToken = await GenerateRefreshTokenAsync(user, string.Empty);

        await _context.SaveChangesAsync();

        return new AuthResponse
        {
            AccessToken  = accessToken,
            RefreshToken = newRefreshToken,
            ExpiresAt    = DateTime.UtcNow.AddMinutes(GetTokenExpirationMinutes()),
            User         = MapToUserDto(user)
        };
    }

    public async Task<bool> RevokeTokenAsync(string refreshToken)
    {
        var token = await _context.RefreshTokens
            .FirstOrDefaultAsync(rt => rt.Token == refreshToken && !rt.IsRevoked);

        if (token == null) return false;

        token.IsRevoked = true;
        token.RevokedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();

        return true;
    }

    public async Task<User?> GetUserByIdAsync(Guid userId)  => await _context.Users.FindAsync(userId);
    public async Task<User?> GetUserByEmailAsync(string email)
        => await _context.Users.FirstOrDefaultAsync(u => u.Email == email);

    // ─── OAuth Login ────────────────────────────────────────────────────────────

    public async Task<AuthResponse> OAuthLoginAsync(string provider, string code, string redirectUri, string ipAddress)
    {
        var normalizedProvider = provider.ToLowerInvariant();

        OAuthUserInfo userInfo = normalizedProvider switch
        {
            "google" => await FetchGoogleUserInfoAsync(code, redirectUri),
            "github" => await FetchGitHubUserInfoAsync(code, redirectUri),
            _        => throw new ArgumentException($"Unsupported OAuth provider: {provider}")
        };

        if (string.IsNullOrEmpty(userInfo.Email))
            throw new InvalidOperationException("OAuth provider did not return an email address.");

        // Find existing account by email (auto-link) or by provider+id
        var user = await _context.Users.FirstOrDefaultAsync(u =>
            u.Email == userInfo.Email ||
            (u.Provider == normalizedProvider && u.ProviderId == userInfo.Id));

        if (user == null)
        {
            // First-time OAuth sign-up — create new account (no password)
            user = new User
            {
                Email        = userInfo.Email,
                PasswordHash = string.Empty,
                FirstName    = userInfo.FirstName,
                LastName     = userInfo.LastName,
                AvatarUrl    = userInfo.AvatarUrl,
                Provider     = normalizedProvider,
                ProviderId   = userInfo.Id,
                Role         = "User",
                IsActive     = true
            };
            _context.Users.Add(user);
        }
        else
        {
            // Existing account — fill in OAuth fields if missing, refresh avatar
            user.Provider   ??= normalizedProvider;
            user.ProviderId ??= userInfo.Id;
            if (!string.IsNullOrEmpty(userInfo.AvatarUrl))
                user.AvatarUrl = userInfo.AvatarUrl;
        }

        user.LastLoginAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();

        var accessToken  = GenerateAccessToken(user);
        var refreshToken = await GenerateRefreshTokenAsync(user, ipAddress);

        return new AuthResponse
        {
            AccessToken  = accessToken,
            RefreshToken = refreshToken,
            ExpiresAt    = DateTime.UtcNow.AddMinutes(GetTokenExpirationMinutes()),
            User         = MapToUserDto(user)
        };
    }

    // ─── Google OAuth ────────────────────────────────────────────────────────────

    private async Task<OAuthUserInfo> FetchGoogleUserInfoAsync(string code, string redirectUri)
    {
        var clientId     = _configuration["OAuth:Google:ClientId"]
            ?? throw new InvalidOperationException("Google ClientId not configured");
        var clientSecret = _configuration["OAuth:Google:ClientSecret"]
            ?? throw new InvalidOperationException("Google ClientSecret not configured");

        var http = _httpClientFactory.CreateClient();

        // Exchange code → access token
        var tokenResp = await http.PostAsync("https://oauth2.googleapis.com/token",
            new FormUrlEncodedContent(new Dictionary<string, string>
            {
                ["code"]          = code,
                ["client_id"]     = clientId,
                ["client_secret"] = clientSecret,
                ["redirect_uri"]  = redirectUri,
                ["grant_type"]    = "authorization_code"
            }));

        var tokenJson = await tokenResp.Content.ReadAsStringAsync();
        if (!tokenResp.IsSuccessStatusCode)
            throw new InvalidOperationException($"Google token exchange failed: {tokenJson}");

        using var tokenDoc   = JsonDocument.Parse(tokenJson);
        var accessToken      = tokenDoc.RootElement.GetProperty("access_token").GetString()
            ?? throw new InvalidOperationException("Google token response missing access_token");

        // Fetch profile
        http = _httpClientFactory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        var profileResp = await http.GetAsync("https://www.googleapis.com/oauth2/v2/userinfo");
        var profileJson = await profileResp.Content.ReadAsStringAsync();
        if (!profileResp.IsSuccessStatusCode)
            throw new InvalidOperationException($"Google profile fetch failed: {profileJson}");

        using var doc  = JsonDocument.Parse(profileJson);
        var root       = doc.RootElement;
        var name       = root.TryGetProperty("name", out var np) ? np.GetString() ?? "" : "";
        var parts      = name.Split(' ', 2, StringSplitOptions.RemoveEmptyEntries);

        return new OAuthUserInfo
        {
            Id        = root.TryGetProperty("id",      out var id)  ? id.GetString()  ?? "" : "",
            Email     = root.TryGetProperty("email",   out var em)  ? em.GetString()  ?? "" : "",
            FirstName = parts.Length > 0 ? parts[0] : "",
            LastName  = parts.Length > 1 ? parts[1] : "",
            AvatarUrl = root.TryGetProperty("picture", out var pic) ? pic.GetString()     : null
        };
    }

    // ─── GitHub OAuth ────────────────────────────────────────────────────────────

    private async Task<OAuthUserInfo> FetchGitHubUserInfoAsync(string code, string redirectUri)
    {
        var clientId     = _configuration["OAuth:GitHub:ClientId"]
            ?? throw new InvalidOperationException("GitHub ClientId not configured");
        var clientSecret = _configuration["OAuth:GitHub:ClientSecret"]
            ?? throw new InvalidOperationException("GitHub ClientSecret not configured");

        // Exchange code → access token
        var http = _httpClientFactory.CreateClient();
        http.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
        http.DefaultRequestHeaders.UserAgent.Add(new ProductInfoHeaderValue("CyberGuard", "1.0"));

        var tokenResp = await http.PostAsync("https://github.com/login/oauth/access_token",
            new FormUrlEncodedContent(new Dictionary<string, string>
            {
                ["code"]          = code,
                ["client_id"]     = clientId,
                ["client_secret"] = clientSecret,
                ["redirect_uri"]  = redirectUri
            }));

        var tokenJson = await tokenResp.Content.ReadAsStringAsync();
        if (!tokenResp.IsSuccessStatusCode)
            throw new InvalidOperationException($"GitHub token exchange failed: {tokenJson}");

        using var tokenDoc  = JsonDocument.Parse(tokenJson);
        var accessToken     = tokenDoc.RootElement.GetProperty("access_token").GetString()
            ?? throw new InvalidOperationException("GitHub token response missing access_token");

        // Fetch user profile
        http = _httpClientFactory.CreateClient();
        http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        http.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/vnd.github.v3+json"));
        http.DefaultRequestHeaders.UserAgent.Add(new ProductInfoHeaderValue("CyberGuard", "1.0"));

        var profileResp = await http.GetAsync("https://api.github.com/user");
        var profileJson = await profileResp.Content.ReadAsStringAsync();
        if (!profileResp.IsSuccessStatusCode)
            throw new InvalidOperationException($"GitHub profile fetch failed: {profileJson}");

        using var doc = JsonDocument.Parse(profileJson);
        var root      = doc.RootElement;

        // GitHub may hide email — fall back to /user/emails
        string? email = root.TryGetProperty("email", out var ep) ? ep.GetString() : null;
        if (string.IsNullOrEmpty(email))
        {
            var emailsResp = await http.GetAsync("https://api.github.com/user/emails");
            if (emailsResp.IsSuccessStatusCode)
            {
                using var emailsDoc = JsonDocument.Parse(await emailsResp.Content.ReadAsStringAsync());
                foreach (var entry in emailsDoc.RootElement.EnumerateArray())
                {
                    var isPrimary  = entry.TryGetProperty("primary",  out var p) && p.GetBoolean();
                    var isVerified = entry.TryGetProperty("verified", out var v) && v.GetBoolean();
                    if (isPrimary && isVerified)
                    {
                        email = entry.TryGetProperty("email", out var e) ? e.GetString() : null;
                        break;
                    }
                }
            }
        }

        var displayName = root.TryGetProperty("name",  out var np2) ? np2.GetString() ?? ""
                        : root.TryGetProperty("login", out var lp)  ? lp.GetString()  ?? "" : "";
        var nameParts   = displayName.Split(' ', 2, StringSplitOptions.RemoveEmptyEntries);

        return new OAuthUserInfo
        {
            Id        = root.TryGetProperty("id",         out var idp) ? idp.GetInt64().ToString() : "",
            Email     = email ?? "",
            FirstName = nameParts.Length > 0 ? nameParts[0] : displayName,
            LastName  = nameParts.Length > 1 ? nameParts[1] : "",
            AvatarUrl = root.TryGetProperty("avatar_url", out var av) ? av.GetString() : null
        };
    }

    // ─── JWT + Refresh Token ─────────────────────────────────────────────────────

    public string GenerateAccessToken(User user)
    {
        var tokenHandler = new JwtSecurityTokenHandler();
        var key = Encoding.UTF8.GetBytes(GetJwtSecret());

        var claims = new[]
        {
            new Claim(JwtRegisteredClaimNames.Sub,   user.Id.ToString()),
            new Claim(JwtRegisteredClaimNames.Email, user.Email),
            new Claim(ClaimTypes.Role,               user.Role),
            new Claim("firstName",                   user.FirstName ?? string.Empty),
            new Claim("lastName",                    user.LastName  ?? string.Empty),
            new Claim(JwtRegisteredClaimNames.Jti,   Guid.NewGuid().ToString())
        };

        var tokenDescriptor = new SecurityTokenDescriptor
        {
            Subject            = new ClaimsIdentity(claims),
            Expires            = DateTime.UtcNow.AddMinutes(GetTokenExpirationMinutes()),
            Issuer             = GetJwtIssuer(),
            Audience           = GetJwtAudience(),
            SigningCredentials = new SigningCredentials(
                new SymmetricSecurityKey(key),
                SecurityAlgorithms.HmacSha256Signature)
        };

        return tokenHandler.WriteToken(tokenHandler.CreateToken(tokenDescriptor));
    }

    public async Task<string> GenerateRefreshTokenAsync(User user, string ipAddress)
    {
        var randomBytes = new byte[64];
        using var rng = RandomNumberGenerator.Create();
        rng.GetBytes(randomBytes);
        var token = Convert.ToBase64String(randomBytes);

        _context.RefreshTokens.Add(new RefreshToken
        {
            UserId      = user.Id,
            Token       = token,
            ExpiresAt   = DateTime.UtcNow.AddDays(7),
            CreatedByIp = ipAddress
        });
        await _context.SaveChangesAsync();

        return token;
    }

    // ─── Helpers ─────────────────────────────────────────────────────────────────

    private UserDto MapToUserDto(User user) => new()
    {
        Id        = user.Id,
        Email     = user.Email,
        FirstName = user.FirstName,
        LastName  = user.LastName,
        Role      = user.Role,
        CreatedAt = user.CreatedAt
    };

    private string GetJwtSecret()    => _configuration["JwtSettings:SecretKey"]                    ?? "your-secret-key-min-32-characters-long-for-security";
    private string GetJwtIssuer()    => _configuration["JwtSettings:Issuer"]                       ?? "RagSystem";
    private string GetJwtAudience()  => _configuration["JwtSettings:Audience"]                     ?? "RagSystemUsers";
    private int GetTokenExpirationMinutes() => int.Parse(_configuration["JwtSettings:AccessTokenExpirationMinutes"] ?? "60");

    // ─── Internal DTO ─────────────────────────────────────────────────────────────

    private sealed class OAuthUserInfo
    {
        public string  Id        { get; init; } = string.Empty;
        public string  Email     { get; init; } = string.Empty;
        public string  FirstName { get; init; } = string.Empty;
        public string  LastName  { get; init; } = string.Empty;
        public string? AvatarUrl { get; init; }
    }
}
