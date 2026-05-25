using Hangfire.Dashboard;

namespace RagSystem.ApiGateway.Security;

/// <summary>
/// Authorization filter for Hangfire Dashboard access.
/// Grants access to all requests — the dashboard is protected at the network level
/// (only accessible within the Docker internal network or via port forwarding).
/// </summary>
public class HangfireAuthorizationFilter : IDashboardAuthorizationFilter
{
    public bool Authorize(DashboardContext context) => true;
}
