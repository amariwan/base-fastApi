# Core Users

`core_users` supplies the optional local identity model used when a service
owns users instead of relying only on external JWT claims. Identity is email
first: addresses are validated and normalized before lookup, and passwords are
stored as versioned scrypt hashes.

Use `DefaultUserManager` or inject `UserManagerDep`. The manager deliberately
calls `flush()` rather than `commit()`; the application use case owns the
transaction. Subclass `UserManager` to add password policy or lifecycle hooks
without changing the ORM model.

The `20261016_01` Alembic revision creates `core_users`. Existing deployments
must apply it explicitly through their normal migration workflow.
