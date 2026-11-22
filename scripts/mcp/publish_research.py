"""Preview selected private MCP records; publish only an explicitly reviewed snapshot."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.mcp.ml_experiment_store import ExperimentStore
from src.mcp.experiment_atlas import ExperimentAtlas

FIELDS = {'id', 'kind', 'date', 'title', 'summary', 'status', 'detail', 'next_check',
          'source_label', 'source_url', 'memory_id'}
SCOPE = ('Explicitly selected public summaries from research memory and saved experiments. '
         'A published snapshot, not live access to private notes. Dates are record dates, '
         'not necessarily original sharing or publication dates.')


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def fingerprint(value):
    return hashlib.sha256(encode(value)).hexdigest()


def read(path):
    if path.is_symlink() or path.stat().st_size > 1_000_000:
        raise ValueError('Expected a bounded regular JSON preview')
    return json.loads(path.read_text())


def source(kind, identity, store, atlas):
    if kind == 'memory':
        stores = store if isinstance(store, list) else [store]
        matches = [s for s in stores if (s.files.root / f'{identity}.json').is_file()]
        if len(matches) != 1:
            raise ValueError('Selected record must exist in exactly one supplied store')
        return matches[0].get(identity)
    if kind == 'atlas':
        return atlas.get(identity)
    raise ValueError('Unknown source kind')


def preview(store, atlas, experiment_ids, atlas_ids):
    selections = [('memory', i) for i in experiment_ids] + [('atlas', i) for i in atlas_ids]
    if not 1 <= len(selections) <= 20 or len(set(selections)) != len(selections):
        raise ValueError('Select 1..20 unique records explicitly')
    entries, receipts = [], []
    for kind, identity in selections:
        record = source(kind, identity, store, atlas)
        receipts.append({'kind': kind, 'identity': identity, 'sha256': fingerprint(record)})
        if kind == 'memory':
            brief = record['brief']
            latest = record.get('selected_research_note')
            note = latest['note'] if latest else None
            texts = [f['claim'] for f in note['findings']] if note else [o['text'] for o in brief['observations']]
            refs = note['references'] if note else brief['references']
            url = next((r['url'] for r in refs if r['kind'] == 'external_reference'), None)
            entries.append(dict(id=identity, kind='Exploring', date=record['revisions'][-1]['recorded_at'][:10],
                title=brief['question'], summary=' '.join(texts)[:600] or 'Draft research question; no findings recorded.',
                status='Unreviewed saved memory', detail=' '.join(brief['limitations'])[:1200],
                next_check=(note.get('proposed_test') if note else None) or brief.get('proposed_change') or 'Not specified',
                source_label='Saved research memory · inspect sources before relying on claims', source_url=url, memory_id=identity))
        else:
            entries.append(dict(id=identity, kind='Experiment', date='', title=record['attempt'],
                summary=record['observation'], status='Curated historical summary · inspect primary evidence',
                detail='This is a historical atlas entry, not a new evaluation.', next_check=record['decision'],
                source_label='Experiment atlas and primary evidence',
                source_url='https://github.com/Jasonlingg/Research-Second-Brain/blob/main/docs/EXPERIMENT_ATLAS.md', memory_id=None))
    return {'warning': 'PRIVATE PREVIEW: may contain private text. Edit public entries before publishing. Do not commit this file.',
            'sources': receipts, 'public': {'updated_at': datetime.now(timezone.utc).date().isoformat(), 'scope': SCOPE, 'entries': entries}}


def publish(packet, digest, store, atlas, output):
    if fingerprint(packet) != digest:
        raise ValueError('Preview changed; inspect it again and use its new review hash')
    for receipt in packet['sources']:
        current = source(receipt['kind'], receipt['identity'], store, atlas)
        if fingerprint(current) != receipt['sha256']:
            raise ValueError('Source changed since preview; generate a new preview')
    public = packet['public']
    if set(public) != {'updated_at', 'scope', 'entries'} or not 1 <= len(public['entries']) <= 20:
        raise ValueError('Invalid public snapshot')
    selected = {r['identity']: r['kind'] for r in packet['sources']}
    if not selected or len(selected) != len(packet['sources']):
        raise ValueError('Missing or duplicate selected sources')
    ids = set()
    for entry in public['entries']:
        if set(entry) != FIELDS or entry['id'] in ids:
            raise ValueError('Unexpected public fields or duplicate ID')
        if entry['id'] not in selected:
            raise ValueError('Public entry was not selected from memory or atlas')
        if entry['memory_id'] != (entry['id'] if selected[entry['id']] == 'memory' else None):
            raise ValueError('Public memory identity does not match its selected source')
        ids.add(entry['id'])
        if any(not isinstance(entry[k], str) for k in FIELDS - {'source_url', 'memory_id'}):
            raise ValueError('Public text fields must be strings')
        if entry['source_url'] is not None and (not isinstance(entry['source_url'], str) or not entry['source_url'].startswith('https://')):
            raise ValueError('Public source URLs must use HTTPS')
        if entry['memory_id'] is not None and not isinstance(entry['memory_id'], str):
            raise ValueError('Invalid memory ID')
        if entry['kind'] not in {'Exploring', 'Experiment'}:
            raise ValueError('Invalid entry kind')
    # Receipts, private paths and unselected records are deliberately excluded.
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + '.pending')
    with temporary.open('xb') as stream:
        stream.write(encode(public))
    temporary.replace(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store-root', type=Path, action='append', help='Explicit private record store; repeat for multiple stores')
    commands = parser.add_subparsers(dest='command', required=True)
    make = commands.add_parser('preview')
    make.add_argument('--experiment-id', action='append', default=[])
    make.add_argument('--atlas-id', action='append', default=[])
    make.add_argument('--output', type=Path, required=True)
    review = commands.add_parser('review')
    review.add_argument('preview', type=Path)
    apply = commands.add_parser('publish')
    apply.add_argument('preview', type=Path)
    apply.add_argument('--review-sha256', required=True)
    apply.add_argument('--output', type=Path, default=ROOT / 'web/research.json')
    args = parser.parse_args()
    if args.command == 'review':
        packet = read(args.preview)
        print(json.dumps(packet['public'], ensure_ascii=False, indent=2))
        print('Review SHA-256:', fingerprint(packet))
        return
    store = [ExperimentStore(p.expanduser()) for p in (args.store_root or [Path('~/.envoy/ml-experiments')])]
    atlas = ExperimentAtlas(ROOT)
    if args.command == 'preview':
        packet = preview(store, atlas, args.experiment_id, args.atlas_id)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('xb') as stream:
            stream.write(encode(packet))
        print('Private preview saved. Inspect/edit it, then run review before publishing.')
    else:
        publish(read(args.preview), args.review_sha256, store, atlas, args.output)
        print('Public snapshot written. Deployment remains a separate explicit step.')


if __name__ == '__main__':
    main()
