# Security Rules

- Never commit MT5/broker passwords, investor passwords, API keys, tokens, account IDs or private keys.
- Initial MT5 research should use a demo account and read-only data functions only.
- Trading/order functions are out of scope until explicitly reviewed.
- If future API keys are required, use least privilege and IP restrictions where available.
- Store secrets in local environment/secrets management, never in strategy configs or experiment markdown.
- Redact account identifiers from screenshots/logs before committing research evidence.
