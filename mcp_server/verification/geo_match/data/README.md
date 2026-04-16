---
date: 2026-04-16
tags:
  - type/runbook
  - domain/verification
status: active
aliases: ["Geo Match Data", "Geo Dataset Refresh"]
related-files:
  - mcp_server/verification/geo_match/static_us.py
  - mcp_server/verification/geo_match/static_global.py
---

# geo_match datasets

This directory holds the static datasets consumed by the hybrid geo matcher
(see `docs/planning/MASTER_PLAN_GEO_MATCHING_2026_04_16.md`).

**These files are NOT committed** — they are large (~12 MB combined) and
regenerable. The repo's top-level `.gitignore` excludes them. The module
must boot successfully whether or not they are present; lookups silently
return `None` and the Nominatim fallback takes over.

## Expected files

| File | Size | Source | License |
|------|------|--------|---------|
| `us_zips.csv` | ~5 MB | [Simple Maps — US ZIP codes (free tier)](https://simplemaps.com/data/us-zips) | CC BY 4.0 (free tier) |
| `cities500.txt` | ~7 MB | [GeoNames cities500](https://download.geonames.org/export/dump/cities500.zip) | CC BY 4.0 |

The free tier of Simple Maps covers our needs (city / state / lat / lng /
population / county). No API key required — just download the CSV.

GeoNames `cities500.txt` is tab-separated, no header; all cities with
population >= 500. See `static_global.py` docstring for the full column list.

## Manual refresh

From the repository root:

```bash
cd mcp_server/verification/geo_match/data

# US ZIPs — Simple Maps free tier
# (Replace the URL if Simple Maps rotates the download; their site always
#  has a current free CSV.)
curl -L -o us_zips_raw.zip https://simplemaps.com/static/data/us-zips/1.86/basic/simplemaps_uszips_basicv1.86.zip
unzip -o us_zips_raw.zip "uszips.csv" -d .
mv uszips.csv us_zips.csv
rm us_zips_raw.zip

# GeoNames global cities >= population 500
curl -L -o cities500.zip https://download.geonames.org/export/dump/cities500.zip
unzip -o cities500.zip cities500.txt -d .
rm cities500.zip
```

Alternatively, a small Python one-liner for the GeoNames file:

```bash
python -c "
import io, urllib.request, zipfile
u = urllib.request.urlopen('https://download.geonames.org/export/dump/cities500.zip')
z = zipfile.ZipFile(io.BytesIO(u.read()))
z.extract('cities500.txt', '.')
"
```

## Verifying

The module logs an INFO line per loaded dataset on first lookup:

```
geo_match.static_us: loaded 33789 ZIP entries (27124 unique city/state pairs) from .../us_zips.csv
geo_match.static_global: loaded 199762 cities from .../cities500.txt
```

If you see WARNING lines instead, the files are missing or malformed.

## Refresh cadence

Quarterly is fine — cities rename and ZIPs shift, but not fast enough
to matter for matching workers to metropolitan areas.

## Out of scope

- An automated refresh job (cron / CI). Add one once the module lands in
  prod and we have a staging bucket to host refreshed files.
- A persistence cache for Nominatim responses. Planned as a separate
  `geo_cache` Supabase table (see master plan WS-3).
