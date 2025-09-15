# Caching Strategy Update for Cumulative Bounding Box Tracking

## Problem Identified

The original `generate_request_cache_key` function was missing the `socket_id` field, which is critical for cumulative bounding box tracking because:

1. **Session-specific data**: Different sessions should have different cache entries
2. **Cumulative state changes**: The API response changes based on cumulative bounding box data stored per session
3. **Cache invalidation**: Each session maintains its own cumulative state that affects the response

## Solution Implemented

### Updated Cache Key Generation

The `generate_request_cache_key` function now includes the `socket_id`:

```python
def generate_request_cache_key(*args, **kwargs) -> str:
    """Generate a cache key based on request data for math evaluation."""
    # ... extract request logic ...
    
    key_data = {
        'socket_id': request.socket_id,  # Critical for session-specific cumulative data
        'question_url': request.question_url,
        'solution_url': request.solution_url,
        'bounding_box': request.bounding_box,
        'user_id': request.user_id,
        'question_attempt_id': request.question_attempt_id
    }
    
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_string.encode()).hexdigest()
```

### Why This Change is Necessary

#### Before the Update:
```python
# Same question, different sessions - WRONG CACHE BEHAVIOR
Request 1: socket_id="user1_session1", question_url="q1.jpg", bounding_box={...}
Request 2: socket_id="user2_session2", question_url="q1.jpg", bounding_box={...}

# Both would generate the SAME cache key (missing socket_id)
# This would cause user2 to get user1's cumulative bounding box data!
```

#### After the Update:
```python
# Same question, different sessions - CORRECT CACHE BEHAVIOR
Request 1: socket_id="user1_session1", question_url="q1.jpg", bounding_box={...}
Request 2: socket_id="user2_session2", question_url="q1.jpg", bounding_box={...}

# Now generates DIFFERENT cache keys (includes socket_id)
# Each session gets its own cached response with correct cumulative data
```

## Caching Behavior Examples

### Scenario 1: Same Session, Multiple Attempts
```python
# Attempt 1
Request: {
    "socket_id": "user123_session456",
    "question_url": "https://example.com/q1.jpg",
    "solution_url": "https://example.com/answer1.jpg",
    "bounding_box": {"minX": 100, "maxX": 300, "minY": 100, "maxY": 200}
}
Cache Key: md5({"socket_id": "user123_session456", "question_url": "...", ...})
Response: { "total_attempts": 1, "cumulative_bounding_box": {...} }

# Attempt 2 (same session, same question, different bounding box)
Request: {
    "socket_id": "user123_session456",  # Same session
    "question_url": "https://example.com/q1.jpg",  # Same question
    "solution_url": "https://example.com/answer2.jpg",  # Different solution
    "bounding_box": {"minX": 150, "maxX": 350, "minY": 150, "maxY": 250}  # Different box
}
Cache Key: md5({"socket_id": "user123_session456", "question_url": "...", "bounding_box": {...}})
Response: { "total_attempts": 2, "cumulative_bounding_box": {...} }  # Different response
```

### Scenario 2: Different Sessions, Same Question
```python
# User 1, Session 1
Request: {
    "socket_id": "user1_session1",
    "question_url": "https://example.com/q1.jpg",
    "bounding_box": {"minX": 100, "maxX": 300, "minY": 100, "maxY": 200}
}
Cache Key: md5({"socket_id": "user1_session1", ...})

# User 2, Session 2 (same question, different session)
Request: {
    "socket_id": "user2_session2",  # Different session
    "question_url": "https://example.com/q1.jpg",  # Same question
    "bounding_box": {"minX": 200, "maxX": 400, "minY": 200, "maxY": 300}
}
Cache Key: md5({"socket_id": "user2_session2", ...})  # Different cache key
```

## Cache Key Components

The cache key now includes all relevant fields:

1. **`socket_id`**: Ensures session isolation
2. **`question_url`**: Identifies the specific question
3. **`solution_url`**: Identifies the specific solution image
4. **`bounding_box`**: Current attempt's bounding box coordinates
5. **`user_id`**: User context (optional)
6. **`question_attempt_id`**: Attempt identifier (optional)

## Benefits of This Update

1. **Session Isolation**: Each session gets its own cached responses
2. **Cumulative Data Integrity**: Cumulative bounding box data is correctly maintained per session
3. **Performance**: Still benefits from caching for identical requests
4. **Correctness**: Prevents cross-session data contamination

## Alternative Caching Strategies Considered

### Option 1: Disable Caching for Cumulative Endpoints
```python
# Could disable caching entirely for /detect-error
# But this would hurt performance for repeated identical requests
```

### Option 2: Cache Only Non-Cumulative Data
```python
# Could cache only the workflow result, not the cumulative response
# But this adds complexity and reduces cache effectiveness
```

### Option 3: Session-Aware Caching (Chosen)
```python
# Include socket_id in cache key
# Maintains performance while ensuring correctness
# Simple and effective solution
```

## Testing the Cache Behavior

You can test the cache behavior with these scenarios:

```python
# Test 1: Same request should hit cache
response1 = await client.post("/detect-error", json=request_data)
response2 = await client.post("/detect-error", json=request_data)  # Should be cached

# Test 2: Different session should miss cache
request_data_2 = request_data.copy()
request_data_2["socket_id"] = "different_session"
response3 = await client.post("/detect-error", json=request_data_2)  # Should miss cache

# Test 3: Different bounding box should miss cache
request_data_3 = request_data.copy()
request_data_3["bounding_box"] = {"minX": 200, "maxX": 400, "minY": 200, "maxY": 300}
response4 = await client.post("/detect-error", json=request_data_3)  # Should miss cache
```

## Conclusion

The updated caching strategy ensures that:
- Each session maintains its own cumulative bounding box state
- Cache keys properly differentiate between sessions
- Performance is maintained through appropriate caching
- Data integrity is preserved across multiple attempts

This change is essential for the cumulative bounding box tracking feature to work correctly with the existing caching infrastructure.
