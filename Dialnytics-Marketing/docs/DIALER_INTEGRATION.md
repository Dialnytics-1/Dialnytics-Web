# Website orders -> dialer integration

## What happens

1. The buyer picks a plan, users and add-ons. For every user they enter name, login email, password (12+ characters) and a number.
   Numbers come from the dialer's **owned, unassigned** Telnyx/Twilio numbers (UK plan shows both providers). Users of one business may share a number.
   Toll-free numbers are shown only when the **Toll-free** add-on is ticked (USA & Canada, $10 one-time per distinct number).
2. Choosing a number holds it for **10 minutes** (hidden from other visitors). The buyer sees the countdown.
3. Placing the order creates the company and **pending** users in the dialer (inactive, cannot log in). The password is hashed by the dialer and is never stored here.
   - Card: hold = 10 minutes. Stripe confirms payment -> the dialer activates the accounts at once (30 days from today, add-ons, numbers).
   - Bank / USDT: the buyer continues on WhatsApp; hold = 1 hour. The order shows as **Pending Orders** in the dialer admin; **Mark as paid** activates it (and updates this site).
4. If payment does not arrive in time, the pending users, the order here and the number hold are deleted automatically (both sides run a sweeper).
5. If a number cannot be assigned at activation, the account is still created without a number; the customer sees a "contact us on WhatsApp" notice.
6. Stripe `invoice.paid` (monthly renewal) adds 30 days in the dialer.

## Environment variables

| Where | Variable | Value |
|---|---|---|
| this site | `DIALER_API_URL` | `https://dialnytics.co.uk` |
| this site | `DIALER_API_KEY` | long random secret (32+ chars) |
| dialer | `MARKETING_API_KEY` | **the same secret** |
| dialer | `MARKETING_URL` | `https://dialnytics-web.onrender.com` (this site; used to report "Mark as paid" / cancel) |
| dialer | `SUPPORT_WHATSAPP` | optional, default `447476629105` |

Generate the secret with `python -c "import secrets;print(secrets.token_urlsafe(40))"`.

## Stripe

- Webhook URL: `https://dialnytics-web.onrender.com/webhooks/stripe` (use your live domain if different).
- Events: `checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`, `customer.subscription.deleted`.
- Checkout sessions close themselves when the number hold ends, so nobody can pay for a released number.
- A payment that arrives after the hold ended (rare race) is marked with a clear note: create the accounts manually or refund.

## Deploy order

1. Deploy the **dialer** first (it adds tables/columns automatically on start: `website_orders`, `number_holds`, `payments.amount_usd/method/reference`, user `signup_*` and `power_enabled`).
2. Set the shared secret on both services, then deploy this site.
