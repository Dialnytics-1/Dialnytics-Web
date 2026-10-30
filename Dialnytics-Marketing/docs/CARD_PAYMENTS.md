# Card payments (Stripe Checkout)

Card checkout is **off** until both environment variables are set in Render:

| Variable | Where to find it |
|---|---|
| `STRIPE_SECRET_KEY` | Stripe Dashboard → Developers → API keys → Secret key (`sk_live_...`, or `sk_test_...` for testing). A restricted key (`rk_...`) with write access to Checkout Sessions also works. |
| `STRIPE_WEBHOOK_SECRET` | Stripe Dashboard → Developers → Webhooks → Add endpoint → URL `https://dialnytics.com/webhooks/stripe`, events `checkout.session.completed`, `customer.subscription.deleted`, `invoice.payment_failed` → Signing secret (`whsec_...`). |

Never put these keys in templates, JavaScript or chat. They are read only on the server.

How it works
1. The customer builds a plan on the order page and picks **Credit / Debit Card**.
2. The server saves the request, recalculates the price itself and creates a Stripe Checkout Session:
   monthly subscription items (plan + each add-on) and a one-time item for the SMS A2P 10DLC registration fee.
3. The customer pays on Stripe and returns to `/order/thanks/`.
4. Stripe calls `/webhooks/stripe`; the request is marked **Paid** in Admin with a note. Activation stays manual, after the account review.
5. Cancellations and failed renewals are added to the request as notes.

Bank Transfer and USDT keep working as before (details sent on WhatsApp).
