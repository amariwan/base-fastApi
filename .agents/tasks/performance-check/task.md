# Task: Performance Check

## Schedule
- Repeat: weekly or before release

## Objective
Detect performance regressions and resource issues.

## Steps
1. Run `just test-cov` and review slow tests.
2. Check for N+1 queries in changed services.
3. Verify pagination on list endpoints.
4. Review cache usage and invalidation.
5. Profile hot endpoints under load (k6/Locust).
6. Check DB query plans for new queries.

## Output
- Performance report with bottlenecks and recommendations.
