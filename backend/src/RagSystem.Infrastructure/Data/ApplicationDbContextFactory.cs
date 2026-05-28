using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace RagSystem.Infrastructure.Data;

/// <summary>
/// Design-time factory for ApplicationDbContext to enable EF Core migrations
/// </summary>
public class ApplicationDbContextFactory : IDesignTimeDbContextFactory<ApplicationDbContext>
{
    public ApplicationDbContext CreateDbContext(string[] args)
    {
        var optionsBuilder = new DbContextOptionsBuilder<ApplicationDbContext>();
        
        // Use a connection string for design-time only
        // The actual connection string is loaded from appsettings.json at runtime
        var connectionString = "Host=localhost;Port=5432;Database=rag_system;Username=postgres;Password=postgres";
        
        // Configure Npgsql data source with dynamic JSON support
        var dataSourceBuilder = new Npgsql.NpgsqlDataSourceBuilder(connectionString);
        dataSourceBuilder.EnableDynamicJson();
        var dataSource = dataSourceBuilder.Build();
        
        optionsBuilder.UseNpgsql(dataSource, npgsqlOptions =>
        {
            npgsqlOptions.MigrationsHistoryTable("__EFMigrationsHistory", "dotnet_app");
        });
        
        return new ApplicationDbContext(optionsBuilder.Options);
    }
}
