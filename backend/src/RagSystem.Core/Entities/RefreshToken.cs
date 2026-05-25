using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace RagSystem.Core.Entities;

/// <summary>
/// Stores refresh tokens for authentication
/// </summary>
[Table("refresh_tokens", Schema = "dotnet_app")]
public class RefreshToken
{
    [Key]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Required]
    public Guid UserId { get; set; }

    [Required]
    [MaxLength(500)]
    public string Token { get; set; } = string.Empty;

    public DateTime ExpiresAt { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public bool IsRevoked { get; set; } = false;

    public DateTime? RevokedAt { get; set; }

    [MaxLength(100)]
    public string? CreatedByIp { get; set; }

    [MaxLength(100)]
    public string? RevokedByIp { get; set; }

    // Navigation property
    [ForeignKey("UserId")]
    public virtual User? User { get; set; }
}
