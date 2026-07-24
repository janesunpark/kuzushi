# Engineering Log

This log records the engineering decisions made while building Kuzushi's data pipeline — the problems considered, the options weighed, and the trade-offs accepted. It is separate from the project's private planning notes: entries here are added only once a decision is settled, and are written for a reader outside the project (recruiters, portfolio reviewers), not as a live scratchpad.

For the research methodology and data ethics behind the underlying observations, see [`docs/methodology.md`](docs/methodology.md) and [`docs/data_ethics.md`](docs/data_ethics.md). This log covers the *engineering* side only: how data is generated, ingested, cleaned, and structured.

**A note on how this document is written.** Consistent with the AI-assistance disclosure in `methodology.md`, portions of this log are drafted and organized with AI assistance based on decisions made, tested, and reviewed by the author. Every entry reflects a decision that was actually made and, where a verification claim is stated (e.g. "0 duplicates across 15 seeds"), actually run — the drafting tool did not originate the engineering judgment, only the write-up.

---

## Milestone 0 — Naming the sampling idiom in `synthetic_generator.py`

**Problem**

Several functions in the synthetic schedule generator need to draw a random, duplicate-free subset of timestamps from a bounded pool (e.g. "pick 2 unique Jiu-Jitsu class slots out of the valid slots this week"), then return results in chronological order. Before writing new pipeline code, it was worth identifying whether this need had already been solved consistently, or was being reinvented differently in different places.

**Options considered**

1. Treat each function's implementation as unrelated one-off logic and move on.
2. Recognize the shared shape — enumerate a candidate pool, guard against an impossible request, sample without replacement, restore chronological order — and document it explicitly before building new code on top of it.

**Chosen solution**

Option 2. The four-stage shape (**enumerate → guard → sample unique → order**) appears in `generate_s03_observations` in full, and in partial form in `_remove_random_off_weeks`, `generate_academic_schedule`, `generate_jiu_jitsu_observations`, and `combine_schedules`. Naming it now gives the upcoming ingestion pipeline a known, tested idiom to reuse deliberately rather than reinvent.

This entry distills decisions that were made, tested, and verified in the project's private engineering blueprint (internal document, not published) — it doesn't re-derive them independently. Internal cross-reference for traceability: blueprint §7 Entry 18, §11 Entries 21 and 24.

**Trade-offs**

- The three existing call sites use three *different* guardrail philosophies when a request can't be satisfied: `raise` (fail loudly — `generate_s03_observations`, `_remove_random_off_weeks`), silent `continue`/skip (`generate_academic_schedule`), and silent `min()` clamping (also `generate_academic_schedule`, capping `num_sessions` to `len(candidate_dates)`). These aren't inconsistencies to fix — they reflect genuinely different domain semantics (an impossible sample request is a bug; a week with zero valid meeting days is a normal calendar fact). Any future shared helper would need an explicit failure-policy parameter to keep these distinct.
- Considered extracting a shared `_sample_unique(pool, k, rng, on_shortage=...)` helper now. Decided against it for this file: it's a one-time synthetic-fixture generator, read far more than it's changed, and the abstraction cost isn't earned yet by three call sites with different failure policies. Revisit this once the same need appears in the production ingestion pipeline (Silver/Gold layers), where one tested helper with an explicit, documented failure policy will be worth the extra layer.
- `generate_s03_observations` samples **indices** (`rng.choice(len(pool), size=k, replace=False)`) rather than sampling the `datetime` objects directly. This is the safer general pattern — `numpy`'s `choice` is built for clean 1-D numeric arrays, and non-numeric objects like `datetime` risk being coerced into an `object`-dtype array, which works but forfeits some of numpy's guarantees. Sampling indices and indexing back into the original list avoids the ambiguity entirely.
- This wasn't the first approach tried. An earlier version used a retry/rejection-sampling loop — draw a timestamp, track used `(date, time)` pairs in a set, re-draw on collision — and it measured clean (0 exact duplicates across 15 seeds). It was replaced anyway: its safety depended on an *unenforced* invariant (the maximum retries ever needed staying below the number of unique combinations available), which only held because of the specific constants in use at the time. Changing those constants later could have silently reintroduced a hang with no error at all. Sampling without replacement removes the risk *structurally* — duplicates can't occur by construction, and the shortage guard fails loudly and immediately if the invariant is ever actually violated, rather than freezing silently. This is the strongest reason to prefer `choice(replace=False)` over a retry loop: not that it's shorter, but that it converts a latent, silent failure mode into an explicit, structural guarantee.
- `_remove_random_off_weeks` achieves the same "no duplicates" guarantee via `shuffle` + slice instead of `choice(replace=False)`, and skips the final sort altogether because it filters the *original* ordered sequence rather than rebuilding a new one from sampled pieces. The alternative — selecting entries via value-equality membership (`week not in off_weeks`) — was considered and rejected: it depends on an unstated invariant that no two schedule entries are ever equal by value, which currently holds only by coincidence (`week_ending` happens to be unique) and isn't enforced anywhere. A constructed test case with duplicate-valued entries showed the value-equality approach silently removing *more* than the requested count. Filtering by index position can't over-remove regardless of whether values repeat.
- The enumerate stage isn't just a defensive nicety — it's been empirically load-bearing. `combine_schedules` builds its candidate universe as the *union* of week-endings from two independently-generated schedules, rather than iterating one schedule and looking for matches in the other. Across 50 simulated seeds, roughly 41% of randomly-selected academic off-weeks still had an independently-scheduled secondary observation land in them — meaning the simpler "iterate one schedule's own entries" approach would have silently dropped a real, frequent case, not a rare edge condition.

---

## Milestone 1 — Bronze loader: dtype strategy, snapshot immutability, and atomicity

*Internal cross-reference: blueprint §9, Entries 9–13.*

**Problem**

The Bronze layer of the pipeline is meant to be an immutable, as-close-to-raw copy of the source CSVs — but "raw" is not automatic. Four separate risks surfaced while building the loader: (1) `pandas.read_csv`'s default type inference is itself a silent cleaning decision, before Bronze is supposed to interpret anything; (2) a save/reload round trip through the wrong file format can silently undo any type discipline applied on load; (3) a snapshot that can be overwritten isn't actually immutable, it just usually doesn't collide; (4) loading two related source files (the session log and the synthesis log) creates a window where one can succeed and the other fail, leaving a Bronze snapshot with no matching sibling from the same run.

**Options considered**

- Dtype on read: (a) let pandas infer as usual and cast explicitly later in Silver; (b) force every column to `object` on read; (c) force every column to pandas' nullable `"string"` extension dtype on read.
- Snapshot format: (a) CSV output keyed to the source filename; (b) Parquet output keyed to `dataset_name` plus a microsecond-precision `ingestion_ts`.
- Immutability: (a) trust that a fresh timestamp on every run makes collisions practically impossible; (b) add an explicit `if output_path.exists(): raise FileExistsError(...)` guard before every write.
- Multi-file atomicity: (a) load-and-save each dataset in a single pass, accepting whatever partial disk state results from a mid-loop failure; (b) load all datasets into memory first, only begin writing once every load has succeeded, and roll back any snapshots already written in the same run if a later save fails.

**Chosen solution**

(c), (b), (b), and (b), respectively.

**Trade-offs**

- Letting pandas infer dtypes on read (option a for dtype) is the default and requires no code, but it *is* a cleaning decision — a Likert rating showing up as `3.0` instead of `"3"` has already been interpreted, before Bronze was supposed to touch it. Forcing `object` dtype is more universally compatible with older libraries, but nullable `"string"` was chosen instead because it's more semantically explicit (missing values become real `pd.NA`, not an ambiguous mix of `NaN` and empty strings) — verified end-to-end by round-tripping a Likert value through a Parquet save/reload and confirming it came back as `"3"` with dtype `string`, not re-inferred as numeric.
- CSV snapshot output is the more familiar default but is purely textual: it cannot distinguish `"3"` from `3` on reload, which would silently undo the dtype decision the moment anyone re-read a snapshot. Parquet carries an actual schema and was verified to preserve the `string` dtype on reload. Keying the filename to `dataset_name` rather than the source file's name reflects that snapshots are organized by *what dataset this is*, not by an incidental source filename that could change.
- Trusting a fresh timestamp per run (immutability option a) holds for the intended call pattern (loader → saver, every time), but leaves a silent gap if the save function is ever called twice on an already-loaded DataFrame — a real, tested scenario where it would silently overwrite. The explicit existence-check guard costs one cheap check per save and turns a possible silent data-loss bug into a loud, immediate, descriptive error instead.
- Single-pass load-and-save (atomicity option a) is simpler code, but was verified to leave an orphaned single-dataset snapshot on disk when a second file's load or save failed partway through — a state with no clean interpretation for downstream reconciliation logic expecting a matched pair. Load-everything-then-save-everything, with rollback on partial failure, was verified across all three relevant cases (full success, load-phase failure, save-phase failure after partial success) to guarantee the loader either fully succeeds or leaves no observable trace — which is what makes it safe to re-run after a failure without manual disk cleanup.

