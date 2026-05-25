using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace RagSystem.Core.Entities;

/// <summary>
/// Represents an uploaded PDF file
/// </summary>
[Table("uploaded_files", Schema = "dotnet_app")]
public class UploadedFile
{
    [Key]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Required]
    public Guid UserId { get; set; }

    [Required]
    [MaxLength(255)]
    public string FileName { get; set; } = string.Empty;

    [Required]
    [MaxLength(500)]
    public string FilePath { get; set; } = string.Empty;

    public long FileSizeBytes { get; set; }

    [MaxLength(100)]
    public string MimeType { get; set; } = "application/pdf";

    [Required]
    [MaxLength(50)]
    public string Status { get; set; } = "uploaded"; // uploaded, processing, completed, failed

    public string? ErrorMessage { get; set; }

    public string? ExtractedText { get; set; }

    public int? PageCount { get; set; }

    public bool Indexed { get; set; } = false;

    public DateTime? IndexedAt { get; set; }

    public DateTime UploadedAt { get; set; } = DateTime.UtcNow;

    public DateTime? ProcessedAt { get; set; }

    public Dictionary<string, object>? ProcessingMetadata { get; set; }

    // Navigation property
    [ForeignKey("UserId")]
    public virtual User? User { get; set; }
}
