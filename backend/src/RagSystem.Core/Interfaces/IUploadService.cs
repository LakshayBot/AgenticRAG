using RagSystem.Core.DTOs.Upload;

namespace RagSystem.Core.Interfaces;

public interface IUploadService
{
    Task<UploadResponse> UploadFileAsync(Stream fileStream, string fileName, long fileSize, string contentType, Guid userId);
    Task<UploadStatusResponse> GetUploadStatusAsync(Guid uploadId, Guid? userId);
    Task<UploadListResponse> GetUserUploadsAsync(Guid userId, int page = 1, int pageSize = 20);
    Task<bool> DeleteUploadAsync(Guid uploadId, Guid userId);
    Task ProcessUploadAsync(Guid uploadId);
}
