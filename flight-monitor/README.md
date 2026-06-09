# flightmon — Nordic budget flight monitor

Watches for cheap **round-trip** fares to the Nordic countries (plus Iceland
and Greenland) for a **flexible 3–4 night** trip, and alerts you when a fare
drops under your budget or hits a historic low for that route.

It pairs the cheapest outbound fare on each date with the cheapest return
exactly 3 or 4 nights later, so every alerted price is a real, bookable
itinerary — not a one-way teaser.

## Why these defaults

- **Origins:** Basel (BSL) and Milan-Bergamo (BGY) — both Ryanair bases
  reachable from Switzerland. Add Zurich (ZRH) once Amadeus is enabled.
- **Targets:** Copenhagen, Billund, Aalborg, Stockholm (Arlanda + Skavsta),
  Oslo (main + Torp), Gothenburg, Helsinki, Tampere. Iceland (KEF) and
  Greenland (Nuuk/GOH) are included with **higher** thresholds because they
  are rarely cheap — you only want to hear about them on a genuine deal.
- **Opportunity =** round-trip ≤ €100 (€120 Iceland, €350 Greenland) **OR** a
  new historic low for the route.

Tune all of this in `config.yaml`.

## Install

```bash
cd flight-monitor
uv sync                 # or: pip install -e .
```

## Run

```bash
uv run flightmon once                  # single scan
uv run flightmon watch --interval 60   # rescan every 60 minutes
uv run flightmon -c config.yaml once   # explicit config path
```

Found deals print to the console and append to `deals.csv`. Full price
history is kept in `flightmon.db` (SQLite) so historic-low detection improves
the longer it runs.

## Data sources

### Ryanair (default, no key)
Uses the unofficial [`ryanair-py`](https://pypi.org/project/ryanair-py/)
cheapest-fare API. Covers mainland Nordic airports. **Ryanair does not fly to
Iceland or Greenland**, so KEF/GOH are skipped by this provider.

### Amadeus (optional — needed for Iceland/Greenland, SAS/Finnair, etc.)
1. Create a free app at <https://developers.amadeus.com>.
2. Export credentials and enable the provider:
   ```bash
   export AMADEUS_CLIENT_ID=...
   export AMADEUS_CLIENT_SECRET=...
   export AMADEUS_HOST=production   # omit for the free test sandbox
   ```
3. Add `amadeus` under `providers:` in `config.yaml`.

Amadeus charges per request and needs concrete dates, so it samples one
candidate departure per week (Wednesdays — typically cheapest) rather than
sweeping every day.

## Alerts

Console + CSV are always on. To also push to Telegram or email, flip
`enabled: true` in `config.yaml` and provide secrets via env vars:

```bash
export FLIGHTMON_TG_TOKEN=...   FLIGHTMON_TG_CHAT=...     # Telegram bot
export FLIGHTMON_SMTP_USER=...  FLIGHTMON_SMTP_PASS=...   # email
```

## Scheduling (instead of `watch`)

A cron entry is more robust than a long-running process:

```cron
*/30 * * * * cd /path/to/flight-monitor && /path/to/uv run flightmon once >> scan.log 2>&1
```

## Tests

```bash
uv run pytest          # date pairing, store/historic-low, evaluate logic
```

## Notes & limits

- **`403 Forbidden` from Ryanair?** Ryanair blocks requests from cloud /
  datacenter IP ranges (AWS, GCP, CI runners, etc.). Run `flightmon` from a
  normal residential connection and it works. If you must run it on a server,
  route it through a residential/VPN egress, or use the Amadeus provider
  instead. The provider fails soft per-route, so a blocked scan finds nothing
  rather than crashing.
- `ryanair-py` is unofficial; Ryanair may change endpoints. The provider fails
  soft per-route so one broken route won't stop the scan.
- Prices are indicative base fares; bags/seats are extra.
- Be polite with request frequency — hourly scans are plenty for fare moves.
