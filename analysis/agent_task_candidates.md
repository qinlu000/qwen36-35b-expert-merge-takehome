# Real-task discovery pilot (2026-10-15)

Read-only discovery, no upstream messages or changes, no teacher API calls and no repository code executed. These are 8 candidates across 5 repository groups, not 8 verified training samples. Source text was inspected; environments and graders still need independent reproduction.

## First lightweight solver candidate

ID: real-rich-import-cwd-001. Repository: Textualize/rich. Base: 9d8f9a372cc5916fd4781fec207ced7ddac2f08f. Source: https://github.com/Textualize/rich/issues/4201 . MIT license verified at https://github.com/Textualize/rich/blob/9d8f9a372cc5916fd4781fec207ced7ddac2f08f/LICENSE .

Sanitized solver requirement: importing Rich fails in a development environment where querying the current working directory raises an operating-system error although absolute paths remain usable. Make package import robust for unavailable working directories while retaining normal behavior. Deliver a patch and real execution records. Do not give the solver the original issue, comments, later history or proposed fix: the original issue includes solution code.

Independent grading: run import in isolated child processes with normal cwd, missing cwd, permission-denied cwd and a general OS error; retain normal-path behavior and simple package regression checks. The narrow reproducer uses only Python standard-library unittest/mock and a source checkout, no Docker. Actual dependency-free import still needs verification of the checkout import chain; currently only source inspection is complete. Estimated packaging/reproduction: 15-30 minutes; solver: 5-20 minutes, not measured.

## Candidate table

All time estimates are pilot budgets for 1-4 CPU, not measured durations.

| ID / category | Primary source / code license | base_commit status | Independent acceptance | group_id / provisional split | Packaging / solver |
|---|---|---|---|---|---|
| rich-import-cwd / repository repair | [Rich issue4201](https://github.com/Textualize/rich/issues/4201), MIT | 9d8f9a372cc5916fd4781fec207ced7ddac2f08f, stated by issue author | Import behavior under cwd error variants plus normal path regression | repo:Textualize/rich / train candidate | 15-30 / 5-20 min |
| boltons-permissions / repository repair, file engineering | [Boltons issue480](https://github.com/mahmoud/boltons/issues/480), BSD-3-Clause | 967864f89791509f9eb36b22b4579d36b72a6df2, full hash resolved from issue commit link | Tightening owner/group/other permissions changes integer mode and actual temporary-file chmod result correctly; preserve unrelated fields | repo:mahmoud/boltons / train candidate | 15-30 / 5-20 min |
| boltons-log-rotation / repository repair, file engineering | [Boltons issue479](https://github.com/mahmoud/boltons/issues/479), BSD-3-Clause | Same 967864f89791509f9eb36b22b4579d36b72a6df2 | Temporary files: keep=1, multiple generations, missing intermediate generation, extension/no extension; check directory entries and retained content | Same boltons group; never cross split | 20-40 / 10-25 min |
| more-itertools-zero-cache / repository repair | [issue1268](https://github.com/more-itertools/more-itertools/issues/1268), MIT | Must resolve base before [fix PR1294](https://github.com/more-itertools/more-itertools/pull/1294); current HEAD 4aeb4338ae1407d8da9723e86da99efeb446f719 is NOT assumed buggy | Zero-cache peek/truthiness must preserve the iterator stream; repeat calls, exhaustion and regular cache regression | repo:more-itertools/more-itertools / val candidate | 20-40 / 10-25 min |
| petl-csv-transform / terminal execution, data engineering | [Official ETL workflow](https://github.com/petl-developers/petl/blob/03a074594a31e731e2fca29bb97536e24717d6ca/docs/intro.rst), MIT | 03a074594a31e731e2fca29bb97536e24717d6ca, current HEAD from git ls-remote | Own CSV fixtures: normalize text, convert numerical columns, derive a field, write CSV; independent stdlib reader checks schema, rows and numerical tolerance | repo:petl-developers/petl / train candidate | 20-40 / 5-20 min |
| petl-stream-to-sqlite / terminal execution, data engineering | [Official streams/IO](https://github.com/petl-developers/petl/blob/03a074594a31e731e2fca29bb97536e24717d6ca/docs/io.rst) and [ETL/database output](https://github.com/petl-developers/petl/blob/03a074594a31e731e2fca29bb97536e24717d6ca/docs/intro.rst), MIT | Same 03a074594a31e731e2fca29bb97536e24717d6ca | Own compressed CSV fixture to SQLite artifact; stdlib sqlite3 verifies values/schema, documented rerun behavior and unchanged read-only inputs | Same petl group; never cross split | 30-60 / 10-25 min |
| mpmath-slow-series / scientific execution, numerical diagnosis | [mpmath issue1186](https://github.com/mpmath/mpmath/issues/1186), BSD-3-Clause | Issue reports abbreviated 7783b37, full hash pending; current HEAD bbbeabbd7e82eab8cfd6948770ae51086ff47098 is only an environment candidate and does not prove the failure persists | Investigate a slow positive series, provide reproducible script and convergence/error evidence. Grader must FIRST establish reference through independent mathematical bounds or high-precision method; issue output alone is not ground truth | repo:mpmath/mpmath / val candidate | 45-90 / 15-30 min |
| mpmath-ode-artifact / scientific execution, simulation artifact | [Official ODE workflow](https://github.com/mpmath/mpmath/blob/bbbeabbd7e82eab8cfd6948770ae51086ff47098/mpmath/calculus/odes.py), BSD-3-Clause | bbbeabbd7e82eab8cfd6948770ae51086ff47098, current HEAD from git ls-remote | Own IVP and sampling requirements: numerical table and accuracy summary; independent analytic identities, initial values and precision stability check | Same mpmath group; parameter variants stay together | 30-60 / 10-25 min |

The petl and ODE items are proposed tasks derived from documented real software workflows. They are not existing GitHub issues and are not claimed to match official benchmark difficulty.

## License evidence

- Rich: [MIT](https://github.com/Textualize/rich/blob/9d8f9a372cc5916fd4781fec207ced7ddac2f08f/LICENSE).
- Boltons: [BSD-3-Clause](https://github.com/mahmoud/boltons/blob/967864f89791509f9eb36b22b4579d36b72a6df2/LICENSE).
- More-itertools: [MIT](https://github.com/more-itertools/more-itertools/blob/4aeb4338ae1407d8da9723e86da99efeb446f719/LICENSE).
- Petl: [MIT](https://github.com/petl-developers/petl/blob/03a074594a31e731e2fca29bb97536e24717d6ca/LICENSE.txt).
- Mpmath: [BSD-3-Clause](https://github.com/mpmath/mpmath/blob/bbbeabbd7e82eab8cfd6948770ae51086ff47098/LICENSE).

A code license does not automatically establish identical licensing for every user's issue prose. Write our own requirements, preserve provenance and code attribution/license. No issue prose or patch is copied into a solver package here. Immutable source snapshots and hashes remain to be produced.

## Split, contamination and replay gates

1. All five repositories are outside the exact SWE Pro eleven-repository list in configs/data_exclusions.json. Fork/rename matching and cross-checking the other three official task families remain pending; this is not a completed decontamination claim.
2. Existing downloaded Open-SWE, Terminal Corpus and other pools may contain these repositories or task families. A proposed val repository requires excluding its full origin group from ALL training sources and teacher task generation, not merely separating our newly collected rows.
3. Multiple trajectories, reproductions and parameter variants of the same issue/root cause share one group. Freeze groups and split BEFORE solving. Val solutions and grader material never enter SFT.
4. Provenance issue/comments, gold patch, future commits and grader tests stay in a separate artifact. The solver only receives sanitized symptoms, allowed starting source and environment. Do not let it search the issue or later history. A discoverer having seen a fix does not justify exposing that fix to an independent solver.
5. For the merged more-itertools repair, resolve the pre-fix commit and establish fail-to-pass. Open issues still require an independent oracle and reproducibility check.
6. Training trajectories need actual tool calls, working directories, observations, patch/artifacts, environment/version and independent pass/fail evidence. A final explanatory answer alone is not an agent trajectory. Conversion into the selected target harness messages requires separate verification. Do not invent tool observations or invisible reasoning.
7. Several issues include explicit suggested fixes; do not pass raw source pages as solver prompts.

## Scope conclusion

This approach can create a small verified training supplement and an independent task-dev set without a separate teacher API bill. Codex time/usage and CPU execution still apply. Eight candidates across five repository groups are far too small for the main million-token SFT corpus, particularly after val holdouts.

GitHub software tasks do not cover HLE's broad academic and multimodal knowledge. No suitable license-checked HLE-style academic question source was approved in this limited pilot. A separate academic-source search and independent answer verification remain necessary. The existing downloaded corpora should remain the main training source unless a larger pilot demonstrates enough throughput and coverage.

Start with the Rich case to validate discovery -> independent solver -> independent verification -> real trajectory export, then decide collection scale. No training/evaluation jobs were started.
