# Milestones

## v0.1 — Foundation (current)

Core library with dictionary I/O, pure-Python word counting, remote dictionary fetching, and LIWC-22 CLI wrapper. Released with full test suite, docs, and CI.

---

## v0.2 — Count Module Enhancements

- **Individual word count export.** Add an option to `count()` that returns per-token match details (which tokens matched which categories), not just category totals. Requires API design for the return type — likely a separate function or a flag that returns a second DataFrame alongside the summary.
- **`drop_category()` utility.** Standalone function that removes one or more category columns from a dictionary DataFrame and drops any terms that are no longer assigned to any remaining category. Keeps the DataFrame API clean until the dx class lands in v0.3.

## v0.3 — Dictionary Class

- **`Dictionary` class wrapping dx DataFrames.** Encapsulate dictionary metadata and operations in a class rather than passing raw DataFrames. Target API surface: `dx.categories`, `dx.terms`, `dx.count(texts)`, `dx.merge(other)`, `dx.drop_category(name)`, `dx.to_dic(path)`, `dx.to_dicx(path)`, `dx.citation`, `dx.filepath`. The underlying storage remains a DataFrame; the class adds discoverability and a natural home for methods like `drop_category`. Raw DataFrame access should still be possible for advanced users.

## v0.4 — Hierarchical Categories

- **Multi-level category support.** LIWC dictionaries have nested category structures (e.g., Affect > Positive Emotion > Happy). Currently all categories are flat columns. Design a representation for category hierarchies within the `Dictionary` class — likely a tree or mapping alongside the DataFrame — so users can query at any level. This is the most design-heavy milestone; prototyping against the LIWC-22 default dictionary structure will be important.

## v0.5 — Performance

- **Memory-efficient counting pipeline.** For large corpora, the current approach materializes everything in memory. Add a streaming mode that processes documents in batches and optionally writes results directly to a file (CSV/Parquet) without holding the full result DataFrame in memory. Should support both in-memory and streaming paths so small-corpus convenience is preserved.

## v1.0 — Stable Release

Final API review, migration guide from v0.x, and commitment to semantic versioning stability.
