"""Command-line interface.

  usuk sources            list corpus sources and their download status
  usuk fetch [ID ...]     download sources (all by default; cached)
  usuk index              extract text, chunk, and build the hybrid index
  usuk ask "question"     answer a question with citations
"""

import argparse
import sys


def cmd_sources(args) -> int:
    from .manifest import load_sources

    for s in load_sources():
        status = "cached" if s.raw_path.exists() else "missing"
        print(f"  [{status:7}] {s.id:38} {s.jurisdiction:7} {s.title}")
    return 0


def cmd_fetch(args) -> int:
    from .ingest import fetch
    from .manifest import load_sources

    sources = load_sources()
    if args.ids:
        wanted = set(args.ids)
        unknown = wanted - {s.id for s in sources}
        if unknown:
            print(f"Unknown source ids: {sorted(unknown)}", file=sys.stderr)
            return 1
        sources = [s for s in sources if s.id in wanted]

    failures = 0
    for s in sources:
        try:
            downloaded = fetch(s, force=args.force)
            print(f"  [{'fetched' if downloaded else 'cached '}] {s.id}")
        except Exception as e:
            failures += 1
            print(f"  [FAILED ] {s.id}: {e}", file=sys.stderr)
    if failures:
        print(f"\n{failures} download(s) failed — fix the manifest URL or retry.", file=sys.stderr)
    return 1 if failures else 0


def cmd_index(args) -> int:
    from .chunking import chunk_source
    from .index import build_index
    from .ingest import extract_text
    from .manifest import load_sources

    chunks = []
    skipped = []
    for s in load_sources():
        if not s.raw_path.exists():
            skipped.append(s.id)
            continue
        text = extract_text(s, force=args.force)
        source_chunks = chunk_source(s, text)
        chunks.extend(source_chunks)
        print(f"  {s.id}: {len(source_chunks)} chunks")
    if skipped:
        print(f"\nSkipped (not downloaded): {', '.join(skipped)}", file=sys.stderr)
    if not chunks:
        print("Nothing to index — run `usuk fetch` first.", file=sys.stderr)
        return 1
    print(f"\nEmbedding and indexing {len(chunks)} chunks (first run downloads a small local embedding model)...")
    build_index(chunks)
    print("Done.")
    return 0


def cmd_workbook(args) -> int:
    from pathlib import Path

    from .calc import build_workbook
    from .config import PRIVATE_DIR, ROOT

    if args.path:
        path = Path(args.path)
    elif args.template:
        path = ROOT / "spreadsheets" / "template_2025.xlsx"
    else:
        path = (PRIVATE_DIR or ROOT / "spreadsheets") / "taxes_2025.xlsx"
    if path.exists() and not args.force:
        print(f"{path} already exists — pass --force to overwrite.", file=sys.stderr)
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    build_workbook(path)
    print(f"Wrote {path}")
    return 0


def cmd_estimate(args) -> int:
    from pathlib import Path

    from .config import PRIVATE_DIR
    from .estimate import run

    base = PRIVATE_DIR or Path.cwd()
    inputs = Path(args.inputs) if args.inputs else base / f"inputs_{args.year}.yaml"
    if not inputs.exists():
        print(f"{inputs} not found — set USUK_PRIVATE_DIR or pass --inputs.", file=sys.stderr)
        return 1
    _, report = run(inputs)
    out = inputs.with_name(f"estimate_{args.year}.md")
    out.write_text(report)
    print(report)
    print(f"Wrote {out}")
    return 0


def cmd_ask(args) -> int:
    from .research import ask

    ask(args.question, k=args.k, show_passages=args.show_passages)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="usuk", description="US/UK expat tax research tool (not tax advice)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("sources", help="list corpus sources and status").set_defaults(func=cmd_sources)

    p = sub.add_parser("fetch", help="download corpus sources")
    p.add_argument("ids", nargs="*", help="specific source ids (default: all)")
    p.add_argument("--force", action="store_true", help="re-download even if cached")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("index", help="extract, chunk, and index the corpus")
    p.add_argument("--force", action="store_true", help="re-extract text from raw files")
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("workbook", help="generate the tax-year calculation workbook (Excel)")
    p.add_argument("path", nargs="?", help="output path (default: $USUK_PRIVATE_DIR/taxes_2025.xlsx, else spreadsheets/)")
    p.add_argument("--force", action="store_true", help="overwrite an existing workbook")
    p.add_argument(
        "--template",
        action="store_true",
        help="write the git-tracked blank template (template_2025.xlsx) instead of a personal working copy",
    )
    p.set_defaults(func=cmd_workbook)

    p = sub.add_parser("ask", help="ask a tax question")
    p.add_argument("question")
    p.add_argument("-k", type=int, default=12, help="number of passages to retrieve (default 12)")
    p.add_argument("--show-passages", action="store_true", help="print retrieved passages first")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("estimate", help="US federal estimate from the private inputs YAML")
    p.add_argument("--year", type=int, default=2025)
    p.add_argument("--inputs", help="inputs file (default: $USUK_PRIVATE_DIR/inputs_<year>.yaml)")
    p.set_defaults(func=cmd_estimate)

    args = parser.parse_args()
    sys.exit(args.func(args))
