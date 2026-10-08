# Caddy staging snippets — NOT production deployment

These are **design examples** only. The friend's running Caddyfile and
subdomain names are currently unknown. Do NOT apply to the VPS until the owner
confirms the names and its existing Caddy imports/site configuration.

## Safe first step: a disabled site with managed TLS

When the friend authorizes a temporary test hostname and its public DNS
(A/AAAA) points to the VPS, an additional site block can request an HTTPS
certificate **without connecting to ASF/Drophira**:

```caddyfile
# Replace the documentation-only hostname with a real temporary subdomain.
staging.example.com {
    respond "Service not enabled" 403
}
```

This is a **deny-all staging block**: no `reverse_proxy`, no auth bypass and
no connection to the phone. Keep existing Caddy sites intact. The VPS admin
validates the *assembled* Caddy config before reloading; they are not asked
to run arbitrary scripts. Caddy may still contact ACME for the staging
hostname; only enable this when DNS and issuance are approved.

Caddy automatically manages public certificates when the public hostname
resolves correctly and its challenges can succeed:
https://caddyserver.com/docs/automatic-https .

## Proxy sketch for a future authorized private integration

The following lines are *schematic* and **must stay commented/disabled**
until the auth boundary, port, private listener and Tailscale permissions
have been tested:

```caddyfile
# asf.example.com {
#     # Require a separately verified front-door authorization policy here,
#     # or serve ONLY over Tailscale, never as open public admin UI.
#     reverse_proxy http://PHONE_PRIVATE_TAILSCALE_IP:ASF_PRIVATE_PORT
# }
#
# drops.example.com {
#     # Current Drophira UI includes administrative controls.
#     # It must NOT be published publicly in this form.
#     reverse_proxy http://PHONE_PRIVATE_TAILSCALE_IP:DROPHIRA_PRIVATE_PORT
# }
```

Nothing on this list proves those ports actually exist on the phone.
Specifically, the existing ASF HTTPS listener on Tailscale :1243 is not an
HTTP listener and must not be pointed to with `http://` until a separate
trusted private HTTP bridge is designed and tested.

**Never** put a Tailscale-auth key, Twitch/Steam token, WebUI password,
friend's existing Caddy configuration or real service credentials in GitHub.
Never enable `tls_insecure_skip_verify` to force a self-signed HTTPS
connection. If HTTPS upstream is chosen, configure a genuinely trusted CA
and an appropriate SNI. Caddy official transport documentation:
https://caddyserver.com/docs/caddyfile/directives/reverse_proxy .

A future public client proxy also needs an identity broker with strict
client isolation. Caddy's `forward_auth` is an *optional authorization
integration*, not a substitute for backend tenant RBAC:
https://caddyserver.com/docs/caddyfile/directives/forward_auth .

## Acceptance before applying any non-disabled proxy

- [ ] Real DNS and test subdomain are confirmed.
- [ ] Caddy VPS is on Tailscale and can reach a narrowly scoped phone port.
- [ ] Correct address family, protocol, Host/Origin forwarding and WebSockets.
- [ ] Deny unauthenticated API and websocket requests; admin stays private.
- [ ] Secure/SameSite/HttpOnly cookies and logout invalidate sessions.
- [ ] No sensitive response or authorization cookie in VPS logs.
- [ ] All existing friend VPS sites continue operating.
- [ ] Pre-change Caddy/DNS/Tailscale state is saved for rollback.
- [ ] Phone ASF and Drophira continue healthy before/after test.
