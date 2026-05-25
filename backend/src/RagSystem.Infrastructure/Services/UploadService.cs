using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using RagSystem.Core.DTOs.Upload;
using RagSystem.Core.Entities;
using RagSystem.Core.Interfaces;
using RagSystem.Infrastructure.Data;

namespace RagSystem.Infrastructure.Services;

public class UploadService : IUploadService
{
    private readonly ApplicationDbContext _context;
    private readonly IPdfServiceClient _pdfClient;
    private readonly IEmbeddingsServiceClient _embeddingsClient;
    private readonly ISearchServiceClient _searchClient;
    private readonly IConfiguration _configuration;
    private readonly ILogger<UploadService> _logger;
    private readonly IServiceScopeFactory _serviceScopeFactory;
    private readonly string _uploadDirectory;

    public UploadService(
        ApplicationDbContext context,
        IPdfServiceClient pdfClient,
        IEmbeddingsServiceClient embeddingsClient,
        ISearchServiceClient searchClient,
        IConfiguration configuration,
        ILogger<UploadService> logger,
        IServiceScopeFactory serviceScopeFactory)
    {
        _context = context;
        _pdfClient = pdfClient;
        _embeddingsClient = embeddingsClient;
        _searchClient = searchClient;
        _configuration = configuration;
        _logger = logger;
        _serviceScopeFactory = serviceScopeFactory;
        _uploadDirectory = _configuration["Upload:Directory"] ?? "./uploads";

        // Ensure upload directory exists
        Directory.CreateDirectory(_uploadDirectory);
    }

    public async Task<UploadResponse> UploadFileAsync(Stream fileStream, string fileName, long fileSize, string contentType, Guid userId)
    {
        // Validate file
        if (fileSize == 0)
            throw new ArgumentException("File is empty");

        var maxSizeMB = int.Parse(_configuration["Upload:MaxSizeMB"] ?? "20");
        if (fileSize > maxSizeMB * 1024 * 1024)
            throw new ArgumentException($"File size exceeds {maxSizeMB}MB limit");

        if (contentType != "application/pdf")
            throw new ArgumentException("Only PDF files are allowed");

        try
        {
            // Generate unique file name
            var fileId = Guid.NewGuid();
            var safeFileName = $"{fileId}_{Path.GetFileName(fileName)}";
            var filePath = Path.Combine(_uploadDirectory, safeFileName);

            // Save file to disk
            using (var fileStreamOutput = new FileStream(filePath, FileMode.Create))
            {
                await fileStream.CopyToAsync(fileStreamOutput);
            }

            // Create database record
            var uploadedFile = new UploadedFile
            {
                Id = fileId,
                UserId = userId,
                FileName = fileName,
                FilePath = filePath,
                FileSizeBytes = fileSize,
                MimeType = contentType,
                Status = "uploaded"
            };

            _context.UploadedFiles.Add(uploadedFile);
            await _context.SaveChangesAsync();

            _logger.LogInformation(
                "File uploaded: UserId={UserId}, FileName={FileName}, Size={Size}",
                userId, fileName, fileSize);

            // Process upload synchronously (parse, embed, index)
            _logger.LogInformation("Starting synchronous processing for upload: {UploadId}", fileId);
            await ProcessUploadAsync(fileId);

            // Reload file to get updated status
            await _context.Entry(uploadedFile).ReloadAsync();

            return new UploadResponse
            {
                UploadId = fileId,
                FileName = fileName,
                FileSizeBytes = fileSize,
                Status = uploadedFile.Status,
                UploadedAt = uploadedFile.UploadedAt
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error uploading file: {FileName}", fileName);
            throw;
        }
    }

    public async Task<UploadStatusResponse> GetUploadStatusAsync(Guid uploadId, Guid? userId)
    {
        var query = _context.UploadedFiles.AsQueryable();
        
        // If userId is provided, filter by it (for non-admin users)
        if (userId.HasValue)
        {
            query = query.Where(f => f.Id == uploadId && f.UserId == userId.Value);
        }
        else
        {
            // For admin access without userId filter
            query = query.Where(f => f.Id == uploadId);
        }

        var file = await query.FirstOrDefaultAsync();

        if (file == null)
            throw new KeyNotFoundException("Upload not found");

        return new UploadStatusResponse
        {
            UploadId = file.Id,
            FileName = file.FileName,
            Status = file.Status,
            ErrorMessage = file.ErrorMessage,
            PageCount = file.PageCount,
            Indexed = file.Indexed,
            ProcessedAt = file.ProcessedAt,
            IndexedAt = file.IndexedAt,
            Metadata = file.ProcessingMetadata
        };
    }

    public async Task<UploadListResponse> GetUserUploadsAsync(Guid userId, int page = 1, int pageSize = 20)
    {
        var query = _context.UploadedFiles
            .Where(f => f.UserId == userId)
            .OrderByDescending(f => f.UploadedAt);

        var totalCount = await query.CountAsync();
        var files = await query
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync();

        return new UploadListResponse
        {
            Uploads = files.Select(f => new UploadStatusResponse
            {
                UploadId = f.Id,
                FileName = f.FileName,
                Status = f.Status,
                ErrorMessage = f.ErrorMessage,
                PageCount = f.PageCount,
                Indexed = f.Indexed,
                ProcessedAt = f.ProcessedAt,
                IndexedAt = f.IndexedAt,
                Metadata = f.ProcessingMetadata
            }).ToList(),
            TotalCount = totalCount,
            Page = page,
            PageSize = pageSize
        };
    }

    public async Task<bool> DeleteUploadAsync(Guid uploadId, Guid userId)
    {
        var file = await _context.UploadedFiles
            .FirstOrDefaultAsync(f => f.Id == uploadId && f.UserId == userId);

        if (file == null)
            return false;

        try
        {
            // Delete file from disk
            if (File.Exists(file.FilePath))
            {
                File.Delete(file.FilePath);
            }

            // Delete from database
            _context.UploadedFiles.Remove(file);
            await _context.SaveChangesAsync();

            _logger.LogInformation("File deleted: UploadId={UploadId}", uploadId);
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error deleting file: UploadId={UploadId}", uploadId);
            return false;
        }
    }

    public async Task ProcessUploadAsync(Guid uploadId)
    {
        var file = await _context.UploadedFiles.FindAsync(uploadId);
        if (file == null)
        {
            _logger.LogWarning("Upload not found for processing: {UploadId}", uploadId);
            return;
        }

        try
        {
            _logger.LogInformation("Processing upload: {UploadId}", uploadId);

            // Update status
            file.Status = "processing";
            await _context.SaveChangesAsync();

            // Read file content
            var fileContent = await File.ReadAllBytesAsync(file.FilePath);

            // Step 1: Parse PDF using Python service
            var parseResult = await _pdfClient.ParsePdfAsync(fileContent, file.FileName);
            
            file.ExtractedText = parseResult.Text;
            file.PageCount = parseResult.PageCount;
            file.ProcessingMetadata = parseResult.Metadata;
            file.ProcessedAt = DateTime.UtcNow;
            await _context.SaveChangesAsync();

            // Step 2: Generate embeddings
            var embeddings = await _embeddingsClient.GenerateEmbeddingsAsync(parseResult.Chunks);

            // Step 3: Index in OpenSearch
            var indexRequest = new IndexRequest
            {
                PaperId = uploadId,
                SourceId = $"upload-{uploadId}",
                Title = file.FileName,
                Chunks = parseResult.Chunks.Select((chunk, idx) => new ChunkData
                {
                    Text = chunk,
                    Embedding = embeddings.Embeddings[idx],
                    ChunkIndex = idx
                }).ToList()
            };

            var indexed = await _searchClient.IndexChunksAsync(indexRequest);

            if (indexed)
            {
                file.Indexed = true;
                file.IndexedAt = DateTime.UtcNow;
                file.Status = "completed";
            }
            else
            {
                file.Status = "failed";
                file.ErrorMessage = "Failed to index in search engine";
            }

            await _context.SaveChangesAsync();

            _logger.LogInformation(
                "Upload processing completed: {UploadId}, Status={Status}",
                uploadId, file.Status);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing upload: {UploadId}", uploadId);

            file.Status = "failed";
            file.ErrorMessage = ex.Message;
            await _context.SaveChangesAsync();
        }
    }
}
