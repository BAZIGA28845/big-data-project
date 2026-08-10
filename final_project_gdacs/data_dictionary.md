# Data Dictionary — clean_gdacs

This describes each column in the cleaned dataset (`clean_gdacs` in PostgreSQL), the table
used for EDA, machine learning, and the Tableau dashboard in this project.

| Column | Type | What it means | Where it comes from |
|---|---|---|---|
| event_id | integer | Unique ID for each disaster event | GDACS `eventid` |
| event_type | text | Disaster type code: EQ = earthquake, FL = flood, TC = tropical cyclone, DR = drought, VO = volcano, WF = wildfire | GDACS `eventtype` |
| event_name | text | Name of the event, if GDACS gave it one. Often blank for smaller events — this is normal, not an error | GDACS `eventname` |
| alert_level | text | Either "Orange" or "Red". Green alerts were left out of this project on purpose (see README) | GDACS `alertlevel` |
| alert_score | numeric | GDACS's internal severity score. Not used as a model feature, since GDACS calculates alert_level directly from it | GDACS `alertscore` |
| country | text | Country or region name, with extra spaces removed | GDACS `country` |
| iso3 | text | 3-letter country code (e.g. RWA, KEN), used for matching countries on the Tableau map | GDACS `iso3` |
| from_date | timestamp | When the event started | GDACS `fromdate` |
| to_date | timestamp | When the event ended | GDACS `todate` |
| year | integer | The year, taken from from_date | Calculated during cleaning |
| latitude | numeric | Event location, latitude | GDACS `geometry.coordinates` |
| longitude | numeric | Event location, longitude | GDACS `geometry.coordinates` |
| severity_value | numeric | A measure of how strong the event was. What it means depends on the event type (e.g. magnitude for earthquakes) | GDACS `severitydata.severity` |
| severity_unit | text | The unit for severity_value (e.g. "M" for magnitude, "ha" for hectares) | GDACS `severitydata.severityunit` |
| loaded_at | timestamp | When this row was saved or last updated in the database | Added by the pipeline itself |

## Notes

- **population_value** was originally planned as a column but was removed. Checking the raw
  API data directly confirmed that GDACS's SEARCH endpoint never provides population exposure
  data for any event type in this dataset — it's a limitation of the API, not a bug in the
  pipeline.
- **Green alert events** are excluded from this entire project. GDACS's SEARCH endpoint
  leaves them out by default; testing showed that including them added over 10,000 extra
  (mostly minor) events for the same date range, which would have diluted the analysis. The
  project is scoped to Orange and Red events only.
- Each row represents one unique disaster event. GDACS sometimes reports the same event more
  than once as new information comes in (called episodes) — only the latest episode for each
  event is kept.
