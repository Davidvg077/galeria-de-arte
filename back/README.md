# Backend

The backend is organized under this folder:

- `api-gateway/` contains the Express gateway, routes, configuration, and
  middleware.
- `services/` contains the FastAPI microservices, shared helpers, and service
  Dockerfiles.
- `tests/` contains backend unit tests.
- `legacy/` contains the retired HTML server and static site.
- `deploy/`, `docs/`, and `scripts/` contain backend deployment resources and
  developer tooling.
- `uploads/` contains artwork files used by the retired HTML server.

Backend package manifests, deployment configuration, documentation, scripts,
and test data are also contained here. Run backend Node commands from this
folder. From the repository root, start Docker Compose with:

```powershell
docker compose -f back/compose.yaml --env-file back/.env.docker up --build
```

The GitHub workflow definitions remain under the repository-root `.github`
directory because GitHub Actions only discovers workflows there. The Render
Blueprint is `back/render.yaml`; configure that path in the Render dashboard.
