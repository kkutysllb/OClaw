# File Path Usage Examples

## Two Path Types

OClaw's file upload system returns two different path types, each for different scenarios:

### 1. Real Host Path (path)

```
/home/user/.kkoclaw/threads/{thread_id}/user-data/uploads/document.pdf
```

**Purpose:**
- The real absolute location of the file on the host filesystem (under `{KKOCLAW_HOME}/threads/{thread_id}/user-data/uploads/`, where `KKOCLAW_HOME` defaults to `~/.kkoclaw`)
- Agents, tools, and APIs now use this real path directly (the `/mnt/user-data` virtual path layer was removed in sandbox refactor phase 3)
- Used for direct filesystem access, backup, debugging, etc.

**Example:**
```python
# Direct access in Python code
from pathlib import Path
file_path = Path("/home/user/.kkoclaw/threads/abc123/user-data/uploads/document.pdf")
content = file_path.read_bytes()
```

The Agent also uses the same real path in conversation:
```python
# Agent uses the read_file tool
read_file(path="/home/user/.kkoclaw/threads/abc123/user-data/uploads/document.pdf")

# Agent uses the bash tool
bash(command="cat /home/user/.kkoclaw/threads/abc123/user-data/uploads/document.pdf")
```

> Prompts (lead_agent prompt, subagent prompts) no longer hardcode concrete paths; real paths are injected at runtime by workspace_path_middleware.

### 2. HTTP Access URL (artifact_url)

```
/api/threads/{thread_id}/artifacts/home/user/.kkoclaw/threads/{thread_id}/user-data/uploads/document.pdf
```

The `artifact_url` is built by concatenating `/api/threads/{thread_id}/artifacts` with the real host absolute path (the filename is percent-encoded).

**Purpose:**
- Frontend accesses files via HTTP
- Used for downloading and previewing files
- Can be opened directly in the browser
- The server validates that the path falls inside the current thread's `user-data/` root

**Example:**
```typescript
// Frontend TypeScript/JavaScript code
const threadId = 'abc123';
const realPath = '/home/user/.kkoclaw/threads/abc123/user-data/uploads/document.pdf';
const base = `/api/threads/${threadId}/artifacts`;

// Download file
const downloadUrl = `${base}${realPath}?download=true`;
window.open(downloadUrl);

// Preview in new window
const viewUrl = `${base}${realPath}`;
window.open(viewUrl, '_blank');

// Fetch using fetch API
const response = await fetch(viewUrl);
const blob = await response.blob();
```

## Complete Usage Flow Example

### Scenario: Frontend uploads file and lets Agent process it

```typescript
// 1. Frontend uploads file
async function uploadAndProcess(threadId: string, file: File) {
  // Upload file
  const formData = new FormData();
  formData.append('files', file);

  const uploadResponse = await fetch(
    `/api/threads/${threadId}/uploads`,
    {
      method: 'POST',
      body: formData
    }
  );

  const uploadData = await uploadResponse.json();
  const fileInfo = uploadData.files[0];

  console.log('File info:', fileInfo);
  // {
  //   filename: "report.pdf",
  //   path: "/home/user/.kkoclaw/threads/abc123/user-data/uploads/report.pdf",
  //   artifact_url: "/api/threads/abc123/artifacts/home/user/.kkoclaw/threads/abc123/user-data/uploads/report.pdf",
  //   markdown_file: "report.md",
  //   markdown_path: "/home/user/.kkoclaw/threads/abc123/user-data/uploads/report.md",
  //   markdown_artifact_url: "/api/threads/abc123/artifacts/home/user/.kkoclaw/threads/abc123/user-data/uploads/report.md"
  // }

  // 2. Send message to Agent
  await sendMessage(threadId, "Please analyze the just-uploaded PDF file");

  // Agent will automatically see the file list including:
  // - report.pdf (real host path: /home/user/.kkoclaw/threads/abc123/user-data/uploads/report.pdf)
  // - report.md (real host path: /home/user/.kkoclaw/threads/abc123/user-data/uploads/report.md)

  // 3. Frontend can directly access the converted Markdown
  const mdResponse = await fetch(fileInfo.markdown_artifact_url);
  const markdownContent = await mdResponse.text();
  console.log('Markdown content:', markdownContent);

  // 4. Or download the original PDF
  const downloadLink = document.createElement('a');
  downloadLink.href = fileInfo.artifact_url + '?download=true';
  downloadLink.download = fileInfo.filename;
  downloadLink.click();
}
```

## Path Usage Table

After the sandbox refactor there is no virtual path; the relationship between the paths used by the Agent, backend, and frontend is:

| Scenario | Path Type Used | Example |
|------|---------------|------|
| Agent tool calls | `path` (real host path) | `/home/user/.kkoclaw/threads/abc123/user-data/uploads/file.pdf` |
| Server backend direct access | `path` | `/home/user/.kkoclaw/threads/abc123/user-data/uploads/file.pdf` |
| Frontend download/preview | `artifact_url` | `/api/threads/abc123/artifacts/home/user/.kkoclaw/threads/abc123/user-data/uploads/file.pdf` |
| Backup scripts | `path` | `/home/user/.kkoclaw/threads/abc123/user-data/uploads/file.pdf` |
| Logging | `path` | `/home/user/.kkoclaw/threads/abc123/user-data/uploads/file.pdf` |

## Code Example Collection

### Python — Backend Processing

```python
from pathlib import Path
from kkoclaw.config.paths import get_paths

def process_uploaded_file(thread_id: str, filename: str):
    # Use the real host path (Paths exposes the thread's uploads directory)
    base_dir = get_paths().sandbox_uploads_dir(thread_id)
    file_path = base_dir / filename

    # Read directly
    with open(file_path, 'rb') as f:
        content = f.read()

    return content
```

### JavaScript — Frontend Access

```javascript
// List uploaded files
async function listUploadedFiles(threadId) {
  const response = await fetch(`/api/threads/${threadId}/uploads/list`);
  const data = await response.json();

  // Create download links for each file
  data.files.forEach(file => {
    console.log(`File: ${file.filename}`);
    console.log(`Download: ${file.artifact_url}?download=true`);
    console.log(`Preview: ${file.artifact_url}`);

    // If it's a document, there's also a Markdown version
    if (file.markdown_artifact_url) {
      console.log(`Markdown: ${file.markdown_artifact_url}`);
    }
  });

  return data.files;
}

// Delete file
async function deleteFile(threadId, filename) {
  const response = await fetch(
    `/api/threads/${threadId}/uploads/${filename}`,
    { method: 'DELETE' }
  );
  return response.json();
}
```

### React Component Example

```tsx
import React, { useState, useEffect } from 'react';

interface UploadedFile {
  filename: string;
  size: number;
  path: string;            // real host absolute path
  artifact_url: string;    // HTTP URL embedding the same real path
  extension: string;
  modified: number;
  markdown_artifact_url?: string;
}

function FileUploadList({ threadId }: { threadId: string }) {
  const [files, setFiles] = useState<UploadedFile[]>([]);

  useEffect(() => {
    fetchFiles();
  }, [threadId]);

  async function fetchFiles() {
    const response = await fetch(`/api/threads/${threadId}/uploads/list`);
    const data = await response.json();
    setFiles(data.files);
  }

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const fileList = event.target.files;
    if (!fileList) return;

    const formData = new FormData();
    Array.from(fileList).forEach(file => {
      formData.append('files', file);
    });

    await fetch(`/api/threads/${threadId}/uploads`, {
      method: 'POST',
      body: formData
    });

    fetchFiles(); // Refresh list
  }

  async function handleDelete(filename: string) {
    await fetch(`/api/threads/${threadId}/uploads/${filename}`, {
      method: 'DELETE'
    });
    fetchFiles(); // Refresh list
  }

  return (
    <div>
      <input type="file" multiple onChange={handleUpload} />

      <ul>
        {files.map(file => (
          <li key={file.filename}>
            <span>{file.filename}</span>
            <a href={file.artifact_url} target="_blank">Preview</a>
            <a href={`${file.artifact_url}?download=true`}>Download</a>
            {file.markdown_artifact_url && (
              <a href={file.markdown_artifact_url} target="_blank">Markdown</a>
            )}
            <button onClick={() => handleDelete(file.filename)}>Delete</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

## Important Notes

1. **Path Security**
   - The actual path (`path`) includes the thread ID, ensuring isolation
   - The API validates paths to prevent directory traversal attacks
   - The frontend should not use `path` directly, but use `artifact_url`

2. **Agent Usage**
   - The Agent sees and uses the real host path (`path`) directly
   - After the sandbox refactor there is no virtual path layer; the Agent and backend use the same path
   - The server still validates that the path falls inside the current thread's `user-data/` root

3. **Frontend Integration**
   - Always use `artifact_url` to access files
   - Do not attempt to access filesystem paths directly
   - Use `?download=true` parameter to force download

4. **Markdown Conversion**
   - On successful conversion, additional `markdown_*` fields are returned
   - It is recommended to prioritize the Markdown version (easier to process)
   - The original file is always preserved
