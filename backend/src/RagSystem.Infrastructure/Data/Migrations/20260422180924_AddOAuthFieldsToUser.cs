using System;
using System.Collections.Generic;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace RagSystem.Infrastructure.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddOAuthFieldsToUser : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "papers",
                schema: "dotnet_app");

            migrationBuilder.AddColumn<string>(
                name: "AvatarUrl",
                schema: "dotnet_app",
                table: "users",
                type: "character varying(500)",
                maxLength: 500,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "Provider",
                schema: "dotnet_app",
                table: "users",
                type: "character varying(50)",
                maxLength: 50,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "ProviderId",
                schema: "dotnet_app",
                table: "users",
                type: "character varying(255)",
                maxLength: 255,
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "AvatarUrl",
                schema: "dotnet_app",
                table: "users");

            migrationBuilder.DropColumn(
                name: "Provider",
                schema: "dotnet_app",
                table: "users");

            migrationBuilder.DropColumn(
                name: "ProviderId",
                schema: "dotnet_app",
                table: "users");

            migrationBuilder.CreateTable(
                name: "papers",
                schema: "dotnet_app",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    Abstract = table.Column<string>(type: "text", nullable: true),
                    ArxivId = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    Authors = table.Column<string[]>(type: "text[]", nullable: true),
                    Category = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "CURRENT_TIMESTAMP"),
                    Indexed = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    IndexedDate = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    Metadata = table.Column<Dictionary<string, object>>(type: "jsonb", nullable: true),
                    PdfProcessed = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    PdfProcessingDate = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    PdfUrl = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    PublishedDate = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    RawText = table.Column<string>(type: "text", nullable: true),
                    Title = table.Column<string>(type: "text", nullable: false),
                    UpdatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_papers", x => x.Id);
                });

            migrationBuilder.CreateIndex(
                name: "IX_papers_ArxivId",
                schema: "dotnet_app",
                table: "papers",
                column: "ArxivId",
                unique: true);
        }
    }
}
