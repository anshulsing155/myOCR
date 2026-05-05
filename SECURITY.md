# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 1.x | Yes |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Email the maintainer directly at the address listed on the GitHub profile. Include:

1. A description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Any suggested fix (optional)

You can expect an acknowledgement within 48 hours and a resolution or timeline within 7 days.

## Sensitive Data Handling

This project processes identity and financial documents. When contributing:

- Never commit files from `inputs/` or `outputs/`
- Never hardcode API keys, tokens, or credentials
- Use environment variables (see `.env.example`) for all secrets
- Do not log or print document content in production code
