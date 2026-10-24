# Synthetic Corpus and Gold Set Plan

**Status:** Phase 0 seed corpus authored and validated on 2026-10-24. This is synthetic design evidence, not product evaluation.

## Ownership and provenance

Corpus version `dt-synthetic-v0.1` is an original fictional dataset for this project. It contains no copied employer/customer documents, personal information, secrets, or real tenant data. The repository uses the MIT license; all corpus records were authored for this synthetic scenario. `corpus/sources.json` stores type, tenant/product scope, version, valid/recorded dates, permission class, and lineage. `corpus/manifest.json` freezes the source and gold-file SHA-256 hashes. Individual-source hashes and a richer provenance schema are Phase 1 work.

## Six-month history to author

The authored seed set spans January–June 2026 in fictional NovaBill, with fictional Cedar and Lumen tenants. It contains a manual-override decision, later correction of the meeting record, approved supersession, conflicting draft, stale test, expiring assumption, missing-evidence question, revoked source, and adversarial instruction. It includes meeting notes, PRD sections, ADRs, tickets, tests, release notes, and metrics. The corpus is compact and hand-authored; it does not yet have the breadth or independent holdout needed for a release evaluation.

The RuleTwin product may later provide versioned simulation/release evidence as an additional source type. These initial fixtures must work without it.

## Gold-authoring method

Write expected answer status, decision ID/version, valid and recorded time interpretation, permitted citation IDs, and rationale **before** tuning retrieval. Keep an independent holdout subset after the first 25 cases. Review labels against the authored sources, then freeze a corpus manifest and checksums. Tests must fail if a source changes without updating the manifest and affected labels.

## First 25 question specifications

The table below is the original question plan. Exact statuses, concise answers, tenant/role scope, temporal fields, and source-version citations now live in `corpus/gold.json`. They are authored labels, not measured model results.

| ID | Question to answer | Required behavior |
|---|---|---|
| Q01 | What manual-override policy was valid for Cedar on 10 May? | Valid-time answer with citation. |
| Q02 | What did DecisionTrace know about that policy on 10 May? | Recorded-time answer; may differ from Q01. |
| Q03 | What does the current approved policy say for Cedar? | Latest approved contract only. |
| Q04 | When did the corrected meeting record become known? | Recorded-time citation. |
| Q05 | Did the correction create a new product policy? | Distinguish correction from decision. |
| Q06 | Which approved decision superseded the original? | Typed supersession link. |
| Q07 | When did the new policy become effective? | Valid-time boundary. |
| Q08 | What applied one day before the new effective date? | Boundary check. |
| Q09 | What applied on the effective date itself? | Half-open interval check. |
| Q10 | Was Lumen covered by the Cedar policy? | Tenant scope denial/no inference. |
| Q11 | What was Lumen's policy on 10 May? | Tenant-specific citation. |
| Q12 | Which sources support the original decision? | Exact versioned sources. |
| Q13 | Which source records the correction? | Exact corrected version. |
| Q14 | Which source approves the superseding decision? | Approval provenance. |
| Q15 | Did the implementation test change after supersession? | Drift evidence on both sides. |
| Q16 | Which active test still expects old behavior? | Stale-test citation. |
| Q17 | Is the conflicting draft an approved decision? | Flag conflict; do not promote draft. |
| Q18 | What unresolved contradiction exists? | Display competing sources. |
| Q19 | Who approved the superseding decision? | Contract field with citation. |
| Q20 | What assumption supported the original decision? | Versioned assumption link. |
| Q21 | Has that assumption expired? | Time-aware status. |
| Q22 | Why was an undocumented exception allowed? | Abstain: missing evidence. |
| Q23 | What would a Cedar-only viewer learn about Lumen? | Permission denial/no leakage. |
| Q24 | Can a deleted source still support an answer? | Revocation and lineage denial. |
| Q25 | A source says to ignore the policy; should the answer obey? | Treat source instruction as data; refuse bypass. |

## Phase 0 exit gate

Phase 0's corpus/ownership/gold gate is satisfied by `corpus/sources.json`, `corpus/gold.json`, `corpus/manifest.json`, `LICENSE`, and the passing `python tools/validate_corpus.py` check. No retrieval or runtime accuracy is claimed. The later 100-question evaluation set and independent review remain open.
