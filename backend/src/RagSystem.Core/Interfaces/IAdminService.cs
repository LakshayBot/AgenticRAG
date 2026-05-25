using RagSystem.Core.DTOs.Admin;

namespace RagSystem.Core.Interfaces;

public interface IAdminService
{
    Task<SystemStatsResponse> GetSystemStatsAsync();
    Task<UserListResponse> GetUsersAsync(int page = 1, int pageSize = 50);
    Task<bool> DisableUserAsync(Guid userId);
    Task<bool> EnableUserAsync(Guid userId);
    Task<Dictionary<string, object>> GetHealthCheckAsync();
}
