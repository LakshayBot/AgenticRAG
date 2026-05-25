using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using RagSystem.Core.DTOs.Search;
using RagSystem.Core.Interfaces;

namespace RagSystem.ApiGateway.Controllers;

[Authorize]
[ApiController]
[Route("api/[controller]")]
public class SearchController : ControllerBase
{
    private readonly ISearchService _searchService;
    private readonly ILogger<SearchController> _logger;

    public SearchController(ISearchService searchService, ILogger<SearchController> logger)
    {
        _searchService = searchService;
        _logger = logger;
    }

    /// <summary>
    /// Perform hybrid search (BM25 + Vector)
    /// </summary>
    [HttpPost("hybrid")]
    [ProducesResponseType(typeof(SearchResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<SearchResponse>> HybridSearch([FromBody] SearchRequest request)
    {
        try
        {
            var response = await _searchService.HybridSearchAsync(request);
            return Ok(response);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error performing hybrid search");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    /// <summary>
    /// Perform BM25 keyword search
    /// </summary>
    [HttpPost("bm25")]
    [ProducesResponseType(typeof(SearchResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<SearchResponse>> BM25Search([FromBody] SearchRequest request)
    {
        try
        {
            var response = await _searchService.BM25SearchAsync(request);
            return Ok(response);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error performing BM25 search");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    /// <summary>
    /// Perform vector similarity search
    /// </summary>
    [HttpPost("vector")]
    [ProducesResponseType(typeof(SearchResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<SearchResponse>> VectorSearch([FromBody] SearchRequest request)
    {
        try
        {
            var response = await _searchService.VectorSearchAsync(request);
            return Ok(response);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error performing vector search");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }
}
