using RagSystem.Core.DTOs.Auth;
using RagSystem.Core.Entities;

namespace RagSystem.Core.Interfaces;

public interface IAuthService
{
    Task<AuthResponse> RegisterAsync(RegisterRequest request);
    Task<AuthResponse> LoginAsync(LoginRequest request);
    Task<AuthResponse> RefreshTokenAsync(string refreshToken);
    Task<bool> RevokeTokenAsync(string refreshToken);
    Task<User?> GetUserByIdAsync(Guid userId);
    Task<User?> GetUserByEmailAsync(string email);
    string GenerateAccessToken(User user);
    Task<string> GenerateRefreshTokenAsync(User user, string ipAddress);

    /// <summary>
    /// Handles OAuth login/signup for Google and GitHub.
    /// Exchanges the authorization code for a user profile, then finds or creates
    /// the user account (auto-linking by email if an account already exists).
    /// Returns a standard AuthResponse with CyberGuard JWT + refresh token.
    /// </summary>
    Task<AuthResponse> OAuthLoginAsync(string provider, string code, string redirectUri, string ipAddress);
}
