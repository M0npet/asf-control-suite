# Preliminary exposure review: current ASF and Drophira WebUIs

**Source review only.** Not a live phone security test, penetration test,
or approval to open an administrative interface publicly.

Sources: ASF `SECURITY.md`, `docs/architecture/README.md`;
Drophira `docs/SECURITY_MODEL.md`, `backend/src/drophira/auth.py`.

## Findings

- **ASF Control Suite:** the native ASF IPC `Authentication` header
  protects administrative APIs. Browser retains IPC password in **RAM only**
  and removes it on refresh/lock/logout. The entire native ASF workspace
  remains available, including bot configuration and privileged commands.
  It has no demonstrated per-client account RBAC. **ADMIN / TAILSCALE ONLY.**
- **Drophira:** one server-side WebUI password with scrypt hash; random
  in-memory session tokens in HttpOnly, SameSite=Strict cookies (12-hour
  default). Same-origin checks on HTTP mutations and WebSocket connection.
  This is **single-owner admin auth**, not a multi-tenant client portal.
  **ADMIN / TAILSCALE ONLY.**
- **Shared VPS trust:** Caddy terminates browser TLS. Friend's VPS operator
  could inspect decrypted credentials, cookies and HTTP bodies. Tailscale
  encrypts the *VPS-to-phone* link but does not hide data from the VPS.
  Owner must explicitly accept this model before transporting secrets.
- **Public risks to address later:** scoped client identities and account
  assignments, MFA for admins, anti-brute-force rate limits, session
  revocation, audit trail, logging redaction, CSRF/Origin, forwarded Host,
  per-user WebSocket isolation and negative authorization tests. A proxy
  password or forward_auth alone does not provide backend tenant isolation.
- **Drophira proxy config:** require `DROPHIRA_SECURE_COOKIE=1` for an HTTPS
  browser origin, preserve original Host and Origin in reverse proxy,
  keep `DROPHIRA_ALLOW_UNAUTHENTICATED` disabled.
- **Port safety:** no direct public ASF IPC, `/Api/*`, Termux, ADB,
  Drophira :8080, SSH, database or raw container ports.

## Fail-closed release checks

1. Public request for any unapproved ASF/Drophira admin hostname returns
   a denial without upstream data.
2. Anonymous login and WebSocket routes reject unauthorized clients.
3. Client A cannot read or control account B (HTTP AND WebSocket).
4. Caddy logs contain no Steam/Twitch secrets, IPC passwords, access tokens,
   session cookies, private configurations or request bodies.
5. Revoking Tailscale grants/shared device removes connectivity and does
   not reveal a non-Tailscale fallback.
6. TLS/Host/Secure-cookie and CSRF remain correct after Caddy termination.
7. Upstream down/phone sleep/rollback fails closed and leaves unrelated
   sites on friend's Caddy unchanged.

Future portal design issues: ASF #35 and Drophira #32.
Network issue: ASF #37. No live actions authorized.
