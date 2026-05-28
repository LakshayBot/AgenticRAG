using System;
using System.Collections.Generic;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace RagSystem.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddAdvisoryEntity : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "advisories",
                schema: "dotnet_app",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    GhsaId = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    CveId = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    Summary = table.Column<string>(type: "text", nullable: false),
                    Description = table.Column<string>(type: "text", nullable: true),
                    Severity = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    CvssScore = table.Column<decimal>(type: "numeric", nullable: true),
                    Type = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    AffectedEcosystems = table.Column<string[]>(type: "text[]", nullable: true),
                    AffectedPackages = table.Column<string[]>(type: "text[]", nullable: true),
                    Vulnerabilities = table.Column<Dictionary<string, object>>(type: "jsonb", nullable: true),
                    CweIds = table.Column<string[]>(type: "text[]", nullable: true),
                    Cwes = table.Column<Dictionary<string, object>>(type: "jsonb", nullable: true),
                    ReferenceUrls = table.Column<string[]>(type: "text[]", nullable: true),
                    GithubUrl = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    PublishedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    UpdatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    WithdrawnAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    Indexed = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    IndexedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "CURRENT_TIMESTAMP"),
                    ModifiedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_advisories", x => x.Id);
                });

            migrationBuilder.CreateIndex(
                name: "IX_advisories_CveId",
                schema: "dotnet_app",
                table: "advisories",
                column: "CveId");

            migrationBuilder.CreateIndex(
                name: "IX_advisories_GhsaId",
                schema: "dotnet_app",
                table: "advisories",
                column: "GhsaId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_advisories_PublishedAt",
                schema: "dotnet_app",
                table: "advisories",
                column: "PublishedAt");

            migrationBuilder.CreateIndex(
                name: "IX_advisories_Severity",
                schema: "dotnet_app",
                table: "advisories",
                column: "Severity");

            migrationBuilder.CreateIndex(
                name: "IX_advisories_UpdatedAt",
                schema: "dotnet_app",
                table: "advisories",
                column: "UpdatedAt");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "advisories",
                schema: "dotnet_app");
        }
    }
}
