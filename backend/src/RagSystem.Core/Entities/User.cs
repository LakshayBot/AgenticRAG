using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace RagSystem.Core.Entities;

/// <summary>
/// Represents a user in the system
/// </summary>
[Table("users", Schema = "dotnet_app")]
public class User
{
    [Key]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Required]
    [MaxLength(255)]
    [EmailAddress]
    public string Email { get; set; } = string.Empty;

    [Required]
    [MaxLength(255)]
    public string PasswordHash { get; set; } = string.Empty;

    [MaxLength(100)]
    public string? FirstName { get; set; }

    [MaxLength(100)]
    public string? LastName { get; set; }

    [Required]
    [MaxLength(50)]
    public string Role { get; set; } = "User"; // User, Admin

    public bool IsActive { get; set; } = true;

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public DateTime? LastLoginAt { get; set; }

    // OAuth / social login fields
    [MaxLength(50)]
    public string? Provider { get; set; }   // "google" | "github" | null (password)

    [MaxLength(255)]
    public string? ProviderId { get; set; } // Provider's unique user ID

    [MaxLength(500)]
    public string? AvatarUrl { get; set; }  // Profile picture URL from provider

    // Navigation properties
    public virtual ICollection<UploadedFile> UploadedFiles { get; set; } = new List<UploadedFile>();
    public virtual ICollection<SearchHistory> SearchHistories { get; set; } = new List<SearchHistory>();
    public virtual ICollection<RefreshToken> RefreshTokens { get; set; } = new List<RefreshToken>();
}
