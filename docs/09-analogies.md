# 09 · The analogies: every feature, the reason for it, and what it does not do

This is the page for anyone who is not a chip designer. Each row is one feature of the
Safety Governor, the everyday thing it works like, the reason it is there, and the honest
limit. The blog series uses the same pictures, so a reader can move between the posts and the
design without learning a new vocabulary.

## The big picture

| Idea | In plain words |
|---|---|
| The model is not the guard | A brilliant employee with no alarm bell wired in. You do not fix that with a smarter employee. You wire in the bell |
| Guard the wire, not the thoughts | A stadium with eighty thousand people shouting. You cannot police the shouting. There is one gate onto the field. Guard the gate |
| The governor | James Watt's brass balls on the spinning shaft: when the engine runs too fast they fly out and close the steam valve. No operator can talk them out of it |
| One governor per GPU | A lifeguard per pool, not one lifeguard for the whole water park |
| Governors wired together | All the lifeguards on the same whistle |
| Added through the rack's boards | The security office rents the room next door that every building already has, instead of asking the landlord to knock a hole in the wall |
| Holding the switches | The governor does not stand in the corridor checking parcels; it holds the keys to the doors between the buildings, and the doors only open for people on the roll |

## Identity and trust

| Feature | Works like | Why it is there | What it does not do |
|---|---|---|---|
| Fused device secret | A birth certificate burned into the chip at the factory | So the chip's identity cannot be copied or edited | Does not survive a fab that lies about the birth certificate |
| Measured boot and DICE key | A house key cut from the shape of the house; change the house and the key stops fitting | So modified firmware cannot sign as the real firmware | Does not prove the firmware is good, only that it is the firmware it claims |
| Anti-rollback counter | An odometer that only counts up | So an old, weaker firmware or policy cannot be loaded back | Cannot tell a good update from a bad one; only an older from a newer |
| Local attestation verifier | The bouncer carries the photo book himself | So the governor does not have to phone a cloud service to know whether its GPU is genuine | Only as good as the photo book (the reference values) it was given |
| Fused-off debug port | The service hatch is welded shut after the factory | So nobody can open the chip up in the field | Makes the chip harder to repair; that is the point |
| Tamper mesh and glitch detectors | A safe that shreds its contents when the door is forced | So extracting keys costs a lab and a week, not a screwdriver and an hour | Does not stop a lab with a month |

## Rules

| Feature | Works like | Why it is there | What it does not do |
|---|---|---|---|
| Policy image signed by k of n keys | A rulebook that takes three of five board members to change | So one person cannot loosen the rules alone | Does not make the rules wise |
| Policy epoch | The edition number printed on the rulebook; tickets printed under an old edition are void | So a rule change takes effect everywhere at once and old permissions die | Needs the edition to reach every governor, which is what the fabric is for |
| Default deny | Every door locked unless a rule opens it | So the model's power is bounded by the rulebook, not by its manners | A rulebook with a gap is a gap |
| Lanes (auto, observer, human) | Airport security: everyone goes through; the rulebook, not the traveler, picks the quick lane or the full search | So trillions of harmless actions stay fast and the rare dangerous one gets the full check | The traveler who looks harmless and is not is the observer lane's problem, not the gate's |
| The assumptions register | The list taped to the wall: who may tell us this, how old can it be, what if two sources disagree, what can we not check | So the guarantee is stated exactly as far as it holds and not an inch further | Does not make a stale map current |

## Permissions

| Feature | Works like | Why it is there | What it does not do |
|---|---|---|---|
| Ticket | A concert ticket: one seat, one show, torn at the door, no good after the date | So a permission cannot be reused, moved to another action, or kept past the rules that issued it | Does not decide whether the show should be happening |
| Reserve, then commit | One cashier per cash drawer; the money is set aside before the receipt is printed | So two requests at the same instant cannot both spend the same allowance | Does not stop a thousand small, individually permitted spends unless the rule sets a budget |
| Used-ticket store that survives power loss | The torn stub is remembered even after the lights go out and come back | So a ticket cannot be replayed after a restart | Fills up; it is sized for a year and checkpointed |
| Hold and approvers | Two keys on a missile console, turned together by two people who cannot reach both | So the highest-stakes actions need several humans, slowly, on the record | Slow on purpose; a fast override would make the lower layers worthless |
| Alarms that only go up | Anyone can pull the fire alarm; only the fire marshal can reset it | So a false alarm is cheap and clearing one is expensive | More alarms mean more stops, and a stop is not always safe; each device defines its safe move |

## Stopping

| Feature | Works like | Why it is there | What it does not do |
|---|---|---|---|
| Heartbeat | The dead man's switch on a train: let go of the handle and the brakes come on | So silence from the authority, or a cut cable, ends in a stop rather than in "carry on" | Makes an outage out of a lost connection; that is the chosen trade |
| Halt loop | The fire-alarm loop through the whole building: pull any station and every bell rings; cut the wire and every bell rings too | So a stop reaches every GPU at once, through a wire with no software in the way | Carries the stop, not the reason; the fabric carries the reason |
| Throttle, reset, power cut | The brake pedal, the ignition key, the breaker in the basement | Three rungs, from reversible to final, so the safe move fits the device | The governor cannot climb back up a rung by itself |
| Safe transition per device | A train just stops; a plane glides; a surgical robot withdraws | Because "do nothing" is itself a hazard for some devices | Choosing the move is an engineering job for each device |

## Containment and provenance

| Feature | Works like | Why it is there | What it does not do |
|---|---|---|---|
| Enforcement points at the switches | The doors between buildings, with the governor holding the keys | So no byte reaches a GPU that is not on the roll, and nothing moves when the heartbeat stops, at no cost to the work inside | Two people on the roll can still pass a parcel the rulebook did not anticipate; that is the named residual, and the future in-GPU checkers are the answer to it |
| Roster-bound links | The bus unlocks its doors only for people on the roll | So a GPU talks over NVLink only to GPUs that passed the same check | Does not stop two legitimate peers from doing something foolish together |
| Bricked paths | Windows bricked up on the ground floor | So a path nobody can check is not assumed safe | Costs a display engine and a debug port in production |
| Output signing | The courier signs for the package | So you can prove which chip, firmware, model and rulebook produced some bytes | Does not prove what is in the box; that is workload provenance and execution integrity, two separate claims |
| Output budgets | A turnstile that counts | So a model cannot leak its weights slowly through the front door without tripping a counter | Does not make the front door safe; it makes the leak measurable and limited |
| Metering | The taxi meter | So compute use is counted per model, read-only, for licensing and audit | Does not say what the compute was for |

## The cluster

| Feature | Works like | Why it is there | What it does not do |
|---|---|---|---|
| Message fabric | The building's intercom, separate from the tenants' Wi-Fi | So governors can share rosters, editions, heartbeats and budgets without the host or the data network touching the messages | Carries no model data and no tool calls |
| Roster | Roll call with ID badges before the bus leaves | So every later decision is scoped to GPUs that passed the check | A perfect clone with a stolen badge gets on the bus; that is a supply-chain problem |
| Cluster-atomic epoch change | The new rulebook is handed out, everyone initials receipt, and only then does the manager say "from now"; anyone who did not initial is sent home | So the rules change everywhere at once and nobody keeps working from the old book | Sends GPUs home; availability is the cost |
| Shared budgets | One cashier per cash drawer, even across buildings | So forty governors cannot each spend the last dollar | Adds a round trip for shared allowances |
| Cross-linked logs | Each security office writes the last line of the neighbors' log books into its own | So rewriting history means rewriting everyone's | Does not stop everyone colluding |

## Building it

| Step | Works like |
|---|---|
| The functional model (`govsim`) | A tabletop model of the building with little badge readers you can push with a pencil |
| The RTL | The architect's drawings, exact to the brick |
| The shuttle run | Sharing a bus to the fab with other riders so the trip costs thousands, not millions |
| GDS, masks, lithography | The drawings become a set of negatives; the fab makes stencils from them and prints the chip layer by layer like a forty-exposure photograph |
| Known-good-die test, then fuses | The part is tested with the service hatch open, then the hatch is welded shut |
| The module in the rack | The security office moves into the room next door, with the keys to the doors between the buildings |
