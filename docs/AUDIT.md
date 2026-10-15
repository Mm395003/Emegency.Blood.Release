# Phase 1 — Audit & Risk Register

**Project:** Emergency Blood Release  
**Stack:** Single-page `index.html` + FastAPI `server.py` + Windows `PrintAgent.cs`  
**Date:** 2026-10-15

## Architecture

| Area | Current state |
|---|---|
| Framework | Static SPA in one HTML file; no React/Vue router |
| Backend | FastAPI JSON file store under `data/` |
| Auth | Signed HMAC tokens + PBKDF2 passwords; admin UI gated client-side, API gated with `require_admin` |
| Persistence | `users.json`, `history.json`, `audit.json` (local disk; ephemeral on many serverless hosts) |
| Print agent | C# TCP listener; UI posts bitmap JSON to `/print/tag-bitmap` |
| Tests | None previously |

## Major features (current behavior)

1. **Login / users** — Sign-in overlay; admin can add users and change passwords; history/audit sync after login.
2. **New release / New Tag** — Patient fields, release type, requested unit count/component, per-unit entry, issue unit list, generate tags.
3. **Tag preview** — Renders 2.71 × 5.13 in compatibility tags; Zebra direct print per tag or batch.
4. **Issue report** — A4 portrait report; Routine vs Emergency (emergency declaration block).
5. **Print Center** — Separate pathways for tag (Zebra) vs issue report (browser A4).
6. **History / Audit / Dashboard** — Local + server sync; search/filter; CSV export; aggregate counts from stored records.
7. **Print Agent** — Windows-only; targets `ZDesigner GK420t`.

## Critical invariants (must preserve)

- Tag size **2.71 × 5.13 in**
- Issue report **A4 portrait**
- Tag print vs A4 report print are independent
- Routine vs Emergency report distinction
- No invented clinical compatibility rules from barcodes
- Multi-unit entry, patient–unit association, history, audit, dashboard, user admin

## Bugs / gaps found

| ID | Severity | Finding |
|---|---|---|
| R1 | High | JSON file storage is not durable on multi-instance/serverless hosts (history/users may reset). |
| R2 | High | Default admin credentials are seeded (`admin` / `admin123`) — must change in production. |
| R3 | Medium | Default `BLOOD_TOKEN_SECRET` is a fixed dev string if env unset. |
| R4 | Medium | Print Agent source listens on **8765**; UI default URL is **8770** — mismatch risk. |
| R5 | Medium | Client can hide Users nav, but some actions rely on tech ID only (not signed-in username) in audit rows. |
| R6 | Medium | No automated regression tests existed before this modernization. |
| R7 | Low | Branding previously used “Emergency Blood Release Protocol” (spec forbids “Protocol”). |
| R8 | Low | New Release was one long form without step progress or review gate. |
| R9 | Low | Print attempt audited as `TAG_PRINT` / report print; verified printer ACK beyond HTTP `ok` is limited. |

## Dependencies

- Python: FastAPI, Uvicorn, Pydantic
- Browser: modern Chromium/Firefox/Safari
- Windows + .NET for Print Agent + Zebra driver

## Security notes (Phase 6 preview)

- Passwords hashed with PBKDF2; tokens HMAC-signed.
- Enforce admin on API for user management (already).
- Production needs: strong `BLOOD_TOKEN_SECRET`, rotated admin password, HTTPS, durable DB if multi-instance.
- Do not deploy architecture changes without approval (per spec).
