"""Watch an operator-selected note folder and rebuild a private local preview."""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.mcp.vault_notes import VaultNotes
from scripts.mcp.build_demo import build


def refresh(notes, output):
    output = output.expanduser().absolute()
    # Prevent accidental private builds in the public source/deployment trees.
    try:
        output.relative_to(ROOT / 'out')
    except ValueError:
        raise ValueError('Private previews must be under this checkout’s ignored out/ directory')
    if any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError('Preview path must not use symlinks')
    marker = '.private-vault-preview'
    if output.exists() and not (output / marker).is_file():
        raise ValueError('Refusing to replace an unmanaged directory')
    snapshot, errors = notes.snapshot()
    if errors:
        raise ValueError('Fix invalid notes before refreshing: ' + json.dumps(errors))
    digest = hashlib.sha256(json.dumps(snapshot['entries'], sort_keys=True).encode())
    for name in ('index.html', 'note.html', 'styles.css', 'research.js'):
        digest.update((ROOT / 'web' / name).read_bytes())
    digest.update((ROOT / 'scripts/mcp/build_demo.py').read_bytes())
    revision = digest.hexdigest()
    if output.exists() and (output / marker).read_text() == revision:
        return 'unchanged'
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name('.preview-' + uuid4().hex)
    backup = output.with_name('.old-preview-' + uuid4().hex)
    try:
        build(temporary, snapshot=snapshot)
        (temporary / marker).write_text(revision)
        (temporary / 'preview-revision.json').write_text(json.dumps(revision))
        index = temporary / 'index.html'
        reload_script = ('<script>setInterval(async()=>{try{const r=await fetch("preview-revision.json",'
                         '{cache:"no-store"});if(r.ok && await r.json()!==%s)location.reload();}'
                         'catch(e){}},3000)</script>' % json.dumps(revision))
        index.write_text(index.read_text().replace('</body>', reload_script + '</body>'))
        if output.exists():
            output.rename(backup)
        try:
            temporary.rename(output)
        except Exception:
            if backup.exists():
                backup.rename(output)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return 'updated'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--notes-vault', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'out/private-notes-preview')
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--interval', type=float, default=3)
    parser.add_argument('--approved-output', type=Path,
                        help='Explicitly export approved snapshots instead of building a private preview')
    args = parser.parse_args()
    if args.interval < 1:
        parser.error('Interval must be at least one second')
    if args.approved_output and args.watch:
        parser.error('Public exports are explicit one-shot actions, never automatic watch output')
    notes = VaultNotes(args.notes_vault)
    if args.approved_output:
        snapshot, _ = notes.snapshot(public=True)
        args.approved_output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.approved_output.with_name('.public-' + uuid4().hex + '.json')
        temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n')
        os.replace(temporary, args.approved_output)
        print('Exported only approved snapshots. Build/push/deploy remains explicit.')
        return
    while True:
        try:
            status = refresh(notes, args.output)
            if status != 'unchanged':
                print(status + ': ' + str(args.output), flush=True)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            if not args.watch:
                raise
            print('Preview unchanged: ' + str(exc), file=sys.stderr, flush=True)
        if not args.watch:
            break
        time.sleep(args.interval)


if __name__ == '__main__':
    main()
