# Security Policy

## Sensitive data

Never commit or publish:

- ASF bot configuration containing credentials
- Steam login credentials or login keys
- Steam Family View PINs
- ASF IPC passwords
- cryptkey files
- TLS private keys or certificates used by a private deployment
- cookies, session tokens or API tokens
- runtime databases
- private account dumps
- runtime logs containing account information
- local backup files

If sensitive data is committed, rotate the affected credential and remove
the data from Git history before publishing.

## Reporting

Please report security issues privately to the repository owner instead of
opening a public issue containing exploit details or secrets.

## Trust boundary

ASF Control Suite uses ASF's native IPC authentication. The project must not
introduce an arbitrary shell/process execution API or its own persistent
credential store.
