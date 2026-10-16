---
name: security-review
description: 'Interactive prompt to review code for security issues in this backend.'
argument-hint: 'files-or-diff'
user-invocable: true
---

You will review code for security issues.

1. Ask for the files or diff to review.
2. Check authn/authz, validation, CSRF, mass assignment, uploads, secrets, rate limiting.
3. List findings by severity with file/line references.
4. Suggest focused tests and validation commands.
