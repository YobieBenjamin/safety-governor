# The brief

`chip-that-says-no-brief.pptx` is an eighteen-slide talk built in pairs: every topic gets a
plain slide with an analogy and a picture, then a technical slide. The topics, in order: what
the project is, the thesis, the logic behind it, the proposal, the six layers, how the
governor meets the model (one action start to finish), where it stands, the challenges, and
what is needed to prove or disprove the thesis. Speaker notes on every slide.

The pictures: the smoke alarm and the fire door (witness and lock), the customs officer who
cannot read the paperwork, the referee with a whistle and a rulebook he did not write, the
bank with its board, teller, guard and vault, the boarding pass, the firewall at the
building's edge, and the bridge whose drawings are done before the steel is ordered.

It is generated, not hand-made: `node docs/brief/build_deck.js [out.pptx]` rebuilds it with
pptxgenjs (one theme, two layouts, named placeholders, sections, notes). The theme colours
are applied by `apply_theme.js` from the pptx skill; set `PPTX_APPLY_THEME` to its path, or
the deck builds in Office's stock palette. Every number on the status slide comes from the
repository: `python -m pytest tests rtl/tests`, `make loop`, `hw/README.md`, and the
reference stack's `./run.sh`.
