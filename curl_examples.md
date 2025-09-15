# Curl Examples for /detect-error API Testing

## Prerequisites
- API server running on `http://localhost:8000`
- `jq` installed for JSON formatting (optional but recommended)

## Basic Test - First Attempt

```bash
curl -X POST "http://localhost:8000/detect-error" \
  -H "Content-Type: application/json" \
  -d '{
    "socket_id": "test_user_123_session_456",
    "question_url": "mock-data/Q1.jpeg",
    "solution_url": "mock-data/Attempt1.jpeg",
    "bounding_box": {
      "minX": 100,
      "maxX": 300,
      "minY": 100,
      "maxY": 200
    },
    "user_id": "test_user_123",
    "question_attempt_id": "attempt_1"
  }' | jq '.'
```

## Second Attempt - Same Session, Different Bounding Box

```bash
curl -X POST "http://localhost:8000/detect-error" \
  -H "Content-Type: application/json" \
  -d '{
    "socket_id": "test_user_123_session_456",
    "question_url": "mock-data/Q2.jpeg",
    "solution_url": "mock-data/Attempt2.jpeg",
    "bounding_box": {
      "minX": 150,
      "maxX": 350,
      "minY": 150,
      "maxY": 250
    },
    "user_id": "test_user_123",
    "question_attempt_id": "attempt_2"
  }' | jq '.'
```
