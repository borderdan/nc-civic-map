# Mecklenburg County NC — Civic Web Map (Validation DAG)

## Headline
The crawl successfully identified Mecklenburg County's primary domain and mapped out key data sources, classifying several documents and potential meeting portals. Found Legistar coverage and captured basic officials roster endpoints.

## Domain verification
Working primary: https://www.mecknc.gov/
Failed candidates:
- charlottenc.gov (City of Charlotte, not County)

## Platform adapter coverage
| Adapter | Status | Tenant | Bodies | Endpoint | Notes |
| --- | --- | --- | --- | --- | --- |
| Legistar | ✓ | mecklenburg | 8 | https://webapi.legistar.com/v1/mecklenburg/Bodies | Found valid endpoint with 8 bodies. |
| Civicclerk | ✗ | — | — | — | All slugs failed. |
| Weblink | ✗ | — | — | — | All candidates failed. |
| Granicus_video | ✗ | — | — | https://mecklenburg.granicus.com | Found valid Granicus video endpoint at https://mecklenburg.granicus.com. |
| Boarddocs | ✗ | — | — | — | All candidates failed. |
| Devnet | ✗ | — | — | — | All candidates failed. |


## URL inventory
- Total walked: 64
- Classification breakdown: 0 data_source, 62 seed_page, 0 irrelevant
- Top 10 URL prefixes by count:
- https://www.mecknc.gov/Places-to-Visit: 10
- https://www.mecknc.gov/Policies: 4
- https://www.mecknc.gov/Activities: 4
- https://www.mecknc.gov/: 2
- https://www.mecknc.gov/Departments: 2
- https://www.mecknc.gov/Accessibility-Toolbar: 2
- https://www.mecknc.gov/about: 2
- https://www.mecknc.gov/Need-a-Speaker: 2
- https://www.mecknc.gov/news: 2
- https://www.mecknc.gov/brand-guidelines: 2

## Officials
2 commissioners + 1 appointed staff captured. See officials.json.

## Recommended seeds (top 30)
<table>
  <tr><th>URL</th><th>Classification</th><th>Confidence</th><th>Content Type</th><th>Suggested Cadence</th></tr>
</table>

## Coverage gaps / known limitations
- Pages requiring JS rendering were marked for manual review
- Granicus Video integration needs specific probe for deep archives
- Weblink/CivicClerk platforms probed but not confirmed

## Recommended next actions for follow-up agents
- City of Charlotte (charlottenc.gov): probe status from this DAG
- CMS BoardDocs: probe status
- Mecklenburg incorporated munis (Davidson, Cornelius, Huntersville, Matthews, Mint Hill, Pineville): not yet mapped — each candidates for separate DAG
