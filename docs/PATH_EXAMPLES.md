# 文件路径使用示例

## 两种路径类型

OClaw 的文件上传系统返回两种不同的路径，每种路径用于不同的场景：

### 1. 真实主机路径 (path)

```
/home/user/.kkoclaw/threads/{thread_id}/user-data/uploads/document.pdf
```

**用途：**
- 文件在主机文件系统中的真实绝对位置（位于 `{KKOCLAW_HOME}/threads/{thread_id}/user-data/uploads/` 下，`KKOCLAW_HOME` 默认为 `~/.kkoclaw`）
- Agent、工具、API 现在直接使用这个真实路径（沙箱重构阶段三已删除 `/mnt/user-data` 虚拟路径层）
- 用于直接文件系统访问、备份、调试等

**示例：**
```python
# Python 代码中直接访问
from pathlib import Path
file_path = Path("/home/user/.kkoclaw/threads/abc123/user-data/uploads/document.pdf")
content = file_path.read_bytes()
```

Agent 在对话中也使用同一真实路径：
```python
# Agent 使用 read_file 工具
read_file(path="/home/user/.kkoclaw/threads/abc123/user-data/uploads/document.pdf")

# Agent 使用 bash 工具
bash(command="cat /home/user/.kkoclaw/threads/abc123/user-data/uploads/document.pdf")
```

> 提示词（lead_agent prompt、subagent prompts）不再硬编码具体路径；真实路径由 workspace_path_middleware 在运行时注入。

### 2. HTTP 访问 URL (artifact_url)

```
/api/threads/{thread_id}/artifacts/home/user/.kkoclaw/threads/{thread_id}/user-data/uploads/document.pdf
```

`artifact_url` 由 `/api/threads/{thread_id}/artifacts` + 真实主机绝对路径拼接而成（文件名做了 percent-encoding）。

**用途：**
- 前端通过 HTTP 访问文件
- 用于下载、预览文件
- 可以直接在浏览器中打开
- 服务端会校验该路径是否落在当前线程的 `user-data/` 根目录内

**示例：**
```typescript
// 前端 TypeScript/JavaScript 代码
const threadId = 'abc123';
const realPath = '/home/user/.kkoclaw/threads/abc123/user-data/uploads/document.pdf';
const base = `/api/threads/${threadId}/artifacts`;

// 下载文件
const downloadUrl = `${base}${realPath}?download=true`;
window.open(downloadUrl);

// 在新窗口预览
const viewUrl = `${base}${realPath}`;
window.open(viewUrl, '_blank');

// 使用 fetch API 获取
const response = await fetch(viewUrl);
const blob = await response.blob();
```

## 完整使用流程示例

### 场景：前端上传文件并让 Agent 处理

```typescript
// 1. 前端上传文件
async function uploadAndProcess(threadId: string, file: File) {
  // 上传文件
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

  console.log('文件信息：', fileInfo);
  // {
  //   filename: "report.pdf",
  //   path: "/home/user/.kkoclaw/threads/abc123/user-data/uploads/report.pdf",
  //   artifact_url: "/api/threads/abc123/artifacts/home/user/.kkoclaw/threads/abc123/user-data/uploads/report.pdf",
  //   markdown_file: "report.md",
  //   markdown_path: "/home/user/.kkoclaw/threads/abc123/user-data/uploads/report.md",
  //   markdown_artifact_url: "/api/threads/abc123/artifacts/home/user/.kkoclaw/threads/abc123/user-data/uploads/report.md"
  // }

  // 2. 发送消息给 Agent
  await sendMessage(threadId, "请分析刚上传的 PDF 文件");

  // Agent 会自动看到文件列表，包含：
  // - report.pdf (真实主机路径: /home/user/.kkoclaw/threads/abc123/user-data/uploads/report.pdf)
  // - report.md (真实主机路径: /home/user/.kkoclaw/threads/abc123/user-data/uploads/report.md)

  // 3. 前端可以直接访问转换后的 Markdown
  const mdResponse = await fetch(fileInfo.markdown_artifact_url);
  const markdownContent = await mdResponse.text();
  console.log('Markdown 内容：', markdownContent);

  // 4. 或者下载原始 PDF
  const downloadLink = document.createElement('a');
  downloadLink.href = fileInfo.artifact_url + '?download=true';
  downloadLink.download = fileInfo.filename;
  downloadLink.click();
}
```

## 路径使用表

沙箱重构后不再有虚拟路径，Agent、后端、前端三方使用的路径关系如下：

| 场景 | 使用的路径类型 | 示例 |
|------|---------------|------|
| Agent 工具调用 | `path`（真实主机路径） | `/home/user/.kkoclaw/threads/abc123/user-data/uploads/file.pdf` |
| 服务器后端代码直接访问 | `path` | `/home/user/.kkoclaw/threads/abc123/user-data/uploads/file.pdf` |
| 前端下载/预览 | `artifact_url` | `/api/threads/abc123/artifacts/home/user/.kkoclaw/threads/abc123/user-data/uploads/file.pdf` |
| 备份脚本 | `path` | `/home/user/.kkoclaw/threads/abc123/user-data/uploads/file.pdf` |
| 日志记录 | `path` | `/home/user/.kkoclaw/threads/abc123/user-data/uploads/file.pdf` |

## 代码示例集合

### Python - 后端处理

```python
from pathlib import Path
from kkoclaw.config.paths import get_paths

def process_uploaded_file(thread_id: str, filename: str):
    # 使用真实主机路径（Paths 暴露线程的 uploads 目录）
    base_dir = get_paths().sandbox_uploads_dir(thread_id)
    file_path = base_dir / filename

    # 直接读取
    with open(file_path, 'rb') as f:
        content = f.read()

    return content
```

### JavaScript - 前端访问

```javascript
// 列出已上传的文件
async function listUploadedFiles(threadId) {
  const response = await fetch(`/api/threads/${threadId}/uploads/list`);
  const data = await response.json();

  // 为每个文件创建下载链接
  data.files.forEach(file => {
    console.log(`文件: ${file.filename}`);
    console.log(`下载: ${file.artifact_url}?download=true`);
    console.log(`预览: ${file.artifact_url}`);

    // 如果是文档，还有 Markdown 版本
    if (file.markdown_artifact_url) {
      console.log(`Markdown: ${file.markdown_artifact_url}`);
    }
  });

  return data.files;
}

// 删除文件
async function deleteFile(threadId, filename) {
  const response = await fetch(
    `/api/threads/${threadId}/uploads/${filename}`,
    { method: 'DELETE' }
  );
  return response.json();
}
```

### React 组件示例

```tsx
import React, { useState, useEffect } from 'react';

interface UploadedFile {
  filename: string;
  size: number;
  path: string;            // 真实主机绝对路径
  artifact_url: string;    // 内嵌同一真实路径的 HTTP URL
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

    fetchFiles(); // 刷新列表
  }

  async function handleDelete(filename: string) {
    await fetch(`/api/threads/${threadId}/uploads/${filename}`, {
      method: 'DELETE'
    });
    fetchFiles(); // 刷新列表
  }

  return (
    <div>
      <input type="file" multiple onChange={handleUpload} />

      <ul>
        {files.map(file => (
          <li key={file.filename}>
            <span>{file.filename}</span>
            <a href={file.artifact_url} target="_blank">预览</a>
            <a href={`${file.artifact_url}?download=true`}>下载</a>
            {file.markdown_artifact_url && (
              <a href={file.markdown_artifact_url} target="_blank">Markdown</a>
            )}
            <button onClick={() => handleDelete(file.filename)}>删除</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

## 注意事项

1. **路径安全性**
   - 实际路径（`path`）包含线程 ID，确保隔离
   - API 会验证路径，防止目录遍历攻击
   - 前端不应直接使用 `path`，而应使用 `artifact_url`

2. **Agent 使用**
   - Agent 直接看到和使用真实主机路径（`path`）
   - 沙箱重构后不再有虚拟路径层，Agent 与后端使用同一路径
   - 服务端仍会校验路径落在当前线程的 `user-data/` 根目录内

3. **前端集成**
   - 始终使用 `artifact_url` 访问文件
   - 不要尝试直接访问文件系统路径
   - 使用 `?download=true` 参数强制下载

4. **Markdown 转换**
   - 转换成功时，会返回额外的 `markdown_*` 字段
   - 建议优先使用 Markdown 版本（更易处理）
   - 原始文件始终保留
