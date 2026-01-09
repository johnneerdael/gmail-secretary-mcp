# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.1] - 2026-01-09

### Fixed
- Multi-architecture Docker builds now support both `linux/amd64` and `linux/arm64`
- Container registry URL corrected to `ghcr.io/johnneerdael/google-workspace-secretary-mcp`

### Added
- Manual OAuth flow (`--manual` flag) for Docker and headless environments
- Docker-based authentication documentation in oauth_workaround.md
- Redirect URI reference table for third-party OAuth providers

## [1.2.0] - 2026-01-08

### Added
- **Email Triage Tools**:
  - `quick_clean_inbox` - Auto-clean emails where user is not addressed (no confirmation required)
  - `triage_priority_emails` - Identify high-priority emails based on recipient count and name mentions
  - `triage_remaining_emails` - Process remaining emails after priority triage
- **User Identity Configuration**:
  - New `identity` section in config.yaml with `email`, `full_name`, and `aliases`
  - Automatic name parsing (first_name, last_name) from full_name
  - Methods for matching emails and name variations
- **New Email Signals**:
  - `is_addressed_to_me` - User's email in To: field
  - `mentions_my_name` - User's name mentioned in email body
- **OpenCode Slash Commands**:
  - `/clean-inbox` - Invoke quick_clean_inbox
  - `/triage-priority` - Invoke triage_priority_emails
  - `/triage-remaining` - Invoke triage_remaining_emails

### Changed
- `get_daily_briefing` now includes `is_addressed_to_me` and `mentions_my_name` signals
- AGENTS.md updated with triage tool documentation and confidence-based approval rules

## [1.1.0] - 2026-01-07

### Added
- Gmail-native search with `gmail_search` tool
- Smart labels system (`Secretary/Priority`, `Secretary/Action-Required`, etc.)
- Calendar integration with timezone-aware scheduling
- Document intelligence for PDF/DOCX attachments
- VIP sender configuration
- Working hours and workdays configuration

## [1.0.0] - 2026-01-05

### Added
- Initial release
- IMAP email access with OAuth2 authentication
- Basic email search and retrieval
- Thread summarization
- Draft creation (safe, non-sending)
- MCP server with Streamable HTTP transport
