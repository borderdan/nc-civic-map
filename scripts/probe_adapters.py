import httpx
import json
import time
import datetime
import os

TIMEOUT = 10.0

def polite_sleep():
    time.sleep(1)

def probe_url(url, method="GET", follow_redirects=True, client=None):
    if client is None:
        try:
            with httpx.Client(timeout=TIMEOUT, follow_redirects=follow_redirects) as c:
                if method.upper() == "HEAD":
                    return c.head(url)
                else:
                    return c.get(url)
        except httpx.RequestError:
            return None
    else:
        try:
            if method.upper() == "HEAD":
                return client.head(url)
            else:
                return client.get(url)
        except httpx.RequestError:
            return None

def check_primary_domains():
    candidates = [
        "https://charmeck.org",
        "https://mecknc.gov",
        "https://www.mecklenburgcountync.gov",
        "https://www.mecknc.gov"
    ]
    primary_domain = None
    primary_domain_status = None
    alt_domains = []

    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        for url in candidates:
            print(f"Probing primary domain: {url}")
            resp = probe_url(url, method="GET", client=client)
            if resp and resp.status_code == 200:
                if not primary_domain:
                    primary_domain = str(resp.url)
                    primary_domain_status = 200
                else:
                    alt_domains.append(str(resp.url))
            polite_sleep()

    return primary_domain, primary_domain_status, alt_domains

def probe_legistar():
    slugs = ["mecklenburg", "mecklenburgnc", "mecknc", "mecklenburgcountync"]
    result = {
        "status": 404,
        "tenant_slug": None,
        "endpoint": None,
        "bodies_count": 0,
        "verified_real": False,
        "sample_bodies": [],
        "notes": "All slugs failed."
    }

    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        for slug in slugs:
            url = f"https://webapi.legistar.com/v1/{slug}/Bodies"
            print(f"Probing Legistar: {url}")
            resp = probe_url(url, method="GET", client=client)
            if resp and resp.status_code == 200:
                try:
                    data = resp.json()
                    if isinstance(data, list):
                        result["status"] = 200
                        result["tenant_slug"] = slug
                        result["endpoint"] = url
                        result["bodies_count"] = len(data)
                        result["verified_real"] = True
                        result["sample_bodies"] = [b.get("BodyName", "") for b in data[:5] if isinstance(b, dict)]
                        result["notes"] = f"Found valid endpoint with {len(data)} bodies."
                        break
                except ValueError:
                    pass
            polite_sleep()

    return result

def probe_civicclerk():
    slugs = ["mecklenburg", "mecknc", "mecklenburgnc", "mecklenburgcountync"]
    result = {
        "status": 404,
        "tenant_slug": None,
        "endpoint": None,
        "verified_real": False,
        "notes": "All slugs failed."
    }

    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        for slug in slugs:
            events_url = f"https://{slug}.api.civicclerk.com/v1/Events?$top=1"
            bodies_url = f"https://{slug}.api.civicclerk.com/v1/Bodies"

            print(f"Probing CivicClerk Events: {events_url}")
            resp_events = probe_url(events_url, method="GET", client=client)
            polite_sleep()

            print(f"Probing CivicClerk Bodies: {bodies_url}")
            resp_bodies = probe_url(bodies_url, method="GET", client=client)
            polite_sleep()

            events_ok = resp_events and resp_events.status_code == 200
            bodies_ok = resp_bodies and resp_bodies.status_code == 200

            if events_ok or bodies_ok:
                result["status"] = 200
                result["tenant_slug"] = slug
                result["endpoint"] = bodies_url if bodies_ok else events_url

                if bodies_ok:
                    try:
                        data = resp_bodies.json()
                        if isinstance(data, list) and len(data) > 0:
                            result["verified_real"] = True
                            result["notes"] = f"Found valid endpoint with bodies data. Sample bodies count: {len(data)}"
                        elif isinstance(data, dict) and data.get("items") and len(data.get("items", [])) > 0:
                            result["verified_real"] = True
                            result["notes"] = f"Found valid endpoint with bodies data. Sample bodies count: {len(data.get('items', []))}"
                        else:
                            result["verified_real"] = False
                            result["notes"] = "Events endpoint OK, but Bodies endpoint returned empty list (video-only tenant)."
                    except ValueError:
                        result["notes"] = "Failed to parse Bodies response JSON."
                else:
                    result["verified_real"] = False
                    result["notes"] = "Events endpoint OK, but Bodies endpoint failed (video-only tenant)."
                break

    return result

def probe_weblink(verify_ssl=False):
    candidates = [
        "https://weblink.mecknc.gov",
        "https://records.mecknc.gov",
        "https://weblink.mecklenburgcountync.gov",
        "https://weblink.charmeck.org"
    ]
    result = {"status": 404, "endpoint": None, "notes": "All candidates failed."}

    if not verify_ssl:
        print("WARNING: SSL verification is disabled for WebLink probes. This silently accepts invalid/self-signed certs.")

    with httpx.Client(timeout=TIMEOUT, follow_redirects=True, verify=verify_ssl) as client:
        for url in candidates:
            print(f"Probing WebLink: {url}")
            resp = probe_url(url, method="HEAD", client=client)
            if not resp or resp.status_code >= 400:
                resp = probe_url(url, method="GET", client=client)

            if resp and resp.status_code < 400:
                result["status"] = resp.status_code
                result["endpoint"] = url
                result["notes"] = f"Found valid WebLink endpoint at {url}."
                break
            polite_sleep()

    return result

def probe_granicus_video():
    candidates = [
        "https://mecknc.granicus.com",
        "https://mecklenburg.granicus.com",
        "https://mecklenburgcountync.granicus.com"
    ]
    result = {"status": 404, "endpoint": None, "notes": "All candidates failed."}

    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        for url in candidates:
            print(f"Probing Granicus Video: {url}")
            resp = probe_url(url, method="HEAD", client=client)
            if not resp or resp.status_code >= 400:
                resp = probe_url(url, method="GET", client=client)

            if resp and resp.status_code < 400:
                result["status"] = resp.status_code
                result["endpoint"] = url
                result["notes"] = f"Found valid Granicus video endpoint at {url}."
                break
            polite_sleep()

    return result

def probe_boarddocs():
    candidates = [
        "https://go.boarddocs.com/nc/cmsk12/Board.nsf/Public",
        "https://go.boarddocs.com/nc/mecknc/Board.nsf/Public"
    ]
    result = {"status": 404, "endpoint": None, "notes": "All candidates failed."}

    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        for url in candidates:
            print(f"Probing BoardDocs: {url}")
            resp = probe_url(url, method="HEAD", client=client)
            if not resp or resp.status_code >= 400:
                resp = probe_url(url, method="GET", client=client)

            if resp and resp.status_code < 400:
                result["status"] = resp.status_code
                result["endpoint"] = url
                result["notes"] = f"Found valid BoardDocs endpoint at {url}."
                break
            polite_sleep()

    return result

def probe_devnet():
    candidates = [
        "https://mecknc.devnetwedge.com",
        "https://mecklenburg.devnetwedge.com"
    ]
    result = {"status": 404, "endpoint": None, "notes": "All candidates failed."}

    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        for url in candidates:
            print(f"Probing DEVNET: {url}")
            resp = probe_url(url, method="HEAD", client=client)
            if not resp or resp.status_code >= 400:
                resp = probe_url(url, method="GET", client=client)

            if resp and resp.status_code < 400:
                result["status"] = resp.status_code
                result["endpoint"] = url
                result["notes"] = f"Found valid DEVNET endpoint at {url}."
                break
            polite_sleep()

    return result

def main():
    print("Starting probes for Mecklenburg County NC adapters...")

    primary_domain, primary_domain_status, alt_domains = check_primary_domains()

    results = {
        "primary_domain": primary_domain,
        "primary_domain_status": primary_domain_status,
        "alt_domains": alt_domains,
        "adapters": {
            "legistar": probe_legistar(),
            "civicclerk": probe_civicclerk(),
            "weblink": probe_weblink(),
            "granicus_video": probe_granicus_video(),
            "boarddocs": probe_boarddocs(),
            "devnet": probe_devnet()
        },
        "probed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    os.makedirs("meck-county", exist_ok=True)
    out_path = "meck-county/adapter_probes.json"

    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Probes complete. Results written to {out_path}.")

if __name__ == '__main__':
    main()
