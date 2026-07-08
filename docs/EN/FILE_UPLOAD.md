# File Upload Feature

## Overview

The OClaw backend provides complete file upload functionality, supporting multi-file uploads with optional conversion of Office documents and PDFs to Markdown format.

## Features

- ✅ Support for simultaneous multi-file uploads
- ✅ Optional document-to-Markdown conversion (PDF, PPT, Excel, Word)
- ✅ File storage in thread-isolated directories
- ✅ Agent automatically detects uploaded files
- ✅ Support for file listing and deletion

## API Endpoints

### 1. Upload Files
```
POST /api/threads/{thread_id}/uploads
```

**Request Body:** `multipart/form-data`
- `files`: One or more files

The gateway enforces upload size limits at the application layer, by default max 10 files, 50 MiB per file, and 100 MiB total per request. These can be adjusted via `uploads.max_files`, `uploads.max_file_size`, and `uploads.max_total_size` in `config.yaml`; the frontend reads the same limits and prompts the user when selecting files — exceeding limits results in a `413 Payload Too Large` response from the backend.

**Response:**
```json
{
  "success": true,
  "files": [
    {
      "filename": "document.pdf",
      "size": 1234567,
      "path": "/home/user/.kkoclaw/threads/{thread_id}/user-data/uploads/document.pdf",
      "artifact_url": "/api/threads/{thread_id}/artifacts/home/user/.kkoclaw/threads/{thread_id}/user-data/uploads/document.pdf",
      "markdown_file": "document.md",
      "markdown_path": "/home/user/.kkoclaw/threads/{thread_id}/user-data/uploads/document.md",
      "markdown_artifact_url": "/api/threads/{thread_id}/artifacts/home/user/.kkoclaw/threads/{thread_id}/user-data/uploads/document.md"
    }
  ],
  "message": "Successfully uploaded 1 file(s)"
}
```

**Path Descriptions:**
- `path`: Real host absolute path (under `{KKOCLAW_HOME}/threads/{thread_id}/user-data/uploads/`)
- `artifact_url`: URL for frontend HTTP access to the file; it embeds the same real host path
- Agents, tools, and APIs now use real host paths directly; the `virtual_path` / `markdown_virtual_path` fields were removed in the sandbox refactor (phase 3)

### 2. Query Upload Limits
```
GET /api/threads/{thread_id}/uploads/limits
```

Returns the gateway's current upload limits for frontend prompting and interception before file selection.

**Response:**
```json
{
  "max_files": 10,
  "max_file_size": 52428800,
  "max_total_size": 104857600
}
```

### 3. List Uploaded Files
```
GET /api/threads/{thread_id}/uploads/list
```

**Response:**
```json
{
  "files": [
    {
      "filename": "document.pdf",
      "size": 1234567,
      "path": "/home/user/.kkoclaw/threads/{thread_id}/user-data/uploads/document.pdf",
      "artifact_url": "/api/threads/{thread_id}/artifacts/home/user/.kkoclaw/threads/{thread_id}/user-data/uploads/document.pdf",
      "extension": ".pdf",
      "modified": 1705997600.0
    }
  ],
  "count": 1
}
```

### 4. Delete File
```
DELETE /api/threads/{thread_id}/uploads/{filename}
```

**Response:**
```json
{
  "success": true,
  "message": "Deleted document.pdf"
}
```

## Supported Document Formats

The following formats are automatically converted to Markdown when `uploads.auto_convert_documents: true` is explicitly enabled:
- PDF (`.pdf`)
- PowerPoint (`.ppt`, `.pptx`)
- Excel (`.xls`, `.xlsx`)
- Word (`.doc`, `.docx`)

Converted Markdown files are saved in the same directory with the original filename + `.md` extension.

By default, auto-conversion is disabled to avoid parsing untrusted Office/PDF uploads on the gateway host. Only set `uploads.auto_convert_documents` to `true` in trusted deployments where this risk is explicitly accepted.

## Agent Integration

### Automatic File Listing

The Agent automatically receives a list of uploaded files on each request, formatted as follows (paths are real host absolute paths, injected at runtime by workspace_path_middleware):

```xml
<uploaded_files>
The following files have been uploaded and are available for use:

- document.pdf (1.2 MB)
  Path: /home/user/.kkoclaw/threads/{thread_id}/user-data/uploads/document.pdf

- document.md (45.3 KB)
  Path: /home/user/.kkoclaw/threads/{thread_id}/user-data/uploads/document.md

You can read these files using the `read_file` tool with the paths shown above.
</uploaded_files>
```

### Using Uploaded Files

The Agent accesses files via real host absolute paths directly — no virtual path layer. The Agent can directly use the `read_file` tool to read uploaded files:

```python
# Read original PDF (if supported)
read_file(path="/home/user/.kkoclaw/threads/{thread_id}/user-data/uploads/document.pdf")

# Read converted Markdown (recommended)
read_file(path="/home/user/.kkoclaw/threads/{thread_id}/user-data/uploads/document.md")
```

**Path notes (after the sandbox refactor):**
- Agent uses: a real host absolute path (e.g. `/home/user/.kkoclaw/threads/{thread_id}/user-data/uploads/document.pdf`)
- Actual storage: the same real path (`{KKOCLAW_HOME}/threads/{thread_id}/user-data/uploads/document.pdf`)
- Frontend access: `/api/threads/{thread_id}/artifacts` + the real host path (HTTP URL)

Prompts (lead_agent prompt, subagent prompts) no longer hardcode `/mnt/user-data` paths; real paths are injected at runtime by workspace_path_middleware.

The upload flow follows a "thread directory first" strategy:
- First writes to `{KKOCLAW_HOME}/threads/{thread_id}/user-data/uploads/` as authoritative storage
- Local sandbox (`sandbox_id=local`) directly uses thread directory contents
- Non-local sandboxes additionally sync to the sandbox container's mount point, ensuring runtime visibility

## Test Examples

### Testing with curl

```bash
# 1. Upload a single file
curl -X POST http://localhost:2026/api/threads/test-thread/uploads \
  -F "files=@/path/to/document.pdf"

# 2. Upload multiple files
curl -X POST http://localhost:2026/api/threads/test-thread/uploads \
  -F "files=@/path/to/document.pdf" \
  -F "files=@/path/to/presentation.pptx" \
  -F "files=@/path/to/spreadsheet.xlsx"

# 3. List uploaded files
curl http://localhost:2026/api/threads/test-thread/uploads/list

# 4. Delete file
curl -X DELETE http://localhost:2026/api/threads/test-thread/uploads/document.pdf
```

### Testing with Python

```python
import requests

thread_id = "test-thread"
base_url = "http://localhost:2026"

# Upload files
files = [
    ("files", open("document.pdf", "rb")),
    ("files", open("presentation.pptx", "rb")),
]
response = requests.post(
    f"{base_url}/api/threads/{thread_id}/uploads",
    files=files
)
print(response.json())

# List files
response = requests.get(f"{base_url}/api/threads/{thread_id}/uploads/list")
print(response.json())

# Delete file
response = requests.delete(
    f"{base_url}/api/threads/{thread_id}/uploads/document.pdf"
)
print(response.json())
```

## File Storage Structure

```
{KKOCLAW_HOME}/threads/        # KKOCLAW_HOME defaults to ~/.kkoclaw
└── {thread_id}/
    └── user-data/
        └── uploads/
            ├── document.pdf          # Original file
            ├── document.md           # Converted Markdown
            ├── presentation.pptx
            ├── presentation.md
            └── ...
```

## Limitations

- Max file size: 100MB (configurable in nginx.conf via `client_max_body_size`)
- Filename security: System automatically validates file paths to prevent directory traversal attacks
- Thread isolation: Uploaded files are mutually isolated per thread and cannot be cross-accessed
- Automatic document conversion is off by default; enable explicitly via `uploads.auto_convert_documents: true` in `config.yaml` if needed

## Technical Implementation

### Components

1. **Upload Router** (`app/gateway/routers/uploads.py`)
   - Handles file upload, listing, and deletion requests
   - Uses markitdown for document conversion

2. **Uploads Middleware** (`packages/harness/kkoclaw/agents/middlewares/uploads_middleware.py`)
   - Injects file list before each Agent request
   - Automatically generates formatted file list messages

3. **Nginx Configuration** (`nginx.conf`)
   - Routes upload requests to Gateway API
   - Configures large file upload support

### Dependencies

- `markitdown>=0.0.1a2` — Document conversion
- `python-multipart>=0.0.20` — File upload processing

## Troubleshooting

### File Upload Failed

1. Check if file size exceeds the limit
2. Check if Gateway API is running properly
3. Check disk space availability
4. View Gateway logs: `make gateway`

### Document Conversion Failed

1. Check if markitdown is properly installed: `uv run python -c "import markitdown"`
2. View specific error messages in logs
3. Some damaged or encrypted documents may not convert, but the original file is still saved

### Agent Cannot See Uploaded Files

1. Confirm UploadsMiddleware is registered in agent.py
2. Verify the thread_id is correct
3. Confirm files are actually uploaded to `{KKOCLAW_HOME}/threads/{thread_id}/user-data/uploads/`
4. For non-local sandbox scenarios, confirm the upload endpoint reported no errors (sandbox sync must complete successfully)

## Development Suggestions

### Frontend Integration

```typescript
// Upload files example
async function uploadFiles(threadId: string, files: File[]) {
  const formData = new FormData();
  files.forEach(file => {
    formData.append('files', file);
  });

  const response = await fetch(
    `/api/threads/${threadId}/uploads`,
    {
      method: 'POST',
      body: formData,
    }
  );

  return response.json();
}

// List files
async function listFiles(threadId: string) {
  const response = await fetch(
    `/api/threads/${threadId}/uploads/list`
  );
  return response.json();
}
```

### Feature Extension Suggestions

1. **File Preview**: Add preview endpoint to view files directly in browser
2. **Batch Deletion**: Support deleting multiple files at once
3. **File Search**: Support searching by filename or type
4. **Version Control**: Retain multiple versions of files
5. **Archive Support**: Auto-extract zip files
6. **Image OCR**: Perform OCR recognition on uploaded images
