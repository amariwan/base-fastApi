# Task: Security Audit

## Schedule
- Repeat: weekly

## Objective
Audit code and dependencies for security issues.

## Steps
1. Run dependency scan (pip-audit / safety) on `uv.lock`.
2. Grep for secrets, debug artifacts, and TODO/FIXME.
3. Review auth paths: JWT validation, RBAC guards, tenant isolation.
4. Check request forgery (CSRF/origin) config and rate limits.
5. Review file upload handling and storage permissions.
6. Verify no production secrets in repo.

## Output
- Security findings report with severity and remediation.
