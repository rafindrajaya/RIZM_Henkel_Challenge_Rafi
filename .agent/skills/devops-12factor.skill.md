---
name: devops-12factor
description: Ensures the application adheres to the Twelve-Factor App methodology for modern DevOps and cloud deployment.
---

# DevOps & Twelve-Factor App Skill

Evaluate and construct the application infrastructure and codebase against the 12-factor methodology to ensure it is robust, scalable, and easy to deploy.

## Core Principles
1. **Codebase**: One codebase tracked in version control, many deploys. Never duplicate codebases for staging/prod.
2. **Dependencies**: Explicitly declare and isolate dependencies (`pyproject.toml`, `requirements.txt`). Never rely on implicit system-wide packages.
3. **Config**: Store configuration in the environment (`.env`). NEVER hardcode secrets, API keys, or environment-specific variables in the code. Use tools like `pydantic-settings`.
4. **Backing Services**: Treat backing services (databases, message queues like Redis/RabbitMQ) as attached resources. Swap them easily via config changes without altering code.
5. **Build, Release, Run**: Strictly separate build and run stages.
6. **Processes**: Execute the app as one or more stateless processes. Store persistent state (like training weights or twin history) in a backing service.
7. **Port Binding**: Export services via port binding (e.g., a FastAPI web server binds to a port and listens to requests).
8. **Concurrency**: Scale out via the process model (add more workers/instances).
9. **Disposability**: Maximize robustness with fast startup and graceful shutdown (handle SIGTERM appropriately to save state).
10. **Dev/Prod Parity**: Keep development, staging, and production environments as similar as possible.
11. **Logs**: Treat logs as event streams. Write to `stdout`/`stderr` and let the execution environment manage routing. Use structured logging (JSON).
12. **Admin Processes**: Run admin/management tasks (like database migrations) as one-off processes in an identical environment.
