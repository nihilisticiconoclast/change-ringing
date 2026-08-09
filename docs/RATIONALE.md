# Why change ringing

Change ringing is a permutation-group problem executed live, by ear, by a
team of people who can't see each other's next move and can't stop to check.
A method (e.g. Plain Bob Minimus, place notation `x14x14x14x12`) specifies how
a set of bells reorders itself on every row; a peal is 5,000+ rows with no
repeated order, rung without a break, over roughly three hours. There's no
score in front of the ringers and no log kept during the performance -- the
thing itself exists only as sound, once, and is judged in the instant by the
ringers' own ears. What survives afterwards is a peal report: date, tower,
method, and who rang which bell.

That's the opposite of a validated model: no held-out test, no ground truth,
no artefact except a report written up after the fact. The data around it,
though, is unusually complete and open:

- **Dove's Guide** (dove.cccbr.org.uk) -- bulk CSV of ~7,300 towers, bells,
  frames and founders, CC BY-SA 4.0.
- **CCCBR Methods Library** -- 20,000+ methods in a formal XML spec.
- **BellBoard** (bb.ringingworld.co.uk) -- a near-complete performance
  record since 2012, with an XML API.
- **CompLib** -- 25,000+ methods, 80,000+ compositions, an auto-proving
  engine, and its own API.

Nobody maintains a linked, queryable version of all of this together. The
tooling that exists is one-person, largely dormant (the Python bridge to the
Methods Library has been inactive since 2022). The gap isn't unfamiliarity --
it's that the social-historical layer (who rang what, where, with whom, over
a century) has never been assembled, because assembling it means resolving
the same ringer across decades of name variants and the same tower across
BellBoard's free-text place names, which is exactly the kind of patient,
memoried, multi-session entity resolution that a single person doing it by
hand has never had time for.

## What this becomes, concretely

Three real uses, not a dashboard:

1. **A method/performance atlas** -- who has ringers in common with whom,
   how a method spread geographically over decades, which ringers have rung
   the widest variety of methods. Currently answerable only by trawling
   BellBoard tower-by-tower.
2. **A ringer-lineage and band-network tool** -- tracing how ringing skill
   and specific methods propagated through a region, useful for local
   history and for tower captains.
3. **A method-genealogy and difficulty-mapping tool** -- showing a learner
   the family a method belongs to and the shortest path from what they can
   already ring to what they want to ring next. A real, named gap in how
   the ringing community currently teaches.

## Who'd use it

Tower captains doing local history, the CCCBR's own Methods Committee,
ringing masters teaching new recruits, and individual ringers -- a
community that is, structurally, unusually inclined toward this kind of
documentation, and currently has nobody building it for them.
