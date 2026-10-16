# The brief

`chip-that-says-no-brief.pptx` is an eighteen-slide talk built in pairs: every topic gets a
plain slide with an analogy and a picture, then a technical slide. The topics, in order: what
the project is, the thesis, the logic behind it, the proposal, the six layers, how the
governor meets the model (one action start to finish), where it stands, the challenges, and
what is needed to prove or disprove the thesis. Speaker notes on every slide.

The pictures are the program's own: the judge model that can keep a gate shut but never be
the gate, the customs officer who cannot read the paperwork, the referee with a whistle and a
rulebook he did not write, biology's reflex that never fires the muscle by itself, the ticket
whose hash breaks when the amount changes, the perimeter firewall that decides what leaves but
not what the far server does. `SOURCES.md` traces every number, mechanism and picture on the
slides to the document, test or post it comes from, and lists what was removed from earlier
drafts for not being from the research.

`chip-that-says-no-brief.pdf` is the same deck rendered to PDF, the reference for how it is
meant to look in any viewer.

It is generated, not hand-made: `node docs/brief/build_deck.js [out.pptx]` rebuilds it with
pptxgenjs (one theme, two layouts, named placeholders, sections, notes). Tables are drawn as
shapes with row heights computed from the text, so every viewer shows the same geometry; the
fonts are Georgia and Arial, which exist on Windows, Mac and iPhone. The theme colours
are applied by `apply_theme.js` from the pptx skill; set `PPTX_APPLY_THEME` to its path, or
the deck builds in Office's stock palette. Every number on the status slide comes from the
repository: `python -m pytest tests rtl/tests`, `make loop`, `hw/README.md`, and the
reference stack's `./run.sh`.
