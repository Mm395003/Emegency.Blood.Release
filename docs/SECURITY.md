# Security findings & remediation

| ID | Finding | Status / remediation |
|---|---|---|
| S1 | Default admin password seeded | Change on first login; set `BLOOD_ADMIN_PASSWORD` |
| S2 | Default token secret if env unset | Set `BLOOD_TOKEN_SECRET` in production |
| S3 | JSON file DB not multi-instance safe | Documented; durable DB requires approval |
| S4 | Users API admin-gated server-side | OK — keep UI gate as convenience only |
| S5 | Audit user field uses Technologist ID text | Prefer signed-in username in future enhancement |
| S6 | No rate limit on `/api/login` | Add reverse-proxy rate limit in production |
| S7 | Synthetic data only in tests | Do not use real PHI in dev |

Password hashing: PBKDF2-SHA256. Sessions: HMAC-signed tokens (`v1.`).
