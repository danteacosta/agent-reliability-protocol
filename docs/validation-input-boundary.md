# Validation input boundary

The offline validator is used to admit research artifacts into downstream checks.
A scalar or array in place of a contract object must be reported as invalid,
not terminate validation with an attribute error. Invalid input does not establish
an experimental result, and these checks do not establish semantic validity.

## Acceptance contract

- Given a non-object JSON root, checking a contract returns a validation error.
- Given missing, unreadable, non-UTF-8 or malformed JSON input, the CLI emits a
  JSON failure and exits with code 1 without reproducing the file contents.
- Given a non-object manifest or event row, directory validation reports an
  error with file context and event line number when available.
- Given a sequence or envelope contract, its event collection must be an array
  of objects; envelopes also require an object manifest before parsing. These
  compound kinds are available through `check_contract`, not the CLI kinds.
- Given malformed profile manifest roots or non-text split/provenance fields,
  return validation errors without dictionary/hash operations on those values.
- Given malformed profile event sequence numbers, the profile returns an error
  before temporal ordering. Strings, booleans, fractions, negatives and missing
  values are not coerced into valid sequence numbers. Event indices are zero-based.
- Existing v1/v2/v3 valid fixtures and wire schemas remain unchanged.

## Design and verification

Object checks precede dictionary access at these ingress points. File-read
errors are normalized where the files are consumed; expected errors remain
validation data. No catch-all exception handling or new runtime dependency is
introduced. Nested field validation continues to use the existing contracts;
this change is not a comprehensive malformed-input audit of every nested type.

Behavior tests call the public validators and CLI entry point with temporary
files. They cover null, arrays, strings, numbers, booleans, malformed JSON,
invalid UTF-8, and absent files. Run `python -m pytest -q` and the CLI fixture
checks from CI. No browser test is needed for this offline interface.
