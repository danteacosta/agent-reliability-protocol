# Keep malformed lifecycle inputs inside profile validation

Contract: given a malformed event collection or a list/object episode identity
or checkpoint, `validate_agent_smell_run` returns actionable validation errors;
it must not raise an uncaught type error. Valid native lifecycle runs and
existing temporal/provenance/leakage checks retain their behavior.

Reproduction: 11 parameterized public-interface regressions failed before the
fix. The profile caught construction errors but continued into set operations
on unhashable JSON values; non-iterable event collections failed earlier.

Design: validate collection and identity shapes before dependent iteration,
sorting, and grouping. Retain the existing validator and error-list contract;
no new abstraction. Tests use real public documents, not implementation mocks.

Verification: `python -m pytest -q`, `python -m compileall -q src tests`, and
`git diff --check`. The regression matrix covers arrays/objects in both identity
fields plus null, numeric, boolean, object, and string collection payloads.
