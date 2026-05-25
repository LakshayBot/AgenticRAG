using System.ComponentModel.DataAnnotations;

namespace RagSystem.Core.DTOs.Upload;

public class UploadResponse
{
    public Guid UploadId { get; set; }
    public string FileName { get; set; } = string.Empty;
    public long FileSizeBytes { get; set; }
    public string Status { get; set; } = string.Empty;
    public DateTime UploadedAt { get; set; }
}

public class UploadStatusResponse
{
    public Guid UploadId { get; set; }
    public string FileName { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public string? ErrorMessage { get; set; }
    public int? PageCount { get; set; }
    public bool Indexed { get; set; }
    public DateTime? ProcessedAt { get; set; }
    public DateTime? IndexedAt { get; set; }
    public Dictionary<string, object>? Metadata { get; set; }
}

public class UploadListResponse
{
    public List<UploadStatusResponse> Uploads { get; set; } = new();
    public int TotalCount { get; set; }
    public int Page { get; set; }
    public int PageSize { get; set; }
}

public class ProcessUploadRequest
{
    [Required]
    public Guid UploadId { get; set; }
}
