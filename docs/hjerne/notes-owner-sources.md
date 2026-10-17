# The owner's request on sources (2026-10-17)

> "Gennemgå også kilderne, og se om der er nogle, der passer bedre til redaktøren end andre."

**The task:** go through every source in config/feeds.json and judge how well it serves the editor's job now – choosing
the day's most important stories by the brain (the books' order of importance and the amir's newest readings) and
giving each an informative headline (who did or said what, where).

**What makes a source fit the editor** (measure it on real data – the data branch keeps the radar's recent items and its
health per source – not on reputation alone):

- **Informative headlines and teasers:** a headline that states the news (wire style) versus one that withholds it
  (questions, "Derfor …", "Se …", cliff-hangers). Count it per source over the last days.
- **Deeds and statements of states:** how often its stories land in the sharp tiers (the leading state's acts, the great
  powers', the Muslim world's rulers, Danish politics on Islam and Muslims) versus light news (sport, weather, royals,
  celebrities, local crime).
- **First and unique:** how often it is first with a story, or the only source for a story that matters.
- **Official voices:** governments' own channels (statements are deeds' words – the method weighs both).
- **Camp:** keep every camp covered (the method compares how the camps report the same event); the movement's own
  outlets never count as confirmation.
- **Noise:** volume per day against what of it is ever important; duplicates of others; broken or stale feeds.

**What to do with it:**

1. A report, docs/hjerne/kilder.md: every source with its numbers and a plain verdict – *styrk* (weigh up, prefer as a
   story's lead), *behold*, *dæmp* (weigh down: mostly curiosity headlines or light news), *fjern* (disable: noise, dead,
   or duplicates without adding a camp) – and the sources that are missing for the editor's job (e.g. a Danish wire,
   more governments' own channels in the Muslim world, the great powers' foreign ministries), each with why.
2. A `fit` value per source in config/feeds.json (e.g. 0.5–1.5) the radar uses: in the rank (a small, measured weight),
   and to choose which outlet's headline and teaser lead a story (the most informative, not the most sensational).
3. The editor's input shows each candidate's lead source and, where it matters, a better source covering the same story.
4. Changes to feeds are made carefully: the caretaker routine edits config/feeds.json every morning (repairs, disables);
   keep its changes and add fields without breaking its format. Never disable a camp's only source.

## New sources (the owner, same day: "find også gerne nye, bedre kilder")

Search for sources that serve the editor better than some of today's: news wires and agencies with informative
headlines (a Danish wire if one can be followed; the big international and regional agencies), governments' and
ministries' own channels (the great powers' foreign ministries; the rulers of the Muslim world – Saudi, Emirati,
Qatari, Egyptian, Turkish, Pakistani, Iranian, Iraqi, Jordanian, Syrian state agencies), Danish political sources
(Folketinget, Statsministeriet, Udenrigsministeriet, the parties' press releases where they publish feeds), and
outlets that fill a camp the radar lacks. Every candidate must be **verified to work** (fetch its RSS/Atom, Telegram
public channel or YouTube feed; real items, recent, readable titles) before it goes into config/feeds.json with its
group, camp, label and fit. Rules that stand: no Facebook, X, Instagram or TikTok scraping; no source on an EU
sanctions list; no terror-listed group's own channel; the movement's own outlets never count as confirmation. List each
new source in docs/hjerne/kilder.md with why it fits, and what it replaces if anything.
