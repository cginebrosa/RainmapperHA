# Mushroom Observations Schema

This document defines the first operational schema for mushroom observations used to calibrate and confirm species model parameters.

The schema is intentionally exhaustive but not fully mandatory. A field observer must be able to create a useful observation with only species, date, location, abundance, source quality and validation state. Additional fields enrich calibration when available.

## Goals

- Capture real positive and negative field observations for species profile calibration.
- Keep fast entry possible from common user reports, especially copied Google Maps links.
- Preserve enough provenance to weight observations during calibration.
- Avoid mixing observations into `mushroom_profiles.json` or `mushroom_reference_catalogs.json`.
- Keep labels translatable through `mushroom-data/mushroom_labels.json`.
- Keep selectable values in `mushroom-data/mushroom_reference_catalogs.json` so they can evolve without code changes.

## Storage

Recommended future file:

```text
mushroom-data/mushroom_observations.json
```

Persistent HA copy should follow the existing mushroom data pattern:

```text
/share/rainmapper/mushroom-data/mushroom_observations.json
```

Controlled values used by this schema live under `catalogs` in `mushroom_reference_catalogs.json`:

- `observation_flush_abundance`
- `observation_validation_statuses`
- `observation_calibration_uses`
- `observation_exclusion_reasons`
- `observation_source_types`
- `observer_expertise_levels`
- `observation_location_sources`
- `observation_altitude_sources`

UI screens should read option labels, ordering and calibration metadata from these catalogs rather than hardcoding display values.

## Minimal Valid Observation

```json
{
  "observation_id": "obs_20260629_0001",
  "species_id": "boletus_pinophilus",
  "observed_at": "2026-06-29",
  "location": {
    "lat": 42.35406,
    "lon": 1.85317
  },
  "flush_abundance": "abundant",
  "source_quality": 0.8,
  "validation_status": "draft",
  "calibration_use": "review"
}
```

Required fields:

- `observation_id`
- `species_id`
- `observed_at`
- `location.lat`
- `location.lon`
- `flush_abundance`
- `source_quality`
- `validation_status`
- `calibration_use`

## Full Observation

```json
{
  "observation_id": "obs_20260629_0001",
  "species_id": "boletus_pinophilus",
  "observed_at": "2026-06-29",
  "location": {
    "input": "https://maps.google.com/...",
    "lat": 42.35406,
    "lon": 1.85317,
    "source": "google_maps_url",
    "precision_m": null
  },
  "altitude": {
    "meters": 1259,
    "source": "google_maps",
    "resolved_at": "2026-06-29T10:30:00Z"
  },
  "flush_abundance": "abundant",
  "observer": {
    "name": "Carlos",
    "expertise": "experienced"
  },
  "source": {
    "type": "personal_observation",
    "label": "",
    "url": "",
    "notes": ""
  },
  "source_quality": 0.9,
  "validation_status": "valid",
  "calibration_use": "include",
  "calibration_exclusion_reason": "",
  "site_context": {
    "observed_host_ids": [
      "host_pinus_sylvestris",
      "host_quercus_ilex"
    ],
    "habitat_notes": "",
    "host_notes": "",
    "soil_notes": "",
    "aspect_notes": ""
  },
  "metadata": {
    "created_at": "2026-06-29T10:30:00Z",
    "updated_at": "2026-06-29T10:30:00Z",
    "created_by": "webui",
    "reviewed_by": "",
    "reviewed_at": ""
  }
}
```

## Field Definitions

### Identity

`observation_id` is a stable unique ID. Suggested format: `obs_YYYYMMDD_NNNN` for UI-created records. Imported records may use a deterministic source prefix.

`species_id` must reference an active species in `mushroom_profiles.json`. Archived species should require explicit review before calibration use.

`observed_at` is the observation date in ISO format, `YYYY-MM-DD`. Time is intentionally optional because most mushroom reports are day-level.

### Location

`location.input` stores the original pasted value. It may be a Google Maps link, decimal coordinates, or another user-provided location string.

`location.lat` and `location.lon` use decimal WGS84 coordinates. This is the canonical coordinate format.

`location.source` records how coordinates were obtained:

- `manual_decimal`
- `google_maps_url`
- `device_gps`
- `imported_csv`
- `inferred`

`location.precision_m` is optional. Use it when the source reports uncertainty, when a location is intentionally blurred, or when an imported record is approximate.

The UI should support parsing common Google Maps URLs and coordinate strings. If parsing fails, the observation should remain draft until coordinates are corrected.

### Altitude

`altitude.meters` is optional but important for calibration. If missing, the UI should offer a `Recover altitude` action from coordinates.

`altitude.source` records where altitude came from:

- `manual`
- `google_maps`
- `dem`
- `imported`

`altitude.resolved_at` records when automatic altitude was fetched.

### Flush Abundance

`flush_abundance` is the observed result. It is categorical, ordered and required.

Allowed values are maintained in `catalogs.observation_flush_abundance`:

- `exceptional`
- `very_abundant`
- `abundant`
- `normal`
- `scarce`
- `very_scarce`
- `absent`

The catalog also stores the numeric `calibration_score` used by calibration:

| Value | Score |
| --- | ---: |
| `exceptional` | 1.00 |
| `very_abundant` | 0.85 |
| `abundant` | 0.70 |
| `normal` | 0.50 |
| `scarce` | 0.30 |
| `very_scarce` | 0.15 |
| `absent` | 0.00 |

Negative observations (`absent`) are valuable when date, species, location and source quality are credible.

### Source And Reliability

`observer.name` is optional.

`observer.expertise` is optional. Values are maintained in `catalogs.observer_expertise_levels`:

- `unknown`
- `beginner`
- `experienced`
- `expert`

`source.type` is optional but recommended. Values are maintained in `catalogs.observation_source_types`:

- `personal_observation`
- `trusted_observer`
- `whatsapp`
- `telegram`
- `social_media`
- `forum`
- `imported_dataset`
- `other`

`source_quality` is required. It is a number from `0.0` to `1.0` that represents source reliability before validation state is applied.

Suggested examples:

- `0.95`: own observation with exact coordinates.
- `0.90`: trusted expert observer.
- `0.70`: reliable verbal report.
- `0.40`: generic social media or group report.
- `0.20`: rumor or weakly attributable report.

### Validation

`validation_status` is required. Values are maintained in `catalogs.observation_validation_statuses`:

- `draft`
- `valid`
- `doubtful`
- `invalid`

The catalog also stores the `calibration_multiplier` used by calibration:

| Status | Multiplier |
| --- | ---: |
| `valid` | 1.00 |
| `draft` | 0.50 |
| `doubtful` | 0.25 |
| `invalid` | 0.00 |

`source_quality` and `validation_status` are deliberately separate. Source quality says how reliable the report source is; validation status says how much Rainmapper accepts the observation.

### Calibration Use

`calibration_use` is required and controls whether a valid observation enters calibration.

Allowed values are maintained in `catalogs.observation_calibration_uses`:

- `include`: use for calibration.
- `exclude`: do not use for calibration.
- `review`: not decided yet.

This is not the same as `validation_status`. A record can be valid but excluded because it is too imprecise, duplicated, outside the model area, or not a wild observation.

`calibration_exclusion_reason` is optional. Values are maintained in `catalogs.observation_exclusion_reasons`:

- `location_too_imprecise`
- `species_uncertain`
- `cultivated_or_market`
- `duplicate`
- `outside_model_area`
- `invalid_date`
- `other`

### Site Context

`site_context` is optional. The first structured site field is:

- `observed_host_ids`: up to 3 trees/hosts observed in the field, as IDs from `catalogs.host_taxa`.

This field describes what the observer saw at the point, not what GIS inferred. It can be compared with species `host_affinities` and, later, with host or forest-type features inferred from official GIS layers.

The remaining fields are free-text notes:

- `habitat_notes`
- `host_notes`
- `soil_notes`
- `aspect_notes`

These notes should not duplicate catalog-backed species affinities. They describe what was observed at this specific site.

### Metadata

`metadata.created_at`, `metadata.updated_at`, `metadata.created_by`, `metadata.reviewed_by` and `metadata.reviewed_at` support audit and maintenance.

## Calibration Weight

The first calibration pass can compute an effective observation weight from:

```text
effective_weight = source_quality * validation_multiplier
```

Then `calibration_use` decides whether the weighted observation is included, excluded, or left for review.

## UI Requirements

- Create observations quickly with the minimal required fields.
- Accept Google Maps URLs or decimal coordinates in one input.
- Store the original pasted location in `location.input`.
- Parse to decimal WGS84 coordinates.
- Offer `Recover altitude` from coordinates.
- Show flush abundance as an ordered selector, not a numeric field.
- Show `source_quality` as a percentage or 0-1 control.
- Keep advanced context fields optional and collapsible.
- Surface records missing coordinates, species, date or calibration decision as requiring review.
