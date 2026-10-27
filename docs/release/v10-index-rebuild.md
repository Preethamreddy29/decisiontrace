# Exact chunk-index rebuild checkpoint

**Date:** 2026-10-27
**Scope:** Stage B index maintenance for the fictional local stack.

`tools/rebuild_index.py` compares every stored chunk with the current deterministic chunker and its checksummed source version. It reports missing or mismatched chunks and stale chunks for revoked versions. The default is read-only; `--apply` repairs only mismatches and removes revoked chunks. `--tenant cedar` can limit the operation to one known tenant. Each tenant is processed under the same evidence lock used by queries and protected mutations; seed loading now takes those locks too.

From the repository root, after the stack starts:

```powershell
docker compose --env-file .env.example exec -T api python -m tools.rebuild_index
docker compose --env-file .env.example exec -T api python -m tools.rebuild_index --apply
```

The live drill removes one authorized chunk and inserts a stale chunk for a revoked seed version. It checks that dry-run detects both without changing them, apply restores the live exact passage and purges the revoked chunk, and a second dry-run reports no drift. The restored authorized search result is checked. This repairs the full-text chunk index only; vector embeddings and compatible vector-index rebuilding remain Stage B work.

The [fresh-stack CI run](https://github.com/Preethamreddy29/decisiontrace/actions/runs/40436054619) passed at `24ca3b0`, including the rebuild drill, seed-lock change, and restore smoke. Local Docker remains unavailable for a second run.
