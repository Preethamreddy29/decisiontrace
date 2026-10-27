# Backup and restore smoke checkpoint

**Date:** 2026-10-27
**Scope:** Stage A recovery evidence for the fictional local stack.

The host command `python tools/verify_backup_restore.py` creates a disposable source through the API, revokes it, takes a PostgreSQL custom-format backup, restores that backup into a randomly named database on the same PostgreSQL server, reruns checked migrations, and verifies the restored snapshot. It removes the temporary database and the source fixture from the primary demo database afterward.

The restored checks require the live corrected meeting version to open and return exact full-text chunks. The seeded revoked source and the API-revoked fixture must have no chunks and must be unavailable through exact-source opening and full-text retrieval. The API-created revocation must retain one audit event and one local outbox event. This verifies a same-server logical restore and migration replay; a clean-host disaster recovery drill remains a later release gate.

The [fresh-stack CI run](https://github.com/Preethamreddy29/decisiontrace/actions/runs/40434501630) passed at `b50a540`, including the backup and restore step. Local Docker was unavailable for a second run. Manual UI review and a clean local stack run remain in Stage A.
