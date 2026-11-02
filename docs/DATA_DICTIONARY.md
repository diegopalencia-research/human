# Data dictionary — v0.2

## observations
One row per indicator observation. A submitted check-in creates multiple rows sharing a timestamp.

| Field | Meaning |
|---|---|
| profile_id | Owner identifier |
| observed_at | Timestamp of observation |
| domain | One of the nine operational domains |
| indicator | Specific measured or self-reported variable |
| value | Raw numeric value |
| unit | Original unit or rating scale |
| scale_min / scale_max | Bounds where a bounded scale applies |
| source | Self-report, device, record, etc. |
| confidence | Confidence in observation (1–5) |
| notes | Context |

## life_periods
Retrospective intervals, such as childhood or a period of shift work. Store approximate start/end dates and recall confidence. These intervals are contextual, not daily observations.

## life_events
Important transitions or disruptions. `impact_domains` contains a list of potentially relevant domains. This is a user-attributed context field, not a causal label.

## activities
Time-use records with date, activity category and duration. A complete activity logging interface is planned but not yet included.

## profiles
Display name and birth date. Birth date supports the lifetime axis; it does not imply that historical physiological data exist.
