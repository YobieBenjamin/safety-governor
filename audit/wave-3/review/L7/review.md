## Review of `exp/l7`: **revise** (the model review could not be trusted; a person decides)

Verifier: clean; model review on ?: 0 blocking, 0 warnings, 0 unsupported claim(s) of 0; estimated $0.91, 13 turns.

### suite in a clean checkout: exit 0

```
........................................................................ [ 31%]
........................................................................ [ 63%]
........................................................................ [ 95%]
...........                                                              [100%]
227 passed in 2.96s

```

### acceptance in a clean checkout: exit 0

```
python3 rtl/formal/run_formal.py
SKIP    tooling absent: sby, yosys not on PATH (the program's container has sby/yosys-smtbmc/z3). No property was checked; run `make formal` in the container to run them.
SKIP    ticket_store:prove
SKIP    epoch_reg:prove
SKIP    halt_seq:prove
SKIP    cap_table:prove
SKIP    monotonic_counter:prove
SKIP    monotonic_counter:wrap
SKIP    mailbox:prove
SKIP    mailbox:nolatch
SKIP    mailbox:midhalt
SKIP    equiv:ticket_store
SKIP    equiv:epoch_reg
SKIP    equiv:halt_seq
SKIP    equiv:cap_table
SKIP    equiv:monotonic_counter
SKIP    equiv:mailbox
SKIP    15 job(s) not run (tools absent). A SKIP is not a PROVED; run in the container to check the properties.

```
