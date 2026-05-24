# RagSystem .NET Backend

This is the .NET backend implementation for the RAG System, providing enterprise-grade API orchestration, authentication, and service management.

## Architecture

- **RagSystem.ApiGateway**: Main API Gateway with orchestration, authentication, and routing
- **RagSystem.Core**: Domain entities, DTOs, and interfaces
- **RagSystem.Infrastructure**: Data access, repositories, and external service clients
- **RagSystem.FileService**: File upload and management service

## Prerequisites

- .NET 8.0 SDK
- Docker & Docker Compose
- PostgreSQL (via Docker)
- Redis (via Docker)

## Getting Started

### 1. Restore Dependencies
```bash
cd backend
dotnet restore
```

### 2. Build Solution
```bash
dotnet build
```

### 3. Run Database Migrations
```bash
cd src/RagSystem.ApiGateway
dotnet ef database update
```

### 4. Run the API Gateway
```bash
cd src/RagSystem.ApiGateway
dotnet run
```

The API will be available at:
- HTTP: http://localhost:5000
- HTTPS: https://localhost:5001
- Swagger: http://localhost:5000/swagger

### 5. Run with Docker Compose
```bash
cd backend
docker-compose up --build
```

## Project Structure

```
backend/
├── src/
│   ├── RagSystem.ApiGateway/      # Main API Gateway
│   │   ├── Controllers/           # API endpoints
│   │   ├── Services/              # Business logic
│   │   ├── Middleware/            # Custom middleware
│   │   └── Program.cs             # Application entry point
│   ├── RagSystem.Core/            # Domain layer
│   │   ├── Entities/              # Database entities
│   │   ├── DTOs/                  # Data transfer objects
│   │   └── Interfaces/            # Service interfaces
│   ├── RagSystem.Infrastructure/  # Data & external services
│   │   ├── Data/                  # DbContext & migrations
│   │   ├── Repositories/          # Data access
│   │   └── Services/              # External HTTP clients
│   └── RagSystem.FileService/     # File management service
└── RagSystem.sln                  # Solution file
```

## Key Features

### Authentication & Authorization
- JWT-based authentication
- Role-based access control (RBAC)
- Refresh token support

### API Orchestration
- Centralized routing to Python microservices
- Request/response transformation
- Error handling and logging

### Caching
- Distributed caching with Redis
- Cache-aside pattern
- Configurable TTL

### Rate Limiting
- IP-based rate limiting
- Per-user rate limiting
- Configurable limits per endpoint

### Monitoring
- Structured logging with Serilog
- Request/response logging
- Performance metrics

## Configuration

Configuration is managed through `appsettings.json` and environment variables.

### Key Settings

```json
{
  "ConnectionStrings": {
    "DefaultConnection": "Host=localhost;Database=rag_db;Username=rag_user;Password=rag_password"
  },
  "JwtSettings": {
    "SecretKey": "your-secret-key-min-32-chars",
    "Issuer": "RagSystem",
    "Audience": "RagSystemUsers",
    "ExpirationMinutes": 1440
  },
  "PythonServices": {
    "PdfService": "http://localhost:8001",
    "EmbeddingsService": "http://localhost:8002",
    "AgenticRagService": "http://localhost:8003",
    "SearchService": "http://localhost:8004",
    "ArxivService": "http://localhost:8005"
  },
  "Redis": {
    "Host": "localhost",
    "Port": 6379,
    "InstanceName": "RagSystem:"
  }
}
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout user

### Search
- `POST /api/v1/search/hybrid` - Hybrid search (BM25 + vector)
- `POST /api/v1/search/bm25` - BM25 keyword search
- `POST /api/v1/search/vector` - Vector semantic search

### RAG (Question Answering)
- `POST /api/v1/rag/ask` - Ask question with RAG
- `POST /api/v1/rag/ask-agentic` - Agentic RAG with reasoning
- `GET /api/v1/rag/ask-stream` - Streaming responses

### Upload
- `POST /api/v1/upload` - Upload PDF file
- `GET /api/v1/upload/{id}/status` - Check upload status
- `GET /api/v1/upload` - List all uploads
- `DELETE /api/v1/upload/{id}` - Delete uploaded file

### Admin
- `GET /api/v1/admin/stats` - System statistics
- `GET /api/v1/admin/users` - List users
- `POST /api/v1/admin/users/{id}/disable` - Disable user
- `GET /api/v1/admin/health` - Comprehensive health check

## Development

### Adding a New Controller

1. Create controller in `RagSystem.ApiGateway/Controllers/`
2. Add service interface in `RagSystem.Core/Interfaces/`
3. Implement service in `RagSystem.Infrastructure/Services/`
4. Register service in `Program.cs`

### Adding Database Migrations

```bash
cd src/RagSystem.ApiGateway
dotnet ef migrations add MigrationName
dotnet ef database update
```

## Testing

Run tests:
```bash
dotnet test
```

## Deployment

### Docker Deployment
```bash
docker build -t ragsystem-api:latest -f src/RagSystem.ApiGateway/Dockerfile .
docker run -p 5000:5000 ragsystem-api:latest
```

### Azure Deployment
See deployment guide in `docs/azure-deployment.md`

## Environment Variables

- `ASPNETCORE_ENVIRONMENT` - Environment (Development/Production)
- `ConnectionStrings__DefaultConnection` - PostgreSQL connection string
- `JwtSettings__SecretKey` - JWT signing key
- `Redis__Host` - Redis host
- `PythonServices__*` - Python service URLs

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running
- Check connection string in appsettings.json
- Run migrations: `dotnet ef database update`

### Python Service Connection Issues
- Verify Python services are running
- Check Python service URLs in configuration
- Test endpoints: `curl http://localhost:8001/health`

### Redis Connection Issues
- Ensure Redis is running
- Check Redis host and port configuration
- Test connection: `redis-cli ping`

## License

See LICENSE file in root directory.
