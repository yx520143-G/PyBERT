# D2 review-fix independent review (candidate479b885)

Incremental fixed diff:9331c38e4393868d69d2bbc4dbd22565c0612324...479b88590ef6613fef0c4e29a85bfde4fe2c1e3d. Both independent agents read only stdlib/Git; product/NumPy/test/write calls0. This is an intermediate self-review, not PM acceptance.

## Standards

Documented0; actionable heuristic0. Complete root CLAUDE.md/userAGENTS and smell baseline applied. Three product files and harness/evidence reviewed; changes limited to review fixes and necessary metadata/guards.110 changed/added files UTF8noBOM,103 receipt hashes match. Protected-final-check-v2.json was created after the pinned reviewed commit and is outside that fixed review.

## Spec

Implemented wrong1; historical partial1; scope creep0.

[P2 wrong] New timestamp ULP bound in clocks.py187–200 also covers integer dtype permitted by validate_period. For int64 t=[2**60,2**60+1024,2**60+3072], exact intervals[1024,2048] and originalts1024 give error1024. Spacing converts integer timestamps to float, yielding256 each and bound>=1024, so the true doubled interval can be accepted/FFT run. The integer timestamps themselves have no floating origin rounding. This violates the PM requirement to retain real nonuniform rejection and the original contract requiring no FFT on nonuniform inputs. Independent read-only source/scalar arithmetic finding; not yet dynamically executed. Keep currentfi/u scope or explicitly validate integer intervals exactly; never rewrite raw.

[P2 historical partial] JSON14 direct write/read elapsed UNKNOWN remains, with existing02copy/08–10malformedbuffer/08cap4001/13preflight/firstseal failures unchanged. No historical timing is retrofilled.

Original snapshot-shadowing fix is confirmed by actual source AST/symtable (baseglobal/reviewedlocal/currentglobal). Float64 16-point rule and analysis metadata carry-through meet the reviewed scope; only the period seam ran, fullworker/coordinator not rerun.15red twofailures,16green twopasses;Dpure18, total17291.

The new integer finding is unresolved pending PM approval of the concrete plan integer-review-followup-plan.json.16/16batchslots are exhausted; no17th execution or launchercap change is permitted without explicit approval.Originalseal1 remains unchanged.
