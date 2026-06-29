# Documentation Directory

This documentation directory contains detailed documentation for the OClaw backend.

## Quick Links

| Document | Description |
|------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture overview |
| [API.md](API.md) | Complete API reference |
| [CONFIGURATION.md](CONFIGURATION.md) | Configuration options |
| [SETUP.md](SETUP.md) | Quick setup guide |

## Feature Documentation

| Document | Description |
|------|------|
| [STREAMING.md](STREAMING.md) | Token-level streaming design: Gateway & OClawClient paths, `stream_mode` semantics, dedup by ID |
| [CODING_AGENT.md](CODING_AGENT.md) | Coding Agent & Qiongqi Engine: isolated runtime, built-in skills, frontend workbench, diff/review/ROI workflow |
| [FILE_UPLOAD.md](FILE_UPLOAD.md) | File upload functionality |
| [PATH_EXAMPLES.md](PATH_EXAMPLES.md) | Path types and usage examples |
| [summarization.md](summarization.md) | Context summarization feature |
| [plan_mode_usage.md](plan_mode_usage.md) | Plan mode & TodoList |
| [AUTO_TITLE_GENERATION.md](AUTO_TITLE_GENERATION.md) | Auto title generation |

## Development

| Document | Description |
|------|------|
| [TODO.md](TODO.md) | Planned features & known issues |

## Quick Start

1. **New to OClaw?** Start with [SETUP.md](SETUP.md) for quick installation
2. **Configuring the system?** See [CONFIGURATION.md](CONFIGURATION.md)
3. **Understanding the architecture?** Read [ARCHITECTURE.md](ARCHITECTURE.md)
4. **Building integrations?** Check the [API.md](API.md) API reference

## Document Organization

```
docs/
├── README.md                  # This file
├── ARCHITECTURE.md            # System architecture
├── API.md                     # API reference
├── CONFIGURATION.md           # Configuration guide
├── SETUP.md                   # Setup instructions
├── FILE_UPLOAD.md             # File upload feature
├── CODING_AGENT.md            # Coding Agent & Qiongqi Engine
├── PATH_EXAMPLES.md           # Path usage examples
├── summarization.md           # Summarization feature
├── plan_mode_usage.md         # Plan mode feature
├── STREAMING.md               # Token-level streaming design
├── AUTO_TITLE_GENERATION.md   # Title generation
├── TITLE_GENERATION_IMPLEMENTATION.md  # Title implementation details
└── TODO.md                    # Roadmap & issues
```
