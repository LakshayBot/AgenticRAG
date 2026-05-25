using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;
using RagSystem.Core.Interfaces;
using RagSystem.Infrastructure.Data;
using RagSystem.Infrastructure.Services;
using RagSystem.Infrastructure.Services.PythonClients;
using StackExchange.Redis;
using System.IdentityModel.Tokens.Jwt;
using System.Text;
using Hangfire;
using Hangfire.PostgreSql;

// Clear default claim mapping to preserve JWT claim names (sub, email, etc.)
JwtSecurityTokenHandler.DefaultInboundClaimTypeMap.Clear();

var builder = WebApplication.CreateBuilder(args);

// Configure Kestrel to listen on port 8000
builder.WebHost.ConfigureKestrel(options =>
{
    options.ListenAnyIP(8000);
});

// Add services to the container
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();

// Swagger configuration with JWT
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo
    {
        Title = "RAG System API",
        Version = "v1",
        Description = ".NET API Gateway for Agentic RAG System"
    });

    c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {
        Description = "JWT Authorization header using the Bearer scheme. Example: \"Bearer {token}\"",
        Name = "Authorization",
        In = ParameterLocation.Header,
        Type = SecuritySchemeType.ApiKey,
        Scheme = "Bearer"
    });

    c.AddSecurityRequirement(new OpenApiSecurityRequirement
    {
        {
            new OpenApiSecurityScheme
            {
                Reference = new OpenApiReference
                {
                    Type = ReferenceType.SecurityScheme,
                    Id = "Bearer"
                }
            },
            Array.Empty<string>()
        }
    });
});

// Database configuration
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");

// Configure Npgsql data source with dynamic JSON support
var dataSourceBuilder = new Npgsql.NpgsqlDataSourceBuilder(connectionString);
dataSourceBuilder.EnableDynamicJson();
var dataSource = dataSourceBuilder.Build();

builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseNpgsql(dataSource, npgsqlOptions =>
    {
        npgsqlOptions.MigrationsHistoryTable("__EFMigrationsHistory", "dotnet_app");
    }));

// Redis configuration
var redisConnection = builder.Configuration.GetConnectionString("Redis") ?? "localhost:6379";
var redisOptions = ConfigurationOptions.Parse(redisConnection);
redisOptions.AbortOnConnectFail = false;
builder.Services.AddSingleton<IConnectionMultiplexer>(
    ConnectionMultiplexer.Connect(redisOptions));

// JWT Authentication
var jwtSettings = builder.Configuration.GetSection("JwtSettings");
var secretKey = jwtSettings["SecretKey"] 
    ?? throw new InvalidOperationException("JWT SecretKey is not configured");

builder.Services.AddAuthentication(options =>
{
    options.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme;
    options.DefaultChallengeScheme = JwtBearerDefaults.AuthenticationScheme;
})
.AddJwtBearer(options =>
{
    options.MapInboundClaims = false; // Preserve original claim names (sub, email, role)
    options.TokenValidationParameters = new TokenValidationParameters
    {
        ValidateIssuer = true,
        ValidateAudience = true,
        ValidateLifetime = true,
        ValidateIssuerSigningKey = true,
        ValidIssuer = jwtSettings["Issuer"],
        ValidAudience = jwtSettings["Audience"],
        IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secretKey)),
        ClockSkew = TimeSpan.Zero,
        // Tell ASP.NET Core to look for "role" claim for authorization
        RoleClaimType = "role"
    };
});

builder.Services.AddAuthorization(options =>
{
    options.AddPolicy("AdminOnly", policy => policy.RequireRole("admin"));
});

// HTTP Client configurations for Python services
builder.Services.AddHttpClient<IPdfServiceClient, PdfServiceClient>(client =>
{
    var baseUrl = builder.Configuration["PythonServices:PdfService:BaseUrl"] ?? "http://localhost:8001";
    client.BaseAddress = new Uri(baseUrl);
    client.Timeout = TimeSpan.FromMinutes(5);
});

builder.Services.AddHttpClient<IEmbeddingsServiceClient, EmbeddingsServiceClient>(client =>
{
    var baseUrl = builder.Configuration["PythonServices:EmbeddingsService:BaseUrl"] ?? "http://localhost:8002";
    client.BaseAddress = new Uri(baseUrl);
    client.Timeout = TimeSpan.FromMinutes(2);
});

builder.Services.AddHttpClient<ISearchServiceClient, SearchServiceClient>(client =>
{
    var baseUrl = builder.Configuration["PythonServices:SearchService:BaseUrl"] ?? "http://localhost:8003";
    client.BaseAddress = new Uri(baseUrl);
    client.Timeout = TimeSpan.FromSeconds(30);
});

builder.Services.AddHttpClient<IAgenticRAGServiceClient, AgenticRAGServiceClient>(client =>
{
    var baseUrl = builder.Configuration["PythonServices:AgenticRAGService:BaseUrl"] ?? "http://localhost:8004";
    client.BaseAddress = new Uri(baseUrl);
    client.Timeout = TimeSpan.FromMinutes(5); // Increased for agentic workflow with multiple LLM calls
});

builder.Services.AddHttpClient<IAdvisoryServiceClient, AdvisoryServiceClient>(client =>
{
    var baseUrl = builder.Configuration["PythonServices:AdvisoryService:BaseUrl"] ?? "http://localhost:8001";
    client.BaseAddress = new Uri(baseUrl);
    client.Timeout = TimeSpan.FromMinutes(30); // Reindex of 486 advisories can take ~15-20 min
});

// Register application services
builder.Services.AddScoped<ICacheService, CacheService>();
builder.Services.AddScoped<IAuthService, AuthService>();
builder.Services.AddScoped<ISearchService, SearchService>();
builder.Services.AddScoped<IRAGService, RAGService>();
builder.Services.AddScoped<IUploadService, UploadService>();
builder.Services.AddScoped<IAdminService, AdminService>();

// Register repositories
builder.Services.AddScoped<IAdvisoryRepository, RagSystem.Infrastructure.Repositories.AdvisoryRepository>();

// Register background jobs
builder.Services.AddScoped<RagSystem.ApiGateway.Jobs.AdvisoryIngestionJob>();

// Hangfire Configuration
builder.Services.AddHangfire(config => config
    .SetDataCompatibilityLevel(CompatibilityLevel.Version_180)
    .UseSimpleAssemblyNameTypeSerializer()
    .UseRecommendedSerializerSettings()
    .UsePostgreSqlStorage(
        c => c.UseNpgsqlConnection(connectionString),
        new PostgreSqlStorageOptions
        {
            PrepareSchemaIfNecessary = true,
            StartupConnectionMaxRetries = 10,
            StartupConnectionBaseDelay = TimeSpan.FromSeconds(1),
            StartupConnectionMaxDelay = TimeSpan.FromSeconds(10)
        }));

builder.Services.AddHangfireServer();

// CORS configuration
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

// Logging
builder.Services.AddLogging(logging =>
{
    logging.AddConsole();
    logging.AddDebug();
});

var app = builder.Build();

// Apply migrations before the API and Hangfire server begin accepting work.
await ApplyDatabaseMigrationsAsync(app);

// Configure the HTTP request pipeline
app.UseSwagger();
app.UseSwaggerUI(c =>
{
    c.SwaggerEndpoint("/swagger/v1/swagger.json", "RAG System API v1");
    c.RoutePrefix = "swagger";
});

app.UseCors("AllowAll");

// Hangfire Dashboard - placed before auth middleware so ASP.NET auth doesn't intercept it
app.UseHangfireDashboard("/hangfire", new DashboardOptions
{
    Authorization = new[] { new RagSystem.ApiGateway.Security.HangfireAuthorizationFilter() }
});

// Schedule recurring job (runs daily at 6 AM UTC)
RecurringJob.AddOrUpdate<RagSystem.ApiGateway.Jobs.AdvisoryIngestionJob>(
    "advisory-ingestion",
    job => job.ExecuteAsync(),
    Cron.Daily(6), // 6 AM UTC
    new RecurringJobOptions
    {
        TimeZone = TimeZoneInfo.Utc
    });

app.UseAuthentication();
app.UseAuthorization();

app.MapControllers();

// Health check endpoint
app.MapGet("/health", async (ApplicationDbContext context, IConnectionMultiplexer redis) =>
{
    var databaseHealthy = await context.Database.CanConnectAsync();
    if (!databaseHealthy)
    {
        return Results.Problem("Database is not reachable", statusCode: StatusCodes.Status503ServiceUnavailable);
    }

    if (!redis.IsConnected)
    {
        return Results.Problem("Redis is not connected", statusCode: StatusCodes.Status503ServiceUnavailable);
    }

    return Results.Ok(new
    {
        status = "healthy",
        timestamp = DateTime.UtcNow,
        version = "1.0.0"
    });
});

app.Logger.LogInformation("RAG System API Gateway starting on port 8000");

app.Run();

static async Task ApplyDatabaseMigrationsAsync(WebApplication app)
{
    var maxAttempts = app.Configuration.GetValue("Database:MigrationMaxAttempts", 12);
    var delaySeconds = app.Configuration.GetValue("Database:MigrationRetryDelaySeconds", 5);

    for (var attempt = 1; attempt <= maxAttempts; attempt++)
    {
        try
        {
            using var scope = app.Services.CreateScope();
            var context = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
            await context.Database.MigrateAsync();
            app.Logger.LogInformation("Database migrations applied successfully");
            return;
        }
        catch (Exception ex) when (attempt < maxAttempts)
        {
            app.Logger.LogWarning(
                ex,
                "Database migration attempt {Attempt}/{MaxAttempts} failed. Retrying in {DelaySeconds} seconds",
                attempt,
                maxAttempts,
                delaySeconds);
            await Task.Delay(TimeSpan.FromSeconds(delaySeconds));
        }
        catch (Exception ex)
        {
            app.Logger.LogCritical(
                ex,
                "Database migrations failed after {MaxAttempts} attempts. Stopping startup",
                maxAttempts);
            throw;
        }
    }
}
