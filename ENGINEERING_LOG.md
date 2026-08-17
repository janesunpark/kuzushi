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

---

## Milestone 8 — Asymmetric, empirically-calibrated cadence per learner

*Internal cross-reference: blueprint §11, Entry 19.*

**Problem**

An initial single shared cadence for both learners' Jiu-Jitsu observations produced a symmetric ~10/10 split, but the real session log shows a meaningfully asymmetric split between the two learners.

**Options considered**

1. Accept a symmetric model as a reasonable simplification.
2. Give each learner independent cadence parameters, calibrated to approximate the real per-learner counts.

**Chosen solution**

Option 2.

**Trade-offs**

- Calibration required checking distributions, not single runs — an early parameter choice that looked close on one seed turned out, across eight seeds, to average noticeably short of the real target, since a single favorable draw isn't the same evidence as a correct average. The final parameters were accepted once multi-seed testing showed both learners consistently landing near their real historical counts rather than matching by chance on one seed.
- A deliberate stopping point was set here rather than continuing to tighten toward an exact historical match — the generator's job is to produce plausible, realistically asymmetric irregularity, not to reproduce one specific year's exact totals, and further precision past this point would cost real effort for no benefit to the generator's actual purpose.
- This is the earliest instance in the project of a recurring calibration discipline: distrust a single seed's apparent success, and set an explicit, principled stopping point for "close enough" rather than let calibration effort expand without bound.

---

## Milestone 9 — Discrete two-phase distribution modeling, and a per-meeting pairing requirement

*Internal cross-reference: blueprint §14, Entry 41.*

**Problem**

`Duration in Minutes` looked at first like a candidate for the same continuous-trend treatment as `Number of Pages Completed`, but the real values are discrete buckets (35/45/60/75/80/90/120 minutes), and the real shape change over the season is a genuine distributional shift — some values disappearing entirely, others becoming dominant — not a smooth drift a single interpolation formula could represent.

**Options considered**

1. Force a continuous trend formula onto the discrete values anyway, accepting some inaccuracy.
2. Two discrete weighted distributions (early/late), split at the real boundary week where the shape genuinely changes.

**Chosen solution**

Option 2, plus a same-meeting pairing requirement (both students' rows for one Enrichment session share the identical drawn value) discovered by checking per-student distributions and finding them identical at every phase — unlike every other per-student field built so far.

**Trade-offs**

- Three bugs surfaced across separate rounds, all in this one function: a missing `cutoff_week` check for Jiu-Jitsu rows, a phase-boundary comparison using the wrong direction (confirmed by finding early-only values appearing exactly at the boundary week across 50 seeds), and — after fixing the direction — a paired distribution-variable swap that inverted the fix instead of completing it (confirmed at scale: the early distribution's signature values appearing hundreds of times strictly after the boundary, across 50 seeds).
- None of the three were visible from reading the code in isolation; each required a targeted check for a specific impossible value showing up on the wrong side of a specific boundary. Consistent with the existing "bugs only findable by running it" pattern, not a new failure mode.

---

## Milestone 10 — Modeling a real, non-monotonic per-student progression instead of an assumed clean one

*Internal cross-reference: blueprint §14, Entry 43.*

**Problem**

`Published Materials Used` needed per-student curriculum-level weights. The plausible assumption going in — a clean, monotonic level progression for both students over the season — held for one student (S02) and did not hold for the other (S01), whose real level usage moves forward, back, and forward again across the year.

**Options considered**

1. Smooth S01's data into the same clean monotonic shape assumed for S02, treating the irregularity as noise.
2. Model each student's real, checked phase sequence directly, including S01's non-monotonic one, even without a confident explanation for why it happened.

**Chosen solution**

Option 2.

**Trade-offs**

- Option 1 would have produced a tidier-looking generator at the cost of actively misrepresenting what the real data shows for one of the two students — exactly the kind of assumed-narrative-over-checked-data mistake this project's whole discipline exists to avoid.
- A second, related mechanism — same-level Textbook/Workbook pairing for 2-item rows — was itself checked against real data rather than assumed (~86% same-level, ~14% genuine cross-level transitions) after an initial "sample two items independently" design was recognized as producing mostly-nonsensical output before it was ever run.
- This function accumulated the most debugging rounds of any field in the generator — a list-vs-dict crash, a computed value never assigned to the row, a missing branch, and a same-level-selection bug passing probabilities where population values belonged. Worth noting as the point where per-field complexity crossed from "pick a value" into "pick a value and decide its relationship to another value in the same row," which Milestone 11 confirms was not a one-off.

---

## Milestone 11 — A genuine cross-field dependency, and a boundary-scoping mistake that recurred three times

*Internal cross-reference: blueprint §14, Entry 44. See also Patterns Journal, "Two independent boundary conditions need two nested if/else pairs."*

**Problem**

`Puzzle Type`'s null-rate genuinely depends on `Primary Task Type`'s already-assigned value (confirmed directly: 100% populated for `Mixed`/`Puzzle`, ~25% for `Worksheet`) — the first field in the generator with a real dependency on another field's *value*, not just on `true_week_ending`. Compounding this, the two fields' own cutoffs don't align: `Puzzle Type` exists two weeks before `Primary Task Type` does, leaving a real coverage gap the original design didn't address at all.

**Options considered**

1. Treat the two boundary questions ("has this field's cutoff passed," "has the other field's cutoff passed") as one combined condition.
2. Nest two separate `if`/`else` pairs, one per boundary question, with the per-row values needed by both computed once, above the split.

**Chosen solution**

Option 2 — but it took three attempts to actually land there.

**Trade-offs**

- Every intermediate attempt collapsed the two boundary questions back into one merged pair in a different surface shape each time: first as a literally duplicated condition, then as an `else` reattached to the wrong (outer) gate — catching Jiu-Jitsu and pre-cutoff rows in logic meant only for late-Enrichment ones, crashing with `KeyError: None`. A third, related bug in the same function — shared per-row values computed in only one branch, silently reused by the other via Python's loop-variable persistence rather than genuine sharing — corrupted per-student calibration without crashing at all, confirmed by finding both students' empirical distributions converging toward each other instead of their own separate real targets.
- Final verification across 100 seeds: zero boundary violations, the real `Worksheet` null rate reproduced almost exactly, and — the check that actually mattered — the two students' distributions landing distinctly near their own targets again once the shared-computation bug was fixed.
- Promoted to its own Patterns Journal entry given it recurred three times within one function's debugging history alone, not because any single occurrence was unusual on its own.

---

## Milestone 12 — Discovering a category of fields determined by another field's state, not independently calibrated

*Internal cross-reference: blueprint §14, Entry 45. See also Patterns Journal, "Fields fully or partly determined by another field's already-assigned state."*

**Problem**

Every field built up to this point was calibrated as if every other field were irrelevant to it. Three fields built in close succession — `Puzzle Challenge or Novelty`, the three `assign_session_context_fields` columns, and `Puzzle Type`'s dependency on `Primary Task Type` (Milestone 11) — turned out not to fit that assumption, each confirmed directly against real data rather than guessed.

**Options considered**

1. Treat each of the three as an isolated special case, calibrated independently despite the real correlation.
2. Model each dependency explicitly — a deterministic gate for `Puzzle Challenge`, a single shared null-gate for the three session-context fields, a probabilistic dependency for `Puzzle Type`.

**Chosen solution**

Option 2 for all three.

**Trade-offs**

- `Puzzle Challenge or Novelty` turned out to be the simplest function in the entire generator specifically because option 2 was correct — a perfect, zero-exception 1:1 relationship with `Puzzle Type` left nothing else to calibrate.
- `assign_session_context_fields`'s apparent ~29%/45% null rates, calculated across the whole season, were entirely an artifact of the pre-cutoff period diluting the average — the true active-period rate for all three fields is 0% null. Caught by checking the active-period rate specifically rather than trusting the whole-season figure.
- The real, generalizable lesson isn't "sometimes fields relate to each other," which is unsurprising — it's that this assumption held silently for over forty prior entries and was worth checking explicitly once a plausible-sounding dependency was suspected, the same discipline that already confirmed a *lack* of relationship between `Task Difficulty` and `Pages Completed` back in Milestone-adjacent Entry 40.

---

## Milestone 13 — Choosing statistical keyword-correlation over semantic generation for a free-text field

*Internal cross-reference: blueprint §14, Entry 47 (Notes design).*

**Problem**

`Notes` is a substantial free-text field (0% null, ~209 words average) unlike every other field in the generator, which are all weighted draws from small, known vocabularies. The original, pre-project hope for this field was to support downstream keyword/theme-frequency analysis; a later, more sophisticated-sounding alternative — generating text whose sentiment or content coherently, specifically reflects each row's exact rating combination — was considered and set aside.

**Options considered**

1. True semantic correlation: generated text that specifically, coherently reflects the exact rating combination for its row.
2. A themed fragment bank, sampled with probabilities that shift based on the row's own ratings for keywords/themes with a real, checked correlation — a soft, statistical correlation, not a semantic one.

**Chosen solution**

Option 2.

**Trade-offs**

- Option 1 would require an LLM generation step — a fundamentally different architecture from the rest of this generator, which is pure weighted random sampling with no model calls. Not ruled out as a future capability, but not a fit for extending the existing pipeline as-is.
- Option 2 turned out to map more naturally onto the *original* keyword-frequency goal than option 1 (sentiment analysis) would have — sentiment requires a classifier to agree the generated text carries the intended sentiment; keyword frequency is direct substring matching against fragments deliberately authored to contain the target vocabulary, sampled with probabilities deliberately tied to the row's own ratings. The generator produces the eventual downstream analysis result by construction, rather than hoping an NLP step discovers it.
- Every candidate keyword/theme was tested against real data before being trusted, not assumed from a plausible-sounding pairing — the same discipline as every other field, applied to something much fuzzier than a value distribution. Results were genuinely mixed: `familiar` correlated strongly and broadly (up to +0.88 against `Resilience`); `independent`, `flexib`, `motivat`, `structure` correlated well against their hypothesized single field; `comparison`, despite being narratively prominent in the source research notes, showed no meaningful correlation against anything tested and was kept as flavor vocabulary only, not built into the correlation mechanism.

---

## Milestone 14 — Verifying generated correlation strength, not just generative mechanism correctness

*Internal cross-reference: blueprint §15, Entry 48. See also Patterns Journal, "A correctly-calibrated selection mechanism doesn't guarantee the generated content carries the measurable signal."*

**Problem**

`assign_notes`'s theme-sampling weights were built and confirmed correct at the row level — high ratings correctly shifted probability toward their correlated themes. Running the same aggregate "mean rating with vs. without keyword" test used to validate every real-CSV correlation earlier in this project, but against *generated* output, revealed four of seven themes showing zero measurable signal despite correct selection logic.

**Options considered**

1. Trust the row-level trace as sufficient verification, since the selection mechanism was demonstrably correct.
2. Run the full aggregate correlation test against generated output, the same test standard used for every real-data correlation claim in this project, and treat a gap between the two as a real bug even though nothing crashed.

**Chosen solution**

Option 2.

**Trade-offs**

- The root cause, once found, was simple: most fragments in the affected themes were thematically related to their keyword but never literally contained it as a substring — a keyword-frequency analysis run against the generated text would find nothing to count, regardless of how correctly the underlying theme got selected. Fixed by auditing every fragment for literal keyword presence and rewriting the ones that lacked it, then rerunning the same aggregate test until all seven themes showed real, correctly-signed diffs against their real targets.
- Two further bugs surfaced only through the same aggregate-verification habit, not through reading the code: `familiar`'s `correlated_field` was set to the full real CSV header rather than the internal short key `assign_secondary_ratings` actually produces, silently returning `None` on every row and producing zero data points — invisible until `familiar` alone came back empty against six working sibling themes. And the rating-adjustment formula could reach exactly zero at the lowest rating value, which — since two themes share one correlated field — could occasionally zero out enough themes simultaneously to leave fewer selectable options than the row's drawn bullet count, crashing the without-replacement sampling call. Fixed with a floor on the adjustment multiplier so suppression stays real but never total.
- The general lesson, worth carrying forward: when a generator's calibration claim is about a *downstream measurable property* (a correlation, a frequency, a distribution), verification needs to check that property directly on generated output — not just confirm the generative mechanism looks correct in isolation. The two can and did diverge here without anything failing loudly.

---

## Milestone 15 — Closing out session-row richness, and naming what's still ahead precisely

*Internal cross-reference: blueprint §15, Entry 48.*

**Problem**

After `assign_notes`, it was worth checking directly whether "session-row richness is done" also meant "the synthetic generator is done" — an assumption worth verifying against the real weekly synthesis CSV and the actual file contents rather than accepting from momentum.

**Options considered**

1. Treat the generator as complete now that every session-observation-log column has a working `assign_` function.
2. Check the real weekly synthesis CSV's columns and the generator file directly before making that claim.

**Chosen solution**

Option 2 — confirmed session-row richness is genuinely complete, and confirmed directly that it is not the whole generator.

**Trade-offs**

- The check was cheap and conclusive: `generate_synthesis_log_rows` currently produces only `week_ending` and `num_sessions_reported`, while the real weekly synthesis CSV has ten additional columns (`Snapshot`, `Notable Shifts or Confirmations`, `Learning Mechanisms Observed`, `Optional: Data Flags`, `Are participants siblings?`, `Dyad ID`, JJ-learner selection, private-lesson selection, three ghost columns) with no corresponding enrichment logic anywhere in the file — and no CSV-writer function exists at all yet.
- Worth naming as its own habit: "is phase X done" and "is the whole project done" are different claims, and the gap between them is exactly the kind of thing worth checking against source material rather than inferring from the momentum of just finishing a hard piece of work.

---

## Milestone 16 — The barrel module that wasn't

*Internal cross-reference: blueprint §16, Entry 49. See also Patterns Journal, "Wildcard imports silently exclude underscore-prefixed names" and "Bugs only findable by running the code, not reading it."*

**Problem**

At 1600+ lines, `synthetic_generator.py` was split by concern into `_helpers.py`, `schedule_generation.py`, `session_enrichment.py`, and `synthesis_enrichment.py`, with `synthetic_generator.py` meant to become a thin barrel module re-exporting everything, so `test_synthetic_generator.py` and `inspect_pipeline.py` could keep calling `sg.function_name(...)` without any changes on their end.

**Options considered**

1. Trust that the split was complete once the new files existed and `synthetic_generator.py`'s first few lines showed the new wildcard imports.
2. Verify by actually running the full pipeline through the real barrel module, the same standard applied to every other piece of this project.

**Chosen solution**

Option 2 — and it caught two separate, real problems option 1 would have missed entirely.

**Trade-offs**

- First: `schedule_generation.py` and `session_enrichment.py` used wildcard imports (`from src.generator._helpers import *`) to pull in their dependencies, but every helper in `_helpers.py` is deliberately underscore-prefixed — and Python's `import *` silently excludes underscore names by default. The pipeline crashed with `NameError` the moment it actually ran, not before. Fixed with explicit imports for the specific underscore names each file needed.
- Second, more subtle: `synthetic_generator.py` itself was never actually reduced to a barrel — the four new wildcard-import lines had been added to the *top* of the file, but the full original 1611 lines of function definitions were still sitting underneath, completely intact. `head` and `grep "^from"` both looked correct; only checking the *whole* file for lingering `def` statements (and noticing the line count hadn't meaningfully changed) revealed it. An `hasattr(sg, '_find_phase')` check that returned `True` initially looked like confirmation the new structure worked — it was actually evidence the old code was still doing the work.
- Fixing the second problem reintroduced the first one in miniature: once `synthetic_generator.py` was genuinely reduced to just wildcard imports, `sg._generate_rng` — the one underscore-prefixed name both `test_synthetic_generator.py` and `inspect_pipeline.py` call directly — stopped being accessible, for exactly the same reason as the first bug. Fixed by adding one explicit import line for it alongside the wildcards.
- Final verification: 25 tests passing via `pytest`, and `python -m scripts.inspect_pipeline` producing the expected output — confirmed against the actual project files, not just a standalone reproduction.

---

## Milestone 17 — `generate_synthesis_log_rows` needed a real cutoff, and fixing it broke tests twice before it broke them zero times

*Internal cross-reference: blueprint §16, Entry 50. See also Patterns Journal, "Positional arguments silently break when a function's signature changes."*

**Problem**

`generate_synthesis_log_rows` produced 39 rows spanning the full season; the real weekly synthesis log has 20, entirely confined to `2026-01-25` onward — a structural gap caught only by comparing generated row counts against the real CSV directly, not by reading the function.

**Options considered**

1. Add a `cutoff_week` parameter and update every call site to match.
2. Same, but patch existing positional call sites minimally rather than converting them fully to keyword arguments.

**Chosen solution**

Option 1, arrived at after option 2's minimal-patch instinct produced a worse failure than the one it was fixing.

**Trade-offs**

- Inserting `cutoff_week` into the middle of the signature broke an existing positional test call immediately (`TypeError`) — expected, and the reason keyword arguments matter for any call site that survives a signature change.
- The first attempted fix converted only the new argument to a keyword, leaving a trailing positional argument after it — syntactically invalid in Python regardless of what the values would have meant, and unlike a runtime `TypeError`, a `SyntaxError` prevents the entire file from being collected by `pytest`. All 25 tests reported as failing, not just the two touching this function, which was momentarily alarming out of proportion to the actual size of the bug.
- Final fix converted both affected call sites fully to keyword arguments, immune to any future reordering. Verified against the real project files: 25 passing, `inspect_pipeline` producing expected output.
- The cutoff date itself required no independent derivation — `2026-01-25` was already established for the session-level `Sibling Dyad` transition, and the real weekly synthesis log's own first entry matches it exactly, strong evidence of one real shared event rather than two coincidental ones.

---

## Milestone 18 — Two synthesis-row functions: a grain question worth asking explicitly, and a conditional-probability correction

*Internal cross-reference: blueprint §16, Entries 51–52. See also Patterns Journal, "Independent projections at the grain each consumer needs" and "Fields fully or partly determined by another field's already-assigned state."*

**Problem**

Two functions needed building on the corrected `generate_synthesis_log_rows` foundation: seven trivial always-fixed fields, and a two-field cluster (`JJ Observed`, `Private Lessons`) with a real cross-field dependency and a genuine data-provenance concern.

**Options considered**

1. For `Student ID`: default to the same per-student explosion already used for the session log, on the reasoning that consistency across the generator is simpler to maintain.
2. For `Student ID`: check the real weekly synthesis CSV's actual grain before assuming the session log's precedent transfers.
3. For the two dependent fields: draw each independently, letting the real cross-field correlation emerge or not by chance.
4. For the two dependent fields: model the confirmed dependency explicitly, gating one field's draw on the other's already-decided value.

**Chosen solution**

Option 2 and option 4.

**Trade-offs**

- Option 2 confirmed the session log's explosion doesn't transfer — every real weekly synthesis row uses the single combined `"S01, S02"` string, reflecting one real submission per week about the dyad, a genuinely different real observation practice from the session log's two-submissions-per-shared-session pattern. Exploding it anyway would have invented a shape the real data doesn't have, for the sake of surface consistency with an unrelated decision.
- Option 4 required more than just adding a gate: the first draft's null-rate for `JJ Observed` reused an *unconditional* active-period figure inside a branch that only runs for the *subset* where `Private Lessons` is already populated — caught by tracing the code's actual nesting structure, not by re-checking whether the original number itself was correctly computed (it was, for a different, no-longer-relevant question). Recomputed against the correct subset: `9/14` null rather than the unconditional `0.6875`.
- A real, scoped design decision on null-handling style: whether to fold `None` directly into a weighted-choice array or keep the separate-`is_null`-then-branch pattern used elsewhere. Kept the combined form for these two fields specifically (few total outcomes, null genuinely being just one more simple option among them), explicitly not generalized to every field, since most fields' null-rate and value-distribution answer different real-world questions that benefit from staying separately calibrated.
- `Private Lessons` was flagged as a genuinely different category of data-quality concern from anything else in this project — not a small-sample-size confidence question, but secondhand information (parental report) that was never directly, weekly-verified the way every other observed field was. Flagged explicitly as a Silver/Gold-layer exclusion candidate rather than left to blend in with the rest of the dataset's implied trustworthiness.
- Final verification, 100 seeds: zero violations across every boundary and dependency check, both distributions within a point of their real targets.
