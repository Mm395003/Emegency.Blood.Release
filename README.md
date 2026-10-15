# Emergency Blood Release

Clinical blood bank tool for compatibility tags (Zebra 2.71 × 5.13 in) and A4 Blood Issue Reports (Routine / Emergency).

## Run locally

```bash
pip install -r requirements.txt
python3 -m uvicorn server:app --host 127.0.0.1 --port 43147
```

Open http://127.0.0.1:43147/

Default admin (change after first login): `admin` / `admin123`

## Tests

```bash
pip install -r requirements.txt pytest httpx
pytest -q
```

## Docs

- `docs/AUDIT.md` — Phase 1 audit & risk register
- `docs/DEPLOYMENT.md` — deploy / rollback
- `docs/SECURITY.md` — security findings

## Constraints

Tag size, Zebra direct print pathway, A4 issue reports, and clinical compatibility entry rules are preserved. See the UI/UX modernization specification.
