# The owner's rule on headlines (2026-10-17)

> "Jeg synes ikke, man skal bruge artikeloverskrifter, da de er mere nysgerrighedsvækkende end informerende, så det skal
> hjernen ændre på."

**The rule:** Khabar does not show the outlets' own headlines as its headlines. Every story the app shows – on the front
page, in Live and in an opened story – carries an **informative headline**: who did or said what, where (and when, if it
matters), in plain Danish, in the style of a news wire. The headline states the news; it never withholds it to make the
reader curious.

What an informative headline is:

- It names the actor (state, ruler, government, army, group, institution) and the act or statement – the method's own
  focus on deeds and on who acts.
- It is a statement, not a teaser: no questions, no "Derfor …", "Se …", "Her er …", "Det skal du vide", "Sådan …",
  "– og det er ikke godt", no cliff-hanger colon, no "eksperter undrer sig", no superlatives the source does not support.
- It keeps the facts and the source's own loaded words where they carry the source's framing (attributed by the source
  name shown with it), as before.

Examples of the change:

- "Førende ekspert har teori om Putin: Derfor er han stadig præsident i dag" → the claim itself, e.g. "Ekspert: Putin
  holder magten, fordi …" (from the teaser and the other outlets' coverage).
- "Se billederne: Kaos i lufthavnen" → "Houthi-angreb lukker King Khalid-lufthavnen i Riyadh; 12 dræbt".

**Who writes them:** the editor (Claude, every 15 minutes) writes the informative headline for every new story that the
app shows – Danish outlets as well as foreign ones – not only the eight strongest foreign headlines as before. With the
15-minute cadence a new story normally gets its headline within a quarter of an hour.

**The app:** shows the editor's headline first for every story (summaries.json `titles`). Until the editor has written
one, it shows the outlet's headline – but where that headline is plainly a curiosity headline (a question, or the
patterns above), it shows the first sentence of the teaser instead, shortened at a word boundary. The opened story may
still name the outlet's original headline in small type ("Originaloverskrift: …"), as it names foreign originals today.
