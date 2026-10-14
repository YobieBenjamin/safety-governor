# The archive on claude.ai

GitHub holds the originals. This folder builds the copies that live on claude.ai, so the
work does not depend on any one place.

`make archive` runs both scripts:

| Script | Produces | Goes to |
|---|---|---|
| `build_archive.py` | `build/archive/`: every tracked file of both repositories at their current commits, a full git bundle of each (split into parts only if one would exceed the publisher's 15 MB per-file limit), a zip of each tracked tree, `index.html` (the table of contents, static), `manifest.json`, and `publish-files-N.json` (the file list for the publisher, 255 per call) | The artifact **Governor Program Archive** on claude.ai |
| `build_project_docs.py` | `build/project/`: the design documents joined into one text document per subject, each with a header naming the repository, the commit and the source files, with image links pointed at the archive artifact | The Project **Hardware and Silicon** on claude.ai, one `project_write` per document |

Both scripts refuse nothing silently: the archive builder requires clean trees (or
`--allow-dirty`), verifies every bundle, checks every file against the per-file limit and the
page against the 16 MB page limit; the documents builder checks that every source was used and
reports dashes carried in from older reference-stack text.

Restoring from the archive is on the page itself: fetch the bundles, `git bundle verify`, then
`git clone <name>-all.bundle <name>`. A Claude session can read any published file, bundles
included, straight from the artifact, so the repositories can be rebuilt from there even when
GitHub is not reachable.
