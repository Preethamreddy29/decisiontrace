# Temporal and Trust Model — Draft

## Terms

- **Valid time:** when a claim or decision applies in the fictional product world.
- **Recorded time:** when DecisionTrace first held a particular source or corrected record. Never backdate this to the source's claimed event time.
- **Correction:** a new recorded version repairs an inaccurate account of an earlier event. It preserves the original record and does not by itself authorize a new product behavior.
- **Supersession:** a later approved decision replaces a prior decision for an explicit scope and effective interval.
- **Contradiction:** incompatible claims overlap in scope and time without an approved resolution. It must be shown, not silently ranked away.
- **Decision contract:** a reviewed, versioned object with owner, approver, tenant/product scope, status, effective interval, evidence IDs, assumptions, and lineage.

## Interval and history rules

Use half-open valid intervals `[start, end)`. The first synthetic corpus uses ISO calendar dates interpreted at UTC day boundaries; recorded events use UTC instants. An imported timestamp must carry an explicit offset and be normalized before comparison. Later tenant-local effective dates require a versioned timezone policy before use. Store recorded intervals independently and append versions rather than overwriting them. A query must state whether its date constrains valid time, recorded time, or both. An ambiguous natural-language date prompts clarification or returns a labeled interpretation; it must not silently become a current-state query.

Every source version and decision version receives a stable ID and content checksum. An answer cites the exact version used. Changing a source, permission, decision status, or index version invalidates dependent answer/cache entries. Deletion or permission revocation blocks retrieval immediately even if physical cleanup continues asynchronously.

## Authorization sequence

1. Authenticate and derive tenant, role, and source scope on the server.
2. Apply permission and temporal predicates before retrieval candidates leave storage.
3. Build context only from authorized versions; mark source text as untrusted data.
4. Produce structured answer claims referencing candidate citation IDs.
5. Resolve citations server-side and verify existence, permission, scope, time, and support.
6. Remove unsupported claims or abstain. Record the version tuple and audit outcome.

No client-supplied tenant ID alone grants access. No direct access to RuleTwin's database is allowed. A future RuleTwin adapter accepts versioned evidence through a documented contract and performs the same provenance and permission checks as other sources.

## Design work still required

The conceptual ERD and state machines are in `data-model.md`, and planned adversarial checks are in `../security/threat-to-test.md`. The Phase 1 design gate is recorded in `../release/phase1-design-gate.md`; runtime controls and the historical answer workflow still require implementation evidence.
