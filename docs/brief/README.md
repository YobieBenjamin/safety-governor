# The brief

`chip-that-says-no-brief.pptx` is a ten-slide talk: thesis, the logic behind it, the proposal,
the six layers, how the governor meets the model (one action start to finish, as a flow chart),
where it stands, the challenges, and what is needed to prove or disprove the thesis.

It is generated, not hand-made: `node docs/brief/build_deck.js [out.pptx]` rebuilds it with
pptxgenjs (one theme, two layouts, named placeholders, sections, speaker notes). The theme
colours are applied by `apply_theme.js` from the pptx skill; set `PPTX_APPLY_THEME` to its
path, or the deck builds in Office's stock palette. Every number on the evidence slide comes
from the repository: `python -m pytest tests rtl/tests`, `make loop`, `hw/README.md`, and the
reference stack's `./run.sh`.
