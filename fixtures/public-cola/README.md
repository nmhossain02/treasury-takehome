# Public COLA test inputs

Run `make samples` to reconstruct the optional public-label evaluation photos pinned in `manifest.json`. The set covers seven metadata records and sixteen front, back, neck, or panel images across rum, tequila, a prepared cocktail, cachaça, bourbon, and Canadian whisky.

These images are test inputs, not database content. The deployable metadata database is built independently from `records.lock.json` and contains no images or OCR output; see `docs/public-cola-index.md`. Label artwork may contain third-party intellectual property, so downloaded originals under `images/` remain excluded from Git. Exact Registry filenames and SHA-256 hashes make reconstruction fail closed if an upstream image changes. Approve/deny actions are local and never contact TTB or alter a public record.
