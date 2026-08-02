# Confidence Scoring

The score prioritizes manual review. It is not a CVSS score, severity rating, or bounty prediction.

## Base evidence

A valid Git `HEAD` signature begins with a base score of 70.

Accepted signatures:

- A complete symbolic reference such as `ref: refs/heads/main`.
- An exact 40-character or 64-character hexadecimal detached object identifier.

HTTP 200 without a valid signature receives no positive score.

## Confidence additions

| Condition | Score |
|---|---:|
| Randomized missing-path response is distinct | +15 |
| Small non-truncated response consistent with HEAD metadata | +5 |
| Compatible content type | +5 |
| Each additional safe Git metadata signature | +5, maximum 100 |

## Classification thresholds

| Classification | Rule |
|---|---|
| `CONFIRMED` | Score 85 or higher with a distinct missing-path baseline |
| `PROBABLE` | Git signature exists but the final score is below 85 |
| `SOFT_404` | Git path response matches or closely resembles the randomized missing path |
| `BLOCKED` | Access denied, normally HTTP 401 or 403 |
| `REDIRECTED` | HTTP 3xx; redirects are intentionally not followed |
| `NOT_EXPOSED` | No valid Git HEAD signature |
| `ERROR` | No usable HTTP response or an internal task error |

## Evidence levels

| Evidence level | Meaning |
|---|---|
| `head-metadata-only` | Valid Git HEAD signature only |
| `multi-file-metadata` | One or more additional Git metadata signatures |
| `unconfirmed` | No positive Git evidence |

## Why a confirmed score is not a guaranteed bounty

A technically confirmed endpoint may still be:

- Out of scope.
- Previously reported.
- Explicitly ineligible.
- Considered low impact.
- Hosted by a third party.
- Protected by a program-specific exception.
- Insufficiently explained in the final report.

Always separate confirmed evidence from potential impact.
