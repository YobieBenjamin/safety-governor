# The brief

`chip-that-says-no-brief.pptx` is a thirty-two-slide talk built in pairs: every topic gets a
plain slide with an analogy and a picture, then a technical slide. The topics, in order: what
the project is and the five stages to a chip we cannot fab; the thesis; the ladder every safety
measure sits on, from a prompt that says "don't" to the chip to a person with a key; why there
is no kill switch for AI and why there is one at the ends (Menger's theorem, the five cuts
measured on the model, the proof in three claims, the check you can run); the logic behind it
and what is proven; the proposal, the module and the die, and how it plugs into NVIDIA's
OpenShell against the shipped middleware contract; the six layers; one bad prompt among a
billion, start to finish, and the inside of the chip; where it stands and what the first wave
of experiments found; the challenges and the prior art; what is needed to prove or disprove
the thesis. Speaker notes on every slide.

The pictures are the program's own: the judge model that can keep a gate shut but never be the
gate, the staircase of rungs, Menger's roads and guards, the customs officer who cannot read the
paperwork, the referee with a whistle and a rulebook he did not write, biology's reflex that
never fires the muscle by itself, the ticket whose hash breaks when the amount changes, the
perimeter firewall that decides what leaves but not what the far server does. `SOURCES.md`
traces every number, mechanism and picture on the slides to the document, test, proof or post
it comes from, and lists what was removed from earlier drafts for not being from the research.

`chip-that-says-no-brief.pdf` is the same deck rendered to PDF, the reference for how it is
meant to look in any viewer.

It is generated, not hand-made: `node docs/brief/build_deck.js [out.pptx]` rebuilds it with
pptxgenjs (one theme, two layouts, named placeholders, sections, notes). Tables and the two
flow charts are drawn as shapes with heights computed from the text, so every viewer shows the
same geometry; the fonts are Georgia and Arial, which exist on Windows, Mac and iPhone. The six
kill-switch figures under `figures/` are copies of the blog's (made by
`hardware-and-silicon/blog/tools/make_figures.py`); the build crops their title band so the
slide's own title is the only one. The theme colours are applied by `apply_theme.js` from the
pptx skill; set `PPTX_APPLY_THEME` to its path, or the deck builds in Office's stock palette.
Every number on the status slides comes from a command: `python -m pytest tests rtl/tests`,
`make proof`, `make loop`, `python3 proofs/no_global_kill_switch.py --percolation`, and the
reference stack's `./run.sh`.
