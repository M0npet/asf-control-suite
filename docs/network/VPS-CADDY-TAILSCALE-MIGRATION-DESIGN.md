# Draft: Mi Max 2 → friend's VPS / Caddy / Tailscale

**Status:** design only, no host, DNS, Tailscale or phone configuration changed.

**Scope:** existing ASF Control Suite (in phone `debian` PRoot) and Drophira
(in separate phone `drophira` PRoot), behind friend's **existing public VPS**
and **existing Caddy** reverse proxy. Friend manages DNS subdomains and
automated certificates. Later: separate client portal/admin console tracked
in [ASF #35](https://github.com/M0npet/asf-control-suite/issues/35) and
[Drophira #32](https://github.com/M0npet/Drophira/issues/32).

This plan is subordinate to [ASF #37](https://github.com/M0npet/asf-control-suite/issues/37)
and [Drophira #33](https://github.com/M0npet/Drophira/issues/33).
It is **not an approval** to expose existing admin UIs on the internet.

## 1. Confirmed and unknown facts

Confirmed by owner:
- Caddy runs **on friend's VPS**, not on home NAT equipment.
- Friend provisions **subdomains** and their HTTPS certificates through this
  existing Caddy/domain workflow.
- Friend will answer a short nontechnical questionnaire but will **not run a
  diagnostic script** on the VPS.

Known phone baseline (from prior acceptance, NOT rechecked for this migration):
- Android 13 / Termux / Tailscale, ASF in `debian`, Drophira in `drophira`.
- ASF HTTPS proxy had been accessible over Tailscale at port 1243.
- Drophira's health/UI were loopback-bound on 127.0.0.1:8080, accessible from
  tablet through explicit ADB port forwarding; it is **not yet a routable VPS
  upstream**.
- Each service has an independent lifecycle. Do not conflate Drophira and ASF.

Still required from friend (text answers, no shell or secrets):
1. Base domain / two available subdomain labels (or ask friend to pick them).
2. Is **Tailscale installed on this same VPS** running Caddy? If not, can
   the friend add it?
3. Is VPS a normal *user-owned* Tailscale node or a **tagged service node**?
   Friend can answer 'don't know'; we then choose a test before changing
   anything. Sharing a machine from one tailnet to a user in another does **not**
   make it usable by that other tailnet's tagged nodes.
4. Is the friend willing to make **two additive Caddy host blocks** later,
   preserving all existing sites, with a rollback to the previous config?
5. Existing front-door login layer: Authelia / Authentik / Cloudflare Access /
   other / none, and whether MFA is available. **No admin/public site until
   policy is approved.**
6. Who controls DNS A/AAAA and TLS challenge, and whether a test-only
   subdomain can be created. No keys or access tokens are requested.

## 2. Target topology and trust boundary

```text
public browser
     |
     | TLS to public FQDN on VPS :443 (Caddy-managed cert)
     v
friend VPS: existing Caddy (one operator, existing sites preserved)
     |
     | Tailscale WireGuard private path, least-privilege port access
     v
Mi Max 2 (Android/Termux/Tailscale)
     +-- ASF private listener/proxy -> debian PRoot, ASF Control Suite
     +-- Drophira private listener -> 127.0.0.1:8080, drophira PRoot

future (NOT YET IMPLEMENTED):
public CLIENT portal: external identity + server-side tenant isolation
private ADMIN console: tailnet-only, MFA, separate session privileges
```

**TLS caveat:** HTTPS terminates at the friend's Caddy. The friend/VPS
administrator can, technically, inspect or log decrypted cookies, passwords
and responses. Tailscale encrypts the VPS→phone link but does not remove
this trust dependency. Do not treat this setup as end-to-end confidential
from the VPS operator. Obtain explicit owner acceptance of this model;
otherwise use a separately controlled HTTPS termination endpoint.

**Underlay choice:** a private HTTP upstream inside verified Tailscale
encryption is preferable to turning off certificate verification for a
self-signed HTTPS backend. For ASF port 1243 (currently self-signed/locally
trusted certificate), choose either a verifiable HTTPS certificate/trust
chain or a separate Tailscale-private HTTP proxy. Never add
`tls_insecure_skip_verify`. Preserve existing ASF endpoint during staging.

## 3. Tailscale connectivity decision tree

### A. Prefer reversible sharing WITHOUT moving the phone

Try sharing **only the phone machine** with the friend's *individual Tailscale
user* from the existing tailnet. Recipient's server must be an eligible,
user-owned node; **tagged** devices in another tailnet cannot use the shared
machine through the standard user share. Test on an isolated TCP port over
Tailscale before DNS or Caddy modifications.

- If successful: phone retains its existing tailnet/IP/other clients, and
  access may be revoked without a full tailnet migration.
- If blocked by tagged VPS or policy: stop. Do not assume an invitation can
  bypass this, and do not use broad grants.
- Alternative only after design approval: a separate isolated Tailscale
  connector under user's control on VPS, or planned full phone migration to
  friend's tailnet with safe local management and roll-back. The existing
  phone's Tailscale account/IP and access can change after a full migration.

Any tailnet policy additions must use **narrow grants**: the specific VPS
identity may connect **only** to chosen service ports on the phone. A public
server is not allowed general access to Termux, ADB, SSH, ASF IPC, Tailscale
admin APIs or other machines. Test both allow AND deny cases.

References:
- https://tailscale.com/docs/features/sharing
- https://tailscale.com/docs/reference/inviting-vs-sharing
- https://tailscale.com/docs/features/access-control/grants

## 4. Network exposure policy (mandatory)

| Surface | Exposure | Prerequisites |
| --- | --- | --- |
| Existing ASF Control Suite administrative UI/API | **Tailscale only** | Tested Tailscale identity, secure auth/session, separate privileged access |
| Existing Drophira administrative UI/API | **Tailscale only** | Auth/session, no raw public backend, Twitch tokens kept private |
| Future client portal | Public HTTPS **later** | Dedicated auth, MFA where appropriate, server-side per-tenant RBAC, audit, throttling |
| Future admin portal | **Tailscale only** by default | MFA, least privilege, administrative audit |
| ASF IPC, direct 8080, Drophira database, SSH, ADB/Termux | **Never publicly published** | Firewall and deny-rule acceptance |
| `/healthz` | Do not expose publicly by default | Separate internal probes only |

TLS/certificates, WSS upgrade, forwarded Host/Origin/cookies, no-store headers,
CSRF controls, per-user WebSocket auth, access rate limits and logging redaction
must all be tested before **any** internet-facing application traffic.
Reverse proxying a global-admin UI is **not** client isolation.

## 5. Phased migration & rollback

**Gate 0 — read-only inventory, owner approval**
- Take versioned, off-phone copies of the existing ASF and Drophira settings
  (protected, never included in PR/issues).
- Establish phone ADB/local management path independent of old Tailscale.
- Snapshot current Termux/Tailscale settings, running PRoot sessions,
  listen ports and current live health; never print passwords/tokens.
- Friend provides text answers above. Confirm whether DNS test names are free.
- No production change. Readiness PASS is required before the next gate.

**Gate 1 — network reachability**
- Use a narrowly scoped, revocable Tailscale share where possible.
- Confirm VPS can reach a *temporary non-sensitive probe* on phone, over
  Tailscale. Verify another non-allowed port is not reachable.
- Close probe and retain current ASF/Drophira listeners unchanged.

**Gate 2 — Caddy *staging only***
- Friend adds a *disabled* or deny-all site for the agreed temporary test
  hostname **without modifying** existing Caddy site blocks.
- Caddy config validation and certificate issuance, DNS A/AAAA verification
  and rollback are done by friend using their ordinary workflow.
- Unauthenticated requests must receive a denial; no direct upstream yet.
- Check that existing sites still work.

**Gate 3 — protected upstream**
- Add a carefully authenticated proxy on a protected host only after
  app/session, Origin/CSRF, websocket, cookies and logging review.
- Select distinct upstream ports; no collisions with current 1243/8080,
  never allow listener binding to 0.0.0.0 on the public VPS for phone ports.
- Test connection drops, phone sleep/reboot, rate limiting, auth logout,
  identity revocation and Caddy restart without service corruption.

**Gate 4 — cutover with explicit approval**
- Only after client portal authorization exists, enable public *client*
  subdomain; admin stays tailnet-only.
- Keep original rollback path for both tailnet and DNS/Caddy.
- Roll back by disabling only the new Caddy blocks and revoking the new
  Tailscale share, leaving old ASF/Drophira sessions running.

## 6. Hard stops

Stop and collect new evidence instead of deploying when:
- VPS uses tagged identity and a machine share was the only proposed route;
- missing DNS/SSL control, unknown Caddy authentication layer;
- no independent phone ADB/local recovery;
- friend is unable to restrict Caddy routes or preserve existing sites;
- insecure upstream TLS / no concrete per-client authorization;
- token or cookie appears in a proxy log, a ticket, or build output;
- service isolation/rollback test fails.

No Twitch/Steam login, farming, device authorization or production deployment
is part of this network-design document.
