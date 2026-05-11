import pandas as pd
import json
import re
import asyncio
from crawl4ai import AsyncWebCrawler
from selectolax.parser import HTMLParser

def classify_urls(csv_path):
    df = pd.read_csv(csv_path)

    classifications = []
    confidences = []
    methods = []

    for url in df['url']:
        classification = "seed_page"
        confidence = 0.50
        method = "pattern-based"

        url_lower = str(url).lower()

        if url_lower.endswith('.pdf'):
            classification = "data_source"
            confidence = 0.95
        elif "/documentcenter/view/" in url_lower:
            classification = "data_source"
            confidence = 0.90
        elif re.search(r'/(agenda|minutes|budget|cip|ordinance)', url_lower):
            classification = "data_source"
            confidence = 0.85
        elif re.search(r'/(contract|rfp|bid|procurement)', url_lower):
            classification = "data_source"
            confidence = 0.85
        elif re.search(r'/(council|committee|department|board|commissioners)', url_lower):
            classification = "seed_page"
            confidence = 0.80
        elif re.search(r'/(search|sitemap|login|accessibility)', url_lower):
            classification = "navigation_chrome"
            confidence = 0.85
        elif "/civicalerts.aspx" in url_lower:
            classification = "news_or_announcement"
            confidence = 0.85
        elif re.search(r'\.(jpg|png|css|js|woff|svg|ico)$', url_lower):
            classification = "irrelevant"
            confidence = 0.95

        classifications.append(classification)
        confidences.append(confidence)
        methods.append(method)

    df['classification'] = classifications
    df['classifier_confidence'] = confidences
    df['classifier_method'] = methods

    df.to_csv(csv_path, index=False)
    return df

async def do_scrape_officials(df, output_path):
    boc_pattern = re.compile(r'/(board-of-commissioners|commissioners|elected-officials|county-commissioners|boc|board)', re.IGNORECASE)
    manager_pattern = re.compile(r'/county-manager', re.IGNORECASE)

    boc_urls = []
    manager_urls = []

    for _, row in df.iterrows():
        url = str(row['url'])
        if boc_pattern.search(url):
            boc_urls.append((url, row.get('classifier_confidence', 0.5)))
        elif manager_pattern.search(url):
            manager_urls.append((url, row.get('classifier_confidence', 0.5)))

    boc_urls.sort(key=lambda x: x[1], reverse=True)
    manager_urls.sort(key=lambda x: x[1], reverse=True)

    if not boc_urls:
        boc_urls = [('https://bocc.mecknc.gov/', 1.0)]

    if not manager_urls:
         manager_urls = [('https://www.mecknc.gov/county-managers-office', 1.0)]

    officials = []

    if boc_urls:
        best_boc_url = boc_urls[0][0]
        print(f"Scraping BoC from: {best_boc_url}")

        try:
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=best_boc_url)
                html = result.html
                if html:
                    parser = HTMLParser(html)
                    text_content = parser.text(separator=' ')

                    found = False
                    matches = re.findall(r'([A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z]\.?)?)[^A-Za-z0-9]*(?:County )?Commissioner[^A-Za-z0-9]*(?:District \d+)?', text_content)

                    for match in set(matches):
                        if match.strip().lower() in ["county manager", "board of", "mecklenburg county"]:
                             continue

                        context_start = max(0, text_content.find(match) - 50)
                        context_end = min(len(text_content), text_content.find(match) + 100)
                        context = text_content[context_start:context_end]

                        district_match = re.search(r'District\s*(\d+)', context, re.IGNORECASE)
                        role = f"Commissioner — District {district_match.group(1)}" if district_match else "Commissioner"

                        term_match = re.search(r'Term:\s*([0-9]{4}(?:\s*-\s*[0-9]{4})?)', context, re.IGNORECASE)
                        term_start = term_match.group(1) if term_match else ""

                        officials.append({
                            "name": match.strip(),
                            "role": role,
                            "term_start": term_start,
                            "source_url": best_boc_url,
                            "extraction_method": "page-parse"
                        })
                        found = True

                    if not found:
                         for node in parser.css('.item, .person, .profile, .member, .card'):
                              text = node.text(separator=' ')
                              if "Commissioner" in text:
                                   name_match = re.search(r'([A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z]\.?)?)', text)
                                   district_match = re.search(r'District\s*(\d+)', text, re.IGNORECASE)
                                   term_match = re.search(r'Term:\s*([0-9]{4}(?:\s*-\s*[0-9]{4})?)', text, re.IGNORECASE)

                                   if name_match:
                                        role = f"Commissioner — District {district_match.group(1)}" if district_match else "Commissioner"
                                        officials.append({
                                            "name": name_match.group(1),
                                            "role": role,
                                            "term_start": term_match.group(1) if term_match else "",
                                            "source_url": best_boc_url,
                                            "extraction_method": "page-parse"
                                        })
                                        found = True
                else:
                    officials.append({
                        "source_url": best_boc_url,
                        "extraction_method": "manual-review-needed"
                    })
        except Exception as e:
            print(f"Failed to crawl {best_boc_url}: {e}")
            officials.append({
                "source_url": best_boc_url,
                "extraction_method": "manual-review-needed"
            })

    if manager_urls:
        best_manager_url = manager_urls[0][0]
        print(f"Scraping Manager from: {best_manager_url}")
        try:
             async with AsyncWebCrawler() as crawler:
                 result = await crawler.arun(url=best_manager_url)
                 if result.html:
                     parser = HTMLParser(result.html)
                     text_content = parser.text(separator=' ')

                     match = re.search(r'([A-Z][a-z]+ [A-Z]\.? [A-Z][a-z]+|[A-Z][a-z]+ [A-Z][a-z]+)[^a-zA-Z0-9]*County Manager', text_content)
                     if not match:
                          match = re.search(r'County Manager[^a-zA-Z0-9]*([A-Z][a-z]+ [A-Z]\.? [A-Z][a-z]+|[A-Z][a-z]+ [A-Z][a-z]+)', text_content)

                     if match:
                         name = match.group(1).strip()
                         officials.append({
                              "name": name,
                              "role": "County Manager",
                              "source_url": best_manager_url,
                              "extraction_method": "page-parse"
                         })
                     else:
                         officials.append({
                              "source_url": best_manager_url,
                              "extraction_method": "manual-review-needed"
                         })
                 else:
                     officials.append({
                          "source_url": best_manager_url,
                          "extraction_method": "manual-review-needed"
                     })
        except Exception as e:
            print(f"Failed to crawl {best_boc_url}: {e}")
            officials.append({
                "source_url": best_boc_url,
                "extraction_method": "manual-review-needed"
            })

    with open(output_path, 'w') as f:
        json.dump(officials, f, indent=2)

def scrape_officials(df, output_path):
    asyncio.run(do_scrape_officials(df, output_path))

if __name__ == '__main__':
    csv_file = 'meck-county/site_map_urls.csv'
    df = classify_urls(csv_file)
    scrape_officials(df, 'meck-county/officials.json')
