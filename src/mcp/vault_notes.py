"""Authoritative Markdown notes and exact-content publication approvals."""
import hashlib
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from src.mcp.ml_experiment_io import LocalFiles


class Note(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=300)
    kind: Literal['Exploring', 'Experiment'] = 'Exploring'
    summary: str = Field(min_length=1, max_length=3000)
    detail: str = Field(min_length=1, max_length=30000)
    next_check: str = Field(default='Not specified', max_length=3000)
    source_label: str = Field(default='Source not supplied', max_length=1000)
    source_url: str | None = Field(default=None, max_length=2000)
    shared_at: str | None = Field(default=None, max_length=100)
    source_published_at: str | None = Field(default=None, max_length=100)
    status: str = Field(default='Unreviewed research note', max_length=300)
    origin_record_id: str | None = Field(default=None, max_length=100)
    capture_basis: str | None = Field(default=None, max_length=1000)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique_mapping(loader, node):
    pairs = loader.construct_pairs(node)
    if any(not isinstance(key, str) for key, _ in pairs):
        raise ValueError('Frontmatter keys must be strings')
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError('Duplicate frontmatter field')
    return dict(pairs)


class Loader(yaml.SafeLoader):
    pass


Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


class VaultNotes:
    def __init__(self, root):
        self.files = LocalFiles(Path(root))
        if (self.files.root / '.envoy-research-vault').exists():
            raise ValueError('Use a personal note folder, not a generated reading vault')

    @staticmethod
    def name(identity):
        if not re.fullmatch(r'note_[0-9a-f]{32}', identity):
            raise ValueError('Invalid note ID')
        return identity + '.md'

    @staticmethod
    def read(directory, name):
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
                raise ValueError('Note must be a regular file below 64 KiB')
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                raw = stream.read(65537)
            if len(raw) > 65536:
                raise ValueError('Note exceeds 64 KiB')
            return raw
        finally:
            os.close(fd)

    @staticmethod
    def write(directory, name, raw):
        temporary = '.write-' + uuid4().hex
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
        finally:
            try:
                os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError:
                pass

    def parse(self, identity, raw):
        text = raw.decode('utf-8')
        if not text.startswith('---\n') or '\n---\n' not in text[4:]:
            raise ValueError('Missing YAML frontmatter')
        header, body = text[4:].split('\n---\n', 1)
        if any(isinstance(token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken)) for token in yaml.scan(header)):
            raise ValueError('YAML anchors are not supported')
        meta = yaml.load(header, Loader=Loader)
        if not isinstance(meta, dict) or meta.get('id') != identity:
            raise ValueError('Note filename and frontmatter ID disagree')
        created, updated = meta.pop('created_at'), meta.pop('updated_at')
        meta.pop('id')
        for timestamp in (created, updated):
            if not isinstance(timestamp, str) or datetime.fromisoformat(timestamp).tzinfo is None:
                raise ValueError('Note timestamps need explicit timezones')
        note = Note.model_validate({**meta, 'detail': body.strip()})
        if note.source_url and not note.source_url.startswith('https://'):
            raise ValueError('Source URL must be HTTPS')
        return {'id': identity, 'sha256': sha(raw), 'created_at': created, 'updated_at': updated,
                'note': note.model_dump(), 'path': str(self.files.root / self.name(identity))}

    def get(self, identity):
        with self.files.locked() as directory:
            return self.parse(identity, self.read(directory, self.name(identity)))

    def save(self, note, identity=None, expected_sha256=None):
        parsed = Note.model_validate(note)
        if parsed.source_url and not parsed.source_url.startswith('https://'):
            raise ValueError('Source URL must be HTTPS')
        identity = identity or 'note_' + uuid4().hex
        name = self.name(identity)
        now = datetime.now(timezone.utc).isoformat()
        with self.files.locked() as directory:
            try:
                old = self.parse(identity, self.read(directory, name))
            except FileNotFoundError:
                old = None
            if (old and expected_sha256 != old['sha256']) or (not old and expected_sha256):
                raise ValueError('Stale note hash; read the current note before editing')
            data = parsed.model_dump()
            body = data.pop('detail')
            if old:
                data['shared_at'] = old['note']['shared_at']
            header = {'id': identity, 'created_at': old['created_at'] if old else now,
                      'updated_at': now, **data}
            raw = ('---\n' + yaml.safe_dump(header, sort_keys=False, allow_unicode=True) + '---\n\n' + body + '\n').encode()
            if len(raw) > 65536:
                raise ValueError('Note exceeds 64 KiB')
            self.write(directory, name, raw)
            return self.parse(identity, raw)

    def scan(self, query=''):
        if len(query) > 300:
            raise ValueError('Search query exceeds 300 characters')
        matches, errors = [], []
        with self.files.locked() as directory:
            names = sorted(n for n in os.listdir(directory) if n.startswith('note_') and n.endswith('.md'))
            if len(names) > 500:
                raise ValueError('Note folder exceeds 500 notes')
            for name in names:
                try:
                    identity = name[:-3]
                    self.name(identity)
                    record = self.parse(identity, self.read(directory, name))
                    terms = query.lower().split()
                    if all(term in json.dumps(record['note'], ensure_ascii=False).lower() for term in terms):
                        matches.append(record)
                except (ValueError, OSError, KeyError, UnicodeError, yaml.YAMLError) as exc:
                    errors.append({'file': name, 'error': str(exc)[:200]})
        return {'matches': matches, 'errors': errors}

    @staticmethod
    def public(record):
        note = record['note']
        return dict(id=record['id'], kind=note['kind'], date=(note['shared_at'] or record['created_at'])[:10],
                    title=note['title'], summary=note['summary'], detail=note['detail'],
                    next_check=note['next_check'], status=note['status'], source_label=note['source_label'],
                    source_url=note['source_url'], memory_id=record['id'])

    def approve(self, identity, expected_sha256, revoke=False):
        with self.files.locked() as directory:
            self.name(identity)
            state = self._approvals(directory)
            if revoke and identity in state and expected_sha256 == state[identity]['sha256']:
                state.pop(identity)
                self.write(directory, '.publication.json', json.dumps(state, ensure_ascii=False).encode())
                return {'id': identity, 'status': 'revoked',
                        'warning': 'Export and redeploy to remove previously published copies.'}
            record = self.parse(identity, self.read(directory, self.name(identity)))
            if expected_sha256 != record['sha256']:
                raise ValueError('Note changed; inspect its current content before approving')
            if revoke:
                state.pop(identity, None)
            else:
                state[identity] = {'sha256': expected_sha256, 'entry': self.public(record)}
            raw = json.dumps(state, ensure_ascii=False).encode()
            if len(raw) > 65536:
                raise ValueError('Publication approvals exceed 64 KiB')
            self.write(directory, '.publication.json', raw)
            return {'id': identity, 'approved_sha256': None if revoke else expected_sha256,
                    'status': 'revoked' if revoke else 'approved_snapshot',
                    'warning': 'Approval does not deploy. Later edits remain private until reapproved.'}

    def _approvals(self, directory):
        try:
            return json.loads(self.read(directory, '.publication.json'))
        except FileNotFoundError:
            return {}

    def snapshot(self, public=False):
        if public:
            with self.files.locked() as directory:
                entries = [value['entry'] for value in self._approvals(directory).values()]
            errors = []
        else:
            scan = self.scan()
            entries, errors = [self.public(r) for r in scan['matches']], scan['errors']
        return {'updated_at': datetime.now(timezone.utc).date().isoformat(),
                'scope': 'Approved exact-content snapshots; subsequent edits are private.' if public else 'PRIVATE vault preview — never deploy this directory.',
                'entries': entries}, errors
