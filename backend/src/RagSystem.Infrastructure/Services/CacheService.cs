using System.Text.Json;
using Microsoft.Extensions.Configuration;
using RagSystem.Core.Interfaces;
using StackExchange.Redis;

namespace RagSystem.Infrastructure.Services;

public class CacheService : ICacheService
{
    private readonly IDatabase _redis;
    private readonly IConfiguration _configuration;
    private readonly string _instanceName;

    public CacheService(IConnectionMultiplexer redis, IConfiguration configuration)
    {
        _redis = redis.GetDatabase();
        _configuration = configuration;
        _instanceName = _configuration["Redis:InstanceName"] ?? "RagSystem:";
    }

    public async Task<T?> GetAsync<T>(string key) where T : class
    {
        var prefixedKey = GetPrefixedKey(key);
        var value = await _redis.StringGetAsync(prefixedKey);

        if (value.IsNullOrEmpty)
            return null;

        return JsonSerializer.Deserialize<T>(value!);
    }

    public async Task SetAsync<T>(string key, T value, TimeSpan? expiration = null) where T : class
    {
        var prefixedKey = GetPrefixedKey(key);
        var serialized = JsonSerializer.Serialize(value);

        if (expiration.HasValue)
        {
            await _redis.StringSetAsync(prefixedKey, serialized, expiration.Value);
        }
        else
        {
            await _redis.StringSetAsync(prefixedKey, serialized);
        }
    }

    public async Task RemoveAsync(string key)
    {
        var prefixedKey = GetPrefixedKey(key);
        await _redis.KeyDeleteAsync(prefixedKey);
    }

    public async Task<bool> ExistsAsync(string key)
    {
        var prefixedKey = GetPrefixedKey(key);
        return await _redis.KeyExistsAsync(prefixedKey);
    }

    public async Task RemoveByPatternAsync(string pattern)
    {
        // Note: This requires RedisValue support for pattern matching
        // In production, consider using a more efficient approach
        var prefixedPattern = GetPrefixedKey(pattern);
        var server = _redis.Multiplexer.GetServer(_redis.Multiplexer.GetEndPoints().First());
        var keys = server.Keys(pattern: prefixedPattern).ToArray();
        
        if (keys.Length > 0)
        {
            await _redis.KeyDeleteAsync(keys);
        }
    }

    private string GetPrefixedKey(string key)
    {
        return $"{_instanceName}{key}";
    }
}
