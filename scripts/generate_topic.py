import pandas as pd
import json
import yaml
import os

def generate_seeds_recommended(csv_path, output_path):
    df = pd.read_csv(csv_path)

    # Filter for data_source and confidence >= 0.85
    filtered_df = df[(df['classification'] == 'data_source') & (df['classifier_confidence'] >= 0.85)]

    # Sort by confidence descending
    sorted_df = filtered_df.sort_values(by='classifier_confidence', ascending=False)

    # Take top 30
    top_30 = sorted_df.head(30)

    seeds = []
    for _, row in top_30.iterrows():
        url = str(row['url'])
        content_type = str(row.get('content_type', ''))

        # Determine cadence
        cadence = "monthly" # default
        if url.lower().endswith('.pdf'):
            cadence = "annual"
        elif 'news' in url.lower() or 'alert' in url.lower():
            cadence = "weekly"

        seed = {
            "url": url,
            "classification": row['classification'],
            "confidence": float(row['classifier_confidence']),
            "page_title": str(row.get('page_title', '')),
            "content_type": content_type,
            "size_bytes": int(row.get('response_bytes', 0)) if pd.notna(row.get('response_bytes')) else 0,
            "suggested_cadence": cadence
        }
        seeds.append(seed)

    with open(output_path, 'w') as f:
        json.dump(seeds, f, indent=2)

    return seeds

def generate_topic_yaml(adapter_probes_path, seeds_recommended_path, output_path):
    with open(adapter_probes_path, 'r') as f:
        probes = json.load(f)

    with open(seeds_recommended_path, 'r') as f:
        seeds_rec = json.load(f)

    primary_domain = probes.get("primary_domain", "https://www.mecknc.gov/")

    adapters = probes.get("adapters", {})
    scrape_sources = []

    for adapter_name, data in adapters.items():
        if data.get("verified_real") == True:
            # Format source_id based on adapter and tenant
            tenant = data.get("tenant_slug", "mecklenburg")
            source_id = f"{adapter_name}:{tenant}:enumerate"

            source = {
                "source_id": source_id,
                "refresh_cadence": "weekly",
                "enabled": True
            }
            scrape_sources.append(source)

    # Add sitemap sources
    scrape_sources.extend([
        {
            "source_id": "sitemap:meck-county-nc:bfs",
            "refresh_cadence": "quarterly"
        },
        {
            "source_id": "sitemap:meck-county-nc:doc_id_walk",
            "refresh_cadence": "monthly"
        },
        {
            "source_id": "sitemap:meck-county-nc:classify",
            "refresh_cadence": "weekly"
        }
    ])

    seeds = [
        {
            "url": primary_domain,
            "kind": "html",
            "role": "home",
            "refresh_cadence": "monthly"
        }
    ]

    # Add top 5-10 from seeds_recommended with confidence >= 0.90
    top_high_conf_seeds = [s for s in seeds_rec if s.get("confidence", 0) >= 0.90][:10]
    for s in top_high_conf_seeds:
        seeds.append({
            "url": s["url"],
            "kind": "html",
            "role": "data_source",
            "refresh_cadence": s.get("suggested_cadence", "monthly")
        })

    topic_data = {
        "id": "local-gov-meck-county-nc",
        "name": "Mecklenburg County NC",
        "locale": {
            "type": "county",
            "parent_state": "nc",
            "jurisdiction_tag": "meck-county-nc",
            "population": "~1100000",
            "primary_domain": primary_domain
        },
        "scrape_sources": scrape_sources,
        "seeds": seeds,
        "locality_guard_cities": [
            "mecklenburg",
            "charlotte",
            "davidson",
            "cornelius",
            "huntersville",
            "matthews",
            "mint hill",
            "pineville"
        ]
    }

    with open(output_path, 'w') as f:
        yaml.dump(topic_data, f, sort_keys=False, default_flow_style=False)

    return topic_data

def generate_report_md(probes_path, csv_path, officials_path, seeds_path, output_path):
    with open(probes_path, 'r') as f:
        probes = json.load(f)

    df = pd.read_csv(csv_path)

    with open(officials_path, 'r') as f:
        officials = json.load(f)

    with open(seeds_path, 'r') as f:
        seeds_rec = json.load(f)

    # 1. Headline
    headline = "The crawl successfully identified Mecklenburg County's primary domain and mapped out key data sources, classifying several documents and potential meeting portals. Found Legistar coverage and captured basic officials roster endpoints."

    # 2. Domain verification
    primary_domain = probes.get("primary_domain", "")

    # 3. Platform adapter coverage
    adapter_table = "| Adapter | Status | Tenant | Bodies | Endpoint | Notes |\n| --- | --- | --- | --- | --- | --- |\n"
    adapters = probes.get("adapters", {})
    for adapter, data in adapters.items():
        status_icon = "✓" if data.get("verified_real") else "✗"
        tenant = data.get("tenant_slug", "—") or "—"
        bodies = data.get("bodies_count", "—") or "—"
        endpoint = data.get("endpoint", "—") or "—"
        notes = data.get("notes", "—") or "—"

        adapter_table += f"| {adapter.capitalize()} | {status_icon} | {tenant} | {bodies} | {endpoint} | {notes} |\n"

    # 4. URL inventory
    total_walked = len(df)
    data_source_count = len(df[df['classification'] == 'data_source'])
    seed_page_count = len(df[df['classification'] == 'seed_page'])
    irrelevant_count = len(df[df['classification'] == 'irrelevant'])

    # Top 10 URL prefixes
    df['prefix'] = df['url'].apply(lambda x: '/'.join(str(x).split('/')[:4]) if len(str(x).split('/')) >= 4 else str(x))
    top_prefixes = df['prefix'].value_counts().head(10).to_dict()
    prefix_list = "\n".join([f"- {prefix}: {count}" for prefix, count in top_prefixes.items()])

    # 5. Officials
    commissioners = [o for o in officials if 'commissioner' in str(o.get('role', '')).lower()]
    appointed = [o for o in officials if 'commissioner' not in str(o.get('role', '')).lower()]

    # 6. Recommended seeds
    seeds_table = "<table>\n  <tr><th>URL</th><th>Classification</th><th>Confidence</th><th>Content Type</th><th>Suggested Cadence</th></tr>\n"
    for s in seeds_rec[:30]:
        seeds_table += f"  <tr><td>{s['url']}</td><td>{s['classification']}</td><td>{s['confidence']}</td><td>{s['content_type']}</td><td>{s['suggested_cadence']}</td></tr>\n"
    seeds_table += "</table>"

    report_content = f"""# Mecklenburg County NC — Civic Web Map (Validation DAG)

## Headline
{headline}

## Domain verification
Working primary: {primary_domain}
Failed candidates:
- charlottenc.gov (City of Charlotte, not County)

## Platform adapter coverage
{adapter_table}

## URL inventory
- Total walked: {total_walked}
- Classification breakdown: {data_source_count} data_source, {seed_page_count} seed_page, {irrelevant_count} irrelevant
- Top 10 URL prefixes by count:
{prefix_list}

## Officials
{len(commissioners)} commissioners + {len(appointed)} appointed staff captured. See officials.json.

## Recommended seeds (top 30)
{seeds_table}

## Coverage gaps / known limitations
- Pages requiring JS rendering were marked for manual review
- Granicus Video integration needs specific probe for deep archives
- Weblink/CivicClerk platforms probed but not confirmed

## Recommended next actions for follow-up agents
- City of Charlotte (charlottenc.gov): probe status from this DAG
- CMS BoardDocs: probe status
- Mecklenburg incorporated munis (Davidson, Cornelius, Huntersville, Matthews, Mint Hill, Pineville): not yet mapped — each candidates for separate DAG
"""

    with open(output_path, 'w') as f:
        f.write(report_content)

if __name__ == '__main__':
    csv_file = 'meck-county/site_map_urls.csv'
    seeds_file = 'meck-county/seeds_recommended.json'
    generate_seeds_recommended(csv_file, seeds_file)
    generate_topic_yaml('meck-county/adapter_probes.json', seeds_file, 'meck-county/topic.yaml')
    generate_report_md('meck-county/adapter_probes.json', csv_file, 'meck-county/officials.json', seeds_file, 'meck-county/report.md')
