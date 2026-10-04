# Brand intake

Do this with the human before making anything for publication. Write the answers into `brand/brand.json` (start
from `brand.example.json`). Ask for what is missing; do not invent a brand.

## Identity
- Name as it should appear, handle(s) per platform, website, the one-line description.
- Logo: a transparent PNG (square mark is best) saved as `brand/logo.png`. If there is none, the name is set in type.
- The default call to action ("Link in bio", "Book a demo", "Follow for more").

## Look
- Colours: background, text, muted text, one accent, the text colour that sits on the accent, a panel colour, a line
  colour, a soft tint. Ask for hex values or a site/style guide to take them from. Check contrast: accent text on the
  background and accent_ink on the soft tint must be easy to read on a phone.
- Fonts: a display face, a body face, a mono/label face (Google Fonts names, or font files with their licence).
  If the brand has its own typefaces, get the files and put them in `brand/` (`"file": "name.ttf"` in the font entry).
- Anything that is never allowed: colours, imagery styles, competitors' marks, stock-photo clichés.

## Voice
- Three words that describe how the brand sounds. Two example posts the human likes, one they dislike.
- `do` list and `dont` list (words to avoid, punctuation habits, claims to avoid). Language and spelling variant.
- What the brand never claims. What needs legal or manager sign-off.

## Audience and goals
- Who the posts are for, what they already know, the one action you want from them.
- The platforms in use and the human's rhythm (posts per week). Time zone.

## Assets and permissions
- Where approved screenshots, product photos and footage live. Who owns them; any licence or credit line required.
- Customer names, faces, quotes: which are cleared for use, in writing. Default is none.
- Voiceover: which voice (if any) the brand uses, and who approved spending on it.

## Accounts and access
- Which accounts you may prepare content for. The human signs in; you never receive or store a password.
- Who approves posts, and how (a message in this chat is the approval; say "approved: <item>").
- Where finished files and the ledger should be kept so they are backed up.

When done, run `./run.sh tools/doctor.py`, make one card of each template on the real brand, and show the human before
any real work starts.
