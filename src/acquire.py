"""Restore exact provider snapshots; never accept changed bytes as frozen evidence."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def save_verified(path, payload, expected_sha256):
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError(f'Snapshot differs from recorded SHA-256: {path.name}')
    # Exclusive creation protects any existing snapshot.
    with path.open('xb') as output:
        output.write(payload)


def sources():
    raw = ROOT / 'data/raw'
    records = json.loads((raw / 'manifest.json').read_text())
    for manifest in ['revision_manifest.json', 'additional_capacity_sources_manifest.json']:
        for record in json.loads((raw / manifest).read_text()):
            name = Path(record.get('file', record.get('path'))).name
            records[name] = record
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', help='Verify local snapshots without network access')
    args = parser.parse_args()
    failures = []
    for name, record in sources().items():
        path = ROOT / 'data/raw' / name
        try:
            if path.exists():
                if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
                    raise ValueError('local snapshot checksum mismatch')
            elif args.verify:
                raise FileNotFoundError('snapshot missing')
            else:
                url = record.get('resolved_url') or record['url']
                request = Request(url, headers={'User-Agent': 'ResourceAudit/1.0'})
                with urlopen(request, timeout=60) as response:
                    save_verified(path, response.read(), record['sha256'])
            print(f'Verified {name}')
        except (OSError, ValueError) as error:
            failures.append(name)
            print(f'UNAVAILABLE {name}: {error}')
    if failures:
        raise SystemExit(f'{len(failures)} snapshots unavailable. See DATA_AVAILABILITY.md; no hashes were changed.')


if __name__ == '__main__':
    main()
