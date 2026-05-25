using Hangfire;
using Hangfire.Storage;
using Microsoft.AspNetCore.Mvc;

namespace RagSystem.ApiGateway.Controllers;

/// <summary>
/// Endpoint to inspect and trigger background jobs without the Hangfire dashboard UI.
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class JobsController : ControllerBase
{
    private readonly ILogger<JobsController> _logger;

    public JobsController(ILogger<JobsController> logger)
    {
        _logger = logger;
    }

    /// <summary>
    /// Get the status of all recurring jobs and recent executions.
    /// </summary>
    [HttpGet("status")]
    [ProducesResponseType(typeof(JobsStatusResponse), StatusCodes.Status200OK)]
    public ActionResult<JobsStatusResponse> GetStatus()
    {
        var monitoring = JobStorage.Current.GetMonitoringApi();

        var stats = monitoring.GetStatistics();

        var recurringJobs = JobStorage.Current
            .GetConnection()
            .GetRecurringJobs()
            .Select(j => new RecurringJobInfo
            {
                Id = j.Id,
                Cron = j.Cron,
                NextExecution = j.NextExecution,
                LastExecution = j.LastExecution,
                LastJobState = j.LastJobState,
                LastJobId = j.LastJobId,
                Queue = j.Queue,
                Error = j.Error
            })
            .ToList();

        var recentJobs = monitoring
            .SucceededJobs(0, 10)
            .Select(j => new RecentJobInfo
            {
                JobId = j.Key,
                State = "Succeeded",
                SucceededAt = j.Value.SucceededAt
            })
            .ToList();

        return Ok(new JobsStatusResponse
        {
            Queued = stats.Enqueued,
            Scheduled = stats.Scheduled,
            Processing = stats.Processing,
            Succeeded = stats.Succeeded,
            Failed = stats.Failed,
            RecurringJobs = recurringJobs,
            RecentSucceeded = recentJobs
        });
    }

    /// <summary>
    /// Manually trigger the advisory ingestion job now (enqueues immediately).
    /// </summary>
    [HttpPost("advisory-ingestion/trigger")]
    [ProducesResponseType(typeof(TriggerJobResponse), StatusCodes.Status200OK)]
    public ActionResult<TriggerJobResponse> TriggerAdvisoryIngestion()
    {
        _logger.LogInformation("Manual trigger requested for advisory-ingestion job");

        var jobId = BackgroundJob.Enqueue<RagSystem.ApiGateway.Jobs.AdvisoryIngestionJob>(
            job => job.ExecuteAsync());

        _logger.LogInformation("Enqueued advisory-ingestion job with ID: {JobId}", jobId);

        return Ok(new TriggerJobResponse
        {
            JobId = jobId,
            Message = "Advisory ingestion job enqueued successfully",
            TriggeredAt = DateTime.UtcNow
        });
    }

    /// <summary>
    /// Get the result/state of a specific job by its ID.
    /// </summary>
    [HttpGet("{jobId}")]
    [ProducesResponseType(typeof(JobDetailResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public ActionResult<JobDetailResponse> GetJob(string jobId)
    {
        var monitoring = JobStorage.Current.GetMonitoringApi();

        var job = monitoring.JobDetails(jobId);
        if (job == null)
            return NotFound(new { message = $"Job '{jobId}' not found" });

        return Ok(new JobDetailResponse
        {
            JobId = jobId,
            CreatedAt = job.CreatedAt,
            CurrentState = job.History.FirstOrDefault()?.StateName ?? "Unknown",
            History = job.History.Select(h => new JobHistoryEntry
            {
                State = h.StateName,
                Reason = h.Reason,
                CreatedAt = h.CreatedAt
            }).ToList()
        });
    }
}

public class JobsStatusResponse
{
    public long Queued { get; set; }
    public long Scheduled { get; set; }
    public long Processing { get; set; }
    public long Succeeded { get; set; }
    public long Failed { get; set; }
    public List<RecurringJobInfo> RecurringJobs { get; set; } = new();
    public List<RecentJobInfo> RecentSucceeded { get; set; } = new();
}

public class RecurringJobInfo
{
    public string Id { get; set; } = string.Empty;
    public string? Cron { get; set; }
    public DateTime? NextExecution { get; set; }
    public DateTime? LastExecution { get; set; }
    public string? LastJobState { get; set; }
    public string? LastJobId { get; set; }
    public string? Queue { get; set; }
    public string? Error { get; set; }
}

public class RecentJobInfo
{
    public string JobId { get; set; } = string.Empty;
    public string State { get; set; } = string.Empty;
    public DateTime? SucceededAt { get; set; }
}

public class TriggerJobResponse
{
    public string JobId { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
    public DateTime TriggeredAt { get; set; }
}

public class JobDetailResponse
{
    public string JobId { get; set; } = string.Empty;
    public DateTime? CreatedAt { get; set; }
    public string CurrentState { get; set; } = string.Empty;
    public List<JobHistoryEntry> History { get; set; } = new();
}

public class JobHistoryEntry
{
    public string State { get; set; } = string.Empty;
    public string? Reason { get; set; }
    public DateTime CreatedAt { get; set; }
}
