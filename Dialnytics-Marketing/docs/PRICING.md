# Price source and calculation

All amounts are USD/month. The owner confirmed that customers pay the listed plan
price only, without setup fees or extra plan charges. No live payment calculation
or payment gateway fee is added by this website.

## USA/Canada

1 user = $22. Two users = $38 TOTAL. Three or more = $15 x user count.
The earlier $30 two-user price was superseded by the owner's later $38 instruction.

## Fixed per-user plans

UK $29; Australia $44; Japan $64; Global $179.
The additional plan rates are the previously reviewed reference rates less USD 1.
European local-number and custom plans have no invented fixed rate; they require a quote.

## UK to Europe

| Selected countries | Rate per user/month |
|---|---:|
| 1 | $44.00 |
| 2 | $79.00 |
| 3 | $110.60 |
| 4 | $137.40 |
| 5 | $159.85 |
| 6 | $178.52 |

These follow the earlier explanation of USD 1 less per user's complete monthly
package, NOT USD 1 less per selected country. The owner confirmed the general
USD 1 discount but did not separately reconfirm the multi-country arithmetic.
Review this interpretation before publishing multi-country prices. More than six
countries goes to a custom quote. Country choices are requirements to confirm,
not an assertion of guaranteed number inventory or every number type in that country.

The self-service request UI supports 1-100 users; this is a form bound, NOT a calling
minute limit. Larger teams can contact sales. No fixed monthly minute limit is
invented for the owner's unlimited offer.

The browser calculates a preview. The server calculates the authoritative amount
from `app/catalog.py` and stores its catalog version and the quoted price with the
request. Prices sent by the browser are not accepted.

## Source record

- Owner's confirmed decisions in this conversation take precedence over the reference.
- Reference structure/rates reviewed: https://dialsyx.com/pricing/ and
  https://dialsyx.com/numbers/uk-to-europe/ on 22 October 2026.
- This application does not scrape or automatically change prices after deployment.
