# Python MongoDB + Redis + Temporal Project

A modern Python application that integrates MongoDB, Redis, and Temporal for robust error detection and workflow management using Pydantic models.

## Features

- **MongoDB Integration**: Async MongoDB operations using Motor
- **Redis Integration**: Async Redis operations for caching
- **Temporal Workflows**: Robust workflow orchestration for error detection
- **Pydantic Models**: Type-safe data validation and serialization
- **FastAPI**: Modern web framework with automatic API documentation
- **Configuration Management**: Environment-based configuration using Pydantic Settings
- **Caching Layer**: Automatic Redis caching for improved performance
- **Error Detection Workflows**: Automated error detection and management

## Project Structure

```
├── main.py                      # FastAPI application with REST endpoints
├── worker.py                    # Temporal worker for running workflows
├── config/
│   ├── __init__.py
│   └── settings.py              # Configuration management
├── models/
│   ├── __init__.py
│   └── data_models.py           # Pydantic models for data validation
├── utils/
│   ├── __init__.py
│   ├── database.py              # Database connection management
│   └── temporal_client.py       # Temporal client management
├── services/
│   ├── __init__.py
│   ├── data_service.py          # Business logic layer
│   └── workflow_service.py      # Workflow management service
├── jobs/
│   ├── __init__.py
│   ├── workflows.py             # Temporal workflows
│   └── activities.py            # Temporal activities
├── tests/
│   └── __init__.py
├── requirements.txt             # Python dependencies
├── env.example                  # Environment variables template
├── example_workflow_usage.py    # Example workflow usage
└── README.md                   # This file
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the example environment file and configure your settings:

```bash
cp env.example .env
```

Edit `.env` with your MongoDB, Redis, and Temporal connection details:

```env
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=myapp

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_DB=0

# Temporal Configuration
TEMPORAL_HOST=localhost:7233
TEMPORAL_NAMESPACE=default
TEMPORAL_TASK_QUEUE=detect-error-queue

# Application Configuration
APP_NAME=MyApp
DEBUG=True
```

### 3. Start Services

Make sure MongoDB, Redis, and Temporal are running:

```bash
# Start MongoDB (if using Docker)
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Start Redis (if using Docker)
docker run -d -p 6379:6379 --name redis redis:latest

# Start Temporal Server (if using Docker)
docker run -d -p 7233:7233 --name temporal temporalio/auto-setup:latest
```

## Usage

### Running the Application

1. **Start the Temporal Worker** (in one terminal):
   ```bash
   python worker.py
   ```

2. **Start the FastAPI Application** (in another terminal):
   ```bash
   python main.py
   ```

The API will be available at `http://localhost:8000`

- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### Example Usage

```bash
python example_workflow_usage.py
```

## API Endpoints

### Health Check
- `GET /health` - Application health status

### Users
- `POST /users` - Create a new user
- `GET /users/{user_id}` - Get user by ID
- `GET /users` - Get all users (with pagination)
- `PUT /users/{user_id}` - Update user
- `DELETE /users/{user_id}` - Delete user

### Products
- `POST /products` - Create a new product
- `GET /products/{product_id}` - Get product by ID
- `GET /products` - Get all products (with optional category filter)
- `PUT /products/{product_id}` - Update product
- `DELETE /products/{product_id}` - Delete product

### Error Detection Workflows
- `POST /workflows/detect-error` - Start a new error detection workflow
- `POST /workflows/monitor-error` - Start a continuous error monitoring workflow
- `GET /workflows/{workflow_id}/result` - Get workflow result
- `GET /workflows/{workflow_id}/status` - Get workflow status
- `POST /workflows/{workflow_id}/resolve-error` - Resolve an error
- `POST /workflows/{workflow_id}/ignore-error` - Ignore an error
- `POST /workflows/{workflow_id}/stop-monitoring` - Stop monitoring workflow
- `GET /workflows` - List active workflows
- `GET /workflows/{workflow_id}/history` - Get workflow history

### Error Logs
- `GET /error-logs` - Get error logs with filters
- `GET /error-logs/{error_log_id}` - Get error log by ID
- `PUT /error-logs/{error_log_id}/status` - Update error log status
- `GET /error-logs/statistics` - Get error statistics

## Workflows

### DetectErrorWorkflow

A comprehensive workflow for detecting and managing errors:

1. **Scan Logs**: Scans specified sources for error patterns
2. **Save Errors**: Stores detected errors in MongoDB
3. **Analyze Severity**: Categorizes errors by severity level
4. **Send Notifications**: Notifies users of critical/high severity errors
5. **Update Status**: Updates error statuses based on analysis
6. **Generate Report**: Creates comprehensive error reports
7. **Wait for Resolution**: Waits for user response or auto-resolves after timeout

### ErrorMonitoringWorkflow

A long-running workflow for continuous error monitoring:

- Runs error detection every 5 minutes
- Automatically processes and notifies on new errors
- Can be stopped via signal

## Models

### Error Detection Models

```python
class ErrorDetectionInput(BaseModel):
    source: str
    error_patterns: List[str]
    severity_threshold: ErrorSeverity
    user_id: Optional[str]
    metadata: Dict[str, Any]

class ErrorDetectionResult(BaseModel):
    workflow_id: str
    errors_detected: int
    errors_resolved: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    error_logs: List[str]
```

### Error Log Model

```python
class ErrorLog(BaseModel):
    id: Optional[PyObjectId]
    error_id: str
    message: str
    stack_trace: Optional[str]
    severity: ErrorSeverity
    status: ErrorStatus
    source: str
    metadata: Dict[str, Any]
    user_id: Optional[str]
    workflow_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    resolved_at: Optional[datetime]
```

## Key Features

### Temporal Workflows
- **Reliability**: Automatic retries and failure handling
- **Durability**: Workflow state persisted in Temporal
- **Scalability**: Can handle high-volume error detection
- **Observability**: Full workflow history and status tracking

### Caching Strategy
- **Automatic Caching**: All read operations are cached in Redis
- **Cache Invalidation**: Updates and deletes automatically invalidate cache
- **TTL**: Cache entries expire after 1 hour

### Error Handling
- **Validation Errors**: Pydantic validates all input data
- **Database Errors**: Proper error handling for MongoDB and Redis operations
- **Workflow Errors**: Temporal handles workflow failures gracefully
- **HTTP Errors**: FastAPI provides proper HTTP status codes

### Type Safety
- **Pydantic Models**: Full type safety with automatic validation
- **Async/Await**: Modern async Python patterns
- **Type Hints**: Complete type annotations throughout the codebase

## Development

### Adding New Workflows

1. Define the workflow in `jobs/workflows.py`
2. Create corresponding activities in `jobs/activities.py`
3. Add workflow service methods in `services/workflow_service.py`
4. Add API endpoints in `main.py`

### Adding New Models

1. Define the model in `models/data_models.py`
2. Create corresponding service methods in `services/data_service.py`
3. Add API endpoints in `main.py`

### Extending Services

The service layer provides a clean separation between business logic and data access. Each service handles:

- MongoDB operations
- Redis caching
- Data validation
- Error handling
- Workflow orchestration

## Dependencies

- **pydantic**: Data validation and settings management
- **motor**: Async MongoDB driver
- **redis**: Async Redis client
- **temporalio**: Temporal Python SDK
- **fastapi**: Web framework
- **uvicorn**: ASGI server
- **python-dotenv**: Environment variable loading

## License

This project is open source and available under the MIT License.
