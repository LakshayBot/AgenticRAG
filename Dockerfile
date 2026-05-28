# =============================================================================
# CyberGuard AI — .NET 8 API Gateway
#
# Multi-stage build.
# Build context: repo root (docker-compose sets context: .)
# Solution:       backend/RagSystem.sln
# Entry project:  backend/src/RagSystem.ApiGateway
# =============================================================================

# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build

ARG CONFIGURATION=Release
ARG ENVIRONMENT=Production

WORKDIR /repo

# Copy solution + project files first (layer-cache NuGet restore)
COPY backend/RagSystem.sln                                        ./backend/
COPY backend/src/RagSystem.ApiGateway/RagSystem.ApiGateway.csproj ./backend/src/RagSystem.ApiGateway/
COPY backend/src/RagSystem.Core/RagSystem.Core.csproj             ./backend/src/RagSystem.Core/
COPY backend/src/RagSystem.Infrastructure/RagSystem.Infrastructure.csproj ./backend/src/RagSystem.Infrastructure/

RUN dotnet restore backend/RagSystem.sln --verbosity minimal

# Copy the full backend source and publish
COPY backend/ ./backend/

RUN dotnet publish backend/src/RagSystem.ApiGateway/RagSystem.ApiGateway.csproj \
    -c "$CONFIGURATION" \
    -o /app/publish \
    --verbosity normal

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime

ARG ENVIRONMENT=Production
ENV ASPNETCORE_ENVIRONMENT=${ENVIRONMENT}
ENV ASPNETCORE_URLS=http://+:8000
ENV DOTNET_RUNNING_IN_CONTAINER=true

# curl is needed for the Docker healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=build /app/publish ./

# Directory for user-uploaded files (mounted as a volume in docker-compose)
RUN mkdir -p /app/uploads

EXPOSE 8000

ENTRYPOINT ["dotnet", "RagSystem.ApiGateway.dll"]
