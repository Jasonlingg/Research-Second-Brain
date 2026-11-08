# Import existing research files

Import specific Markdown notes or JSON exports into Envoy's existing experiment
store. No model or network calls are made. Source text stays unreviewed; JSON
values are not inferred to be validated measurements, plans or outcomes.

## Preview, then apply

From the repository root:

```bash
python scripts/mcp/import_memory.py preview \
  --source-root /path/to/research \
  --file notes/lora.md --file results/batching.json
```

Preview lists paths, hashes, excerpts and draft titles without writing records,
snapshots or destination directories. It does not scan the folder. Inspect that
output, then apply the same selection with its `preview_sha256`:

```bash
python scripts/mcp/import_memory.py apply \
  --source-root /path/to/research \
  --file notes/lora.md --file results/batching.json \
  --preview-sha256 REPLACE_WITH_PREVIEW_HASH
```

Both commands accept `--store-root` and `--library-root`. Defaults match the
server: `~/.envoy/ml-experiments` and `~/.envoy/arxiv-library`. Use your server's
configured paths when they differ.

## Through MCP

Add `--import-root /path/to/research` to the current server's launch arguments.
Restart the connection. Two tools become available:

- `preview_memory_import(paths)` reads only explicitly selected relative paths
- `apply_memory_import(paths, preview_sha256)` saves that exact inspected preview

The root is operator-selected at startup, not supplied by a tool call. Preview
returns source excerpts to your assistant. Apply creates one draft per file;
titles use a Markdown H1 when present, otherwise the filename. No research
question or interpretation is inferred from a title. Read the imported text and
receipts using `get_experiment`, and search it using `find_related_experiments`.

Successful MCP saves refresh the Obsidian view when configured. CLI imports
require the existing manual export/refresh command to update that view.

## Preservation and limits

- Original UTF-8 text, file hashes and bounded chunks are saved immutably under
  `LIBRARY_ROOT/envoy-imports/`; source files are not modified
- Identical retries reuse the existing record and preserve subsequent edits
- A changed file needs a new preview and creates a separate record; older records
  are retained, with no inferred supersession or automatic synchronization
- A batch reports each saved or failed file separately; successful records survive
  another file's failure, and a retry is safe
- Select up to ten `.md` or `.json` files per batch, each at most 64 KiB and
  24,000 characters; invalid batches fail validation before snapshot writes
- Hidden files, directory scans and symlinks are rejected; Envoy-generated pages
  are rejected when importing from its generated vault root

Import personal Obsidian notes explicitly. This is snapshot ingestion, not
two-way vault synchronization. Recall still uses lexical overlap and cannot
reliably infer synonyms, chronology or contradictory conclusions.

The initial end-to-end check used three synthetic source files, four positive
lexical queries and one absent-topic query. All four expected records ranked
first; the absent topic returned no matches. These are controlled engineering
fixtures, not an independent relevance benchmark or demonstrated workflow gain.
