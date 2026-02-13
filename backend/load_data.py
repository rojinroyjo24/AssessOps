"""
Data Loader Script - Loads attempt_events.json into the platform via API.

Reads the sample data file and sends it to the ingestion endpoint.
This can be run from inside the backend container or from the host.

Usage:
    python load_data.py                              # Uses default URL
    python load_data.py http://localhost:8000         # Custom API URL
    python load_data.py http://backend:8000           # Inside Docker network
"""

import json
import sys
import os

try:
    import httpx
except ImportError:
    print("httpx not available, falling back to urllib")
    import urllib.request
    import urllib.error

    def post_json(url, data):
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8')
            print(f"HTTP Error {e.code}: {body}")
            sys.exit(1)
else:
    def post_json(url, data):
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=data)
            resp.raise_for_status()
            return resp.json()


def main():
    # Determine API base URL
    api_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv("API_URL", "http://localhost:8000")
    ingest_url = f"{api_url}/api/ingest/attempts"

    # Locate the data file
    data_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "attempt_events.json")
    if not os.path.exists(data_file):
        # Try current directory
        data_file = "attempt_events.json"
    
    if not os.path.exists(data_file):
        print(f"Error: Could not find attempt_events.json")
        sys.exit(1)

    # Load events
    print(f"Loading data from: {data_file}")
    with open(data_file, 'r') as f:
        raw_events = json.load(f)
    
    # Transform nested structure to flat structure expected by API
    events = []
    for event in raw_events:
        transformed = {
            "event_id": event.get("source_event_id"),
            "student_name": event.get("student", {}).get("full_name"),
            "student_email": event.get("student", {}).get("email"),
            "student_phone": event.get("student", {}).get("phone"),
            "test_id": event.get("test", {}).get("name", "").replace(" ", "-").lower(),
            "test_name": event.get("test", {}).get("name"),
            "started_at": event.get("started_at"),
            "submitted_at": event.get("submitted_at"),
            "answers": event.get("answers", {}),
            "channel": event.get("channel", "unknown")
        }
        events.append(transformed)
    
    print(f"Found {len(events)} events to ingest")
    print(f"Sending to: {ingest_url}")
    print()

    # Send to API
    payload = {"events": events}
    result = post_json(ingest_url, payload)

    # Display results
    print("=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)
    print(f"  Total Received:      {result.get('total_received', '?')}")
    print(f"  Successfully Ingested: {result.get('ingested', '?')}")
    print(f"  Duplicates Detected:   {result.get('duplicates_detected', '?')}")
    print(f"  Scored:                {result.get('scored', '?')}")
    print(f"  Errors:                {result.get('errors', '?')}")
    print("=" * 60)
    print()
    
    # Print details
    details = result.get('details', [])
    for d in details:
        status = d.get('status', '?')
        event_id = d.get('event_id', '?')
        icon = '✅' if status == 'SCORED' else ('🔁' if status == 'DEDUPED' else '❌')
        extra = ''
        if status == 'SCORED':
            extra = f" (score: {d.get('score', '?')})"
        elif status == 'DEDUPED':
            extra = f" (canonical: {d.get('canonical_attempt_id', '?')[:8]}...)"
        elif status == 'ERROR':
            extra = f" ({d.get('reason', '?')})"
        print(f"  {icon} {event_id}: {status}{extra}")
    
    print()
    print("✅ Data loading complete! Visit http://localhost:3000 to view the dashboard.")


if __name__ == "__main__":
    main()
