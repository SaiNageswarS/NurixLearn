# NurixLearn - Math Solution Evaluation Application

An application to evaluate a hand-written math solution against a given problem using AI-powered analysis.

## Introduction

NurixLearn is a Python application that analyzes hand-written mathematical solutions by comparing them against given problems. The application uses AI to evaluate correctness, identify errors, and provide detailed feedback on student work. It can process images of both the original problem and the student's handwritten solution to provide comprehensive evaluation results.

## Features

- **AI-Powered Math Evaluation**: Uses advanced AI models to analyze mathematical solutions
- **Image Processing**: Handles both printed problem images and handwritten solution images
- **Error Detection**: Identifies specific errors and provides detailed feedback
- **Flexible Storage**: Supports both local filesystem and Azure Blob Storage
- **Dual Operation Modes**: Can run as a workflow or API service
- **Bounding Box Support**: Allows focusing on specific regions of images
- **Comprehensive Results**: Provides correctness scores, error analysis, and detailed feedback

## Operation Modes

The application can be run in two different modes:

### 1. Workflow Mode
Direct execution of the math evaluation workflow with command-line arguments.

### 2. API Service Mode
Runs as a FastAPI server providing REST endpoints for math evaluation.

## Usage

### Workflow Mode

Run the application directly with command-line arguments to process a single math evaluation:

```bash
python main.py --mode workflow --container-name mock_data --question-image Q1.jpeg --working-note-image Attempt1.jpeg --student-id student123 --assignment-id assignment456
```

#### Required Parameters:
- `--container-name`: Container/folder name containing the images
- `--question-image`: Image filename for the printed question
- `--working-note-image`: Image filename for the handwritten working note

#### Optional Parameters:
- `--student-id`: Student identifier for tracking
- `--assignment-id`: Assignment identifier for tracking
- `--bbox-x`: X coordinate of bounding box top-left corner (for focusing on specific image regions)
- `--bbox-y`: Y coordinate of bounding box top-left corner
- `--bbox-width`: Width of the bounding box
- `--bbox-height`: Height of the bounding box

#### Example with Bounding Box:
```bash
python main.py --mode workflow --container-name mock_data --question-image Q1.jpeg --working-note-image Attempt1.jpeg --student-id student123 --assignment-id assignment456 --bbox-x 100 --bbox-y 50 --bbox-width 200 --bbox-height 150
```

### API Service Mode

Run the application as a FastAPI server:

```bash
python main.py --mode server
```

The API will be available at `http://localhost:8000`

- **API Documentation**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

#### API Endpoints:
- `POST /evaluate` - Evaluate a math solution
- `GET /health` - Application health status
- `GET /evaluations/{evaluation_id}` - Get evaluation result by ID

## Storage Managers

The application supports two storage backends for handling images:

### LocalStorageManager

Uses the local filesystem where `container_name` is treated as a folder name.

**Configuration:**
- Images are stored in: `{base_path}/{container_name}/{image_name}`
- Default base path is the current directory
- Supports common image formats: JPG, PNG, GIF, BMP, WebP

**Testing Setup:**
1. Create a folder structure:
   ```bash
   mkdir -p mock_data
   cp your_question_image.jpg mock_data/Q1.jpeg
   cp your_solution_image.jpg mock_data/Attempt1.jpeg
   ```

2. Run with local storage:
   ```bash
   python main.py --mode workflow --container-name mock_data --question-image Q1.jpeg --working-note-image Attempt1.jpeg
   ```

### AzureStorageManager

Uses Azure Blob Storage with service principal authentication.

**Configuration:**
Set the following environment variables:
```env
AZURE_CLIENT_ID=your_client_id
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_SECRET=your_client_secret
AZURE_STORAGE_ACCOUNT_NAME=your_storage_account
```

**Testing Setup:**
1. Create an Azure Storage Account
2. Create a container (e.g., "math-images")
3. Upload your images to the container
4. Set up a service principal with Blob Storage permissions
5. Configure the environment variables
6. Run the application:
   ```bash
   python main.py --mode workflow --container-name math-images --question-image Q1.jpeg --working-note-image Attempt1.jpeg
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

Edit `.env` with your configuration:

```env
# MongoDB Configuration (optional for basic usage)
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=myapp

# Redis Configuration (optional for basic usage)
REDIS_URL=redis://localhost:6379
REDIS_DB=0

# Azure Configuration (required for AzureStorageManager)
AZURE_CLIENT_ID=your_client_id
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_SECRET=your_client_secret
AZURE_STORAGE_ACCOUNT_NAME=your_storage_account
AZURE_STORAGE_CONTAINER=math-images

# LLM Configuration (required for AI evaluation)
OPENAI_API_KEY=your_openai_api_key

# Application Configuration
APP_NAME=MathEvaluationApp
DEBUG=True
```

### 3. Quick Start with Local Storage

For immediate testing with local files:

1. Create test data:
   ```bash
   mkdir -p mock_data
   # Add your question and solution images to mock_data/
   ```

2. Run evaluation:
   ```bash
   python main.py --mode workflow --container-name mock_data --question-image your_question.jpg --working-note-image your_solution.jpg
   ```

## Project Structure

```
├── main.py                      # Main entry point with CLI and server modes
├── config/
│   └── settings.py              # Configuration management
├── models/
│   └── data_models.py           # Pydantic models for data validation
├── utils/
│   ├── storage.py               # Storage managers (Local & Azure)
│   └── database.py              # Database connection management
├── services/
│   └── detect_error_service.py  # API service implementation
├── jobs/
│   ├── workflow.py              # Math evaluation workflow
│   └── activities.py            # Workflow activities
├── requirements.txt             # Python dependencies
├── env.example                  # Environment variables template
└── README.md                   # This file
```

## Dependencies

- **pydantic**: Data validation and settings management
- **fastapi**: Web framework for API mode
- **uvicorn**: ASGI server
- **azure-storage-blob**: Azure Blob Storage integration
- **azure-identity**: Azure authentication
- **openai**: AI model integration for math evaluation
- **motor**: Async MongoDB driver (optional)
- **redis**: Async Redis client (optional)
- **python-dotenv**: Environment variable loading

## License

This project is open source and available under the MIT License.