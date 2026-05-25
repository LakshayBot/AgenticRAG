from fastapi import APIRouter
from sqlalchemy import text

from ..dependencies import DatabaseDep, OpenSearchDep, SessionDep, SettingsDep
from ..repositories.uploaded_paper import UploadedPaperRepository
from ..schemas.api.health import HealthResponse, ServiceStatus
from ..services.ollama import OllamaClient

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(
    settings: SettingsDep, 
    database: DatabaseDep, 
    opensearch_client: OpenSearchDep,
    session: SessionDep
) -> HealthResponse:
    """Comprehensive health check endpoint for monitoring and load balancer probes.

    :returns: Service health status with version and connectivity checks
    :rtype: HealthResponse
    """
    services = {}
    overall_status = "ok"

    def _check_service(name: str, check_func, *args, **kwargs):
        """Helper to standardize service health checks."""
        try:
            if kwargs.get("is_async"):
                # Handle async functions separately in the calling code
                return check_func(*args)
            result = check_func(*args)
            services[name] = result
            if result.status != "healthy":
                nonlocal overall_status
                overall_status = "degraded"
        except Exception as e:
            services[name] = ServiceStatus(status="unhealthy", message=str(e))
            overall_status = "degraded"

    # Database check
    def _check_database():
        with database.get_session() as session:
            session.execute(text("SELECT 1"))
        return ServiceStatus(status="healthy", message="Connected successfully")

    # OpenSearch check
    def _check_opensearch():
        if not opensearch_client.health_check():
            return ServiceStatus(status="unhealthy", message="Not responding")
        stats = opensearch_client.get_index_stats()
        return ServiceStatus(
            status="healthy",
            message=f"Index '{stats.get('index_name', 'unknown')}' with {stats.get('document_count', 0)} documents",
        )
    
    # Upload statistics check
    def _check_uploads():
        try:
            repository = UploadedPaperRepository(session)
            stats = repository.get_processing_stats()
            message = (
                f"Uploads: {stats['total_uploads']} total, "
                f"{stats['completed']} completed, "
                f"{stats['pending']} pending, "
                f"{stats['failed']} failed "
                f"({stats['total_size_mb']}MB used)"
            )
            return ServiceStatus(status="healthy", message=message)
        except Exception as e:
            return ServiceStatus(status="degraded", message=f"Error getting stats: {str(e)}")

    # Run synchronous checks
    _check_service("database", _check_database)
    _check_service("opensearch", _check_opensearch)
    _check_service("uploads", _check_uploads)

    # Handle Ollama async check separately
    try:
        ollama_client = OllamaClient(settings)
        ollama_health = await ollama_client.health_check()
        services["ollama"] = ServiceStatus(status=ollama_health["status"], message=ollama_health["message"])
        if ollama_health["status"] != "healthy":
            overall_status = "degraded"
    except Exception as e:
        services["ollama"] = ServiceStatus(status="unhealthy", message=str(e))
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        service_name=settings.service_name,
        services=services,
    )
