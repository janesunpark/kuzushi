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

---

## Milestone 2 — Selecting weeks to skew, not rows

*Internal cross-reference: blueprint §12, Entries 26–27.*

**Problem**

Simulating realistic data-entry defects requires shifting some rows' apparent timestamps so they land in the wrong week — but doing this by sampling individual rows produced three distinct bugs, only found by running the code and checking actual output: a whole session's late entry should move together, not split across students; a week-selection loop was silently dropping the first selected week; and rows were being mutated before being copied, corrupting the caller's original list despite the function nominally returning a new one.

**Options considered**

1. Patch each of the three symptoms individually while still sampling at the row level.
2. Restructure around sampling *weeks* — enumerate unique `true_week_ending` values, exclude the most recent, sample `n` of the rest without replacement, then copy-and-conditionally-shift every row in one pass.

**Chosen solution**

Option 2.

This reuses the enumerate → guard → sample-unique → order idiom first named in Milestone 0, applied here at the granularity of weeks rather than timestamps.

**Trade-offs**

- Option 1 would need three separate fixes for symptoms of one root cause, and would still leave a subtler bias unaddressed: sampling from a flat row list weights each week's selection probability by how many rows it happens to contribute, so a 2-session week is twice as likely to be picked as a 1-session week. Option 2 fixes all three bugs and the weighting bias in one restructuring.
- The function still requires two linear passes over the row list (one to enumerate eligible weeks, one to copy-and-shift), not one — a cost accepted deliberately, since correctly excluding "the last eligible week" and sampling fairly from the rest both require seeing the complete set of weeks before any row can be touched. A single-pass alternative (reservoir sampling) exists for exactly this shape of problem, but it's designed for streams too large to hold in memory or whose size isn't known in advance; at 168 rows, neither condition applies, so reaching for it would be solving a problem this dataset doesn't have.

---

## Milestone 3 — Choosing what feeds `generate_synthesis_log_rows`, and coordinating it with `inject_timestamp_skew`

*Internal cross-reference: blueprint §12, Entry 28.*

**Problem**

`generate_synthesis_log_rows` needed to produce week-level synthesis ground truth (`week_ending`, `num_sessions_reported`) for later reconciliation testing. Two decisions were entangled here: what representation should feed this function, and how it relates to the already-existing `inject_timestamp_skew` step.

On the first: `combine_schedules` already produces week-structured records with true session counts attached; `derive_session_rows` instead flattens that same information into individual observation-level rows. Deriving synthesis rows from the flattened row-level output would mean re-aggregating rows back into weekly counts — effectively reimplementing a simplified version of the real Silver-layer reconciliation logic (`expected_rows = num_sessions_reported × 2`, compared against actual row counts) inside the fixture generator itself, before the pipeline being tested even exists.

On the second: once `generate_synthesis_log_rows` and `inject_timestamp_skew` were both built independently on top of `combined_schedule`, cross-checking them revealed a real gap — one of two deliberately-skewed weeks fell before synthesis practice began in the simulated timeline, producing a week with no corresponding synthesis note to reconcile against at all, silently wasting half the planted test cases.

**Options considered**

- Representation source: (a) derive synthesis rows from `derive_session_rows`'s flattened output, re-aggregating row counts back up to the week level; (b) derive synthesis rows directly from `combined_schedule`, which already carries week-level ground truth.
- Skew/coverage coordination: (a) keep `generate_synthesis_log_rows` and `inject_timestamp_skew` independent and accept that some skewed weeks may fall outside synthesis coverage; (b) have `inject_timestamp_skew` select only from weeks that `generate_synthesis_log_rows` actually produced an entry for, and re-parameterize the synthesis-note start as `n_skipped_weeks: int` instead of a hardcoded calendar date.

**Chosen solution**

(b) for both.

**Trade-offs**

- Deriving synthesis rows from flattened session rows (representation option a) would work, but blurs a line worth keeping clean: the generator's job is to produce ground truth and deliberately corrupted derived views of it, not to pre-validate itself. If the fixture generator re-implements even a simplified version of the reconciliation logic the real pipeline is supposed to be tested against, a bug shared between the two would be invisible — the fixture and the system under test would be grading each other's homework instead of one acting as an independent check on the other. Deriving directly from `combined_schedule` (option b) keeps the two projections — observation-level rows and week-level synthesis summaries — as independent views of the same underlying truth, joined explicitly later, rather than one being derived from a flattened form of the other.
- This mirrors a decision already made in the real production schema (blueprint §1): `fact_session` and `fact_weekly_synthesis` are treated as two different fact tables at genuinely different grains, connected by an explicit grain-mismatch join, not collapsed into a single natural-key merge. The generator arriving at the same shape independently is a good sign the underlying principle — don't force one grain to be derived from another when both are legitimate views of the same reality — is being applied consistently, not just remembered once.
- Coordinating skew selection with synthesis coverage (option b) required threading `synthesis_log_rows` into `inject_timestamp_skew` as an input and reordering the pipeline so synthesis rows are generated before skew is injected — more coupling between the two functions than treating them independently (option a). But independence was shown, on a real seed, to silently produce non-functional test cases: a skewed week with no synthesis note to reconcile against is indistinguishable from any other uncovered week, defeating the purpose of planting it. Re-verified directly after the fix: both skewed weeks are now confirmed present in the synthesis log with matching true counts.
- Reparameterizing the synthesis-note start as `n_skipped_weeks: int` instead of a calendar date gives `n=0` a clean, portable meaning ("no gap") that will still hold for a future observation cycle with no pre-synthesis gap at all, without needing to recompute a date every time. One residual imprecision, not a bug: `n_skipped_weeks` counts raw positions in `combined_schedule`, which includes Jiu-Jitsu-only weeks alongside academic ones, so "skip N" and "skip N *eligible* weeks" aren't quite identical — close enough for this generator's realism standard, but worth knowing if a future use ever needs an exact row-count target.

---

## Milestone 4 — The one function breaking `rng` convention, found only by integration testing

*Internal cross-reference: blueprint §13, Entry 36.*

**Problem**

Every function in the generator accepts `rng: np.random.Generator` directly, threading one continuously-advancing stream through the whole pipeline — except `combine_schedules`, which took a raw `seed: int` and built its own internal generator from scratch, with no way to supply or retrieve the shared stream. This was invisible as long as `combine_schedules` was tested only in isolation. A hand-built integration script composing the full pipeline — schedule generation through every enrichment step, the first genuine end-to-end run of the whole thing — surfaced it directly: the outer `rng` created for the enrichment steps produced, as its first draw after `combine_schedules` returned, a value identical to a completely fresh generator's first draw — proof `combine_schedules` had never touched the shared stream at all.

**Options considered**

1. Leave `combine_schedules` taking a raw seed, treating schedule generation and row enrichment as two separately-reproducible phases rather than one continuous pipeline.
2. Change its signature to accept `rng` directly, matching every other function, with the caller responsible for creating one generator from a single top-level seed and threading it through the entire pipeline, `combine_schedules` included.

**Chosen solution**

Option 2.

**Trade-offs**

- Option 1 would have been a permanent, quiet inconsistency — the one function in the whole file not following its own established convention, discoverable only by explicitly checking draw-for-draw equality against a fresh generator, which is a non-obvious thing to think to check in the first place. Option 2 is a small, mechanical signature change, but was necessary for the "one seed reproduces the entire synthetic dataset" property to actually hold end-to-end, rather than being true only within each phase separately. Re-verified directly after the fix: the draw taken immediately after `combine_schedules` returns no longer matches a fresh generator's first draw, and the complete pipeline reproduces identically under a matching seed and diverges under a different one.
- The lesson here is sharper than "run the code, don't just read it" (Milestones 1 and 2's theme): every individual function was already correct in isolation — unit-level testing of `combine_schedules` alone would never have surfaced this, because the defect only exists in how functions compose together. Only a genuine integration test (here, a plain inspection script rather than a formal one) could catch it. A system where every component follows a convention except the one composing them is a specific, findable smell — and it's specifically invisible to testing components one at a time.

*A separate, unrelated fix landed in the same pass, worth noting for completeness but not part of the decision above: `assign_deprecated_ratings`'s `cutoff_week` argument was off by one week, which would have forced an entire week to always-null against evidence the real data had a genuine chance of populating it. Re-verified after the fix.*

---

## Milestone 5 — Splitting `timestamp` into ground truth and apparent value, before skew existed

*Internal cross-reference: blueprint §12, Entry 26. First instance of the anchor-field idiom named in Milestone 7.*

**Problem**

`derive_session_rows`'s output has one timestamp field, and at that stage it's ground truth — but the very next step deliberately corrupts it for some rows to simulate retrospective entry. Once that happens, a row's apparent timestamp can no longer be trusted to indicate its true week.

**Options considered**

1. Keep a single `timestamp` field and let downstream code re-derive week membership from it as needed, after corruption has already happened.
2. Carry `true_week_ending` alongside `timestamp` from the moment rows are created, explicitly named as privileged, generator-only ground truth that must never appear in the eventual CSV output.

**Chosen solution**

Option 2.

**Trade-offs**

- Option 1 is the field shape a real Bronze/Silver pipeline actually has to work with — deliberately not what this intermediate generator representation should mimic, since the whole point of building skew is to have an answer key to check reconciliation logic against later. Option 2 preserves that answer key for free, at the moment it's cheapest to keep, rather than reconstructing "which week did this really belong to" after the only trustworthy signal has been intentionally destroyed for some rows.
- This is the first instance of what later became a named, reused idiom in this project — see Milestone 7, where the same reasoning paid off a second and third time, including against a threat this entry never anticipated.

---

## Milestone 6 — Reordering the pipeline to derive → enrich → inject, with `session_category` as the stable discriminator

*Internal cross-reference: blueprint §13, Entry 32.*

**Problem**

`observation_context` needed to become real category strings, but `inject_timestamp_skew` and the enrichment functions running after it needed a stable way to identify "this is an Enrichment row" regardless of what `observation_context` had since been rewritten to. The original build order — skew before any enrichment — had no actual technical justification; it was simply the order the functions happened to get built in.

**Options considered**

1. Keep the original order, requiring every future enrichment function to avoid touching or depending on anything skew already changed.
2. Reorder into a genuine three-phase pipeline — derive truth, enrich truth, inject defect — introducing `session_category` as a field set once and never modified again, with every downstream function keying off it instead of the mutable `observation_context`.

**Chosen solution**

Option 2.

**Trade-offs**

- Option 1 was checked and found to have no correctness dependency actually requiring it. Option 2 costs nothing to adopt and buys a strictly simpler mental model: skew becomes the true last step, the only function permitted to touch `timestamp` after everything else is already correct. `session_category` mirrors the exact reasoning behind Milestone 5's `true_week_ending` split.
- Verified the switch was necessary, not cosmetic: re-running the full reordered pipeline confirmed the skew step still correctly matches the right rows after the discriminator field had already been overwritten — had it not been switched, skew would have silently matched zero rows.

---

## Milestone 7 — Anchor fields, and a granularity mismatch that took several passes to diagnose

*Internal cross-reference: blueprint §13, Entry 37. Builds on Milestones 5 and 6, the two earlier anchor-field instances.*

**Problem**

A cutover comparison — checking a raw session date against a fixed reference date — worked, but the reason it worked was genuinely non-obvious and took several wrong turns to diagnose correctly. Cutoff values in this project are always constructed as week-ending values, which are always Sundays. The synthetic schedule's spring-semester sessions only ever fall on two specific non-Sunday weekdays. A weekday date can never satisfy "on or after this Sunday" within its own week — the earliest date that can is the following week's version of that same weekday. This silently pushed the effective transition one full week later than intended, with no error anywhere to reveal it. The value eventually found to "work" only did so because it happened to be reachable within its own week by the same meeting-day pattern — sidestepping the mismatch rather than resolving it.

**Options considered**

1. Leave the fix as a direct comparison against that specific weekday value, now confirmed to produce the desired result.
2. Refactor to compare against the anchor field (`true_week_ending`) instead of the more granular raw value — verified, after correcting an earlier wrong equivalence, to produce identical output to option 1.

**Chosen solution**

Option 2.

**Trade-offs**

- Option 1 works today, but its correctness depends on an unstated fact invisible at the call site — that the chosen value happens to be reachable within its own week by the specific meeting pattern in use — which would silently stop holding against a different meeting pattern or a differently-built cutoff. Option 2 costs nothing and states the actual intent directly, independent of which weekdays sessions happen to fall on.
- General lesson: a week-level cutoff compared against day-level data is safe only when every day-level value is guaranteed to reach the cutoff within its own week — easy to lose silently when the cutoff and the data being compared are built from different conventions. When a fix works for a reason that takes several rounds of tracing to explain, that's itself a signal the implementation is more fragile than it looks, independent of whether today's value happens to be correct.
- This is the third time this exact shape of decision has paid off (see Milestones 5 and 6, both defending against deliberate data corruption from other generator functions). This occurrence is the most interesting of the three precisely because it defended against nothing either earlier instance was built for — nothing here was corrupted; the raw field simply carried more resolution than the comparison needed. An anchor field's value isn't limited to the one threat it was built to defend against — it extends to an entire class of grain-mismatch fragilities, including ones nobody anticipated when it was first built.
