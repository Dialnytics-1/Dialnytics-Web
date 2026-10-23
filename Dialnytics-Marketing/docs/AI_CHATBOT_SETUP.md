# Dialnytics AI Assistant — Website chat + WhatsApp (24 Oct 2026)

## Kya bana hai

1. **Website chat** (har page par neeche right corner mein chat button)
   - Pehle language: English / Roman Urdu.
   - Bot plans, prices, features, payment aur activation ke jawab deta hai (prices `app/catalog.py` se aate hain).
   - Baat cheet mein yeh details leta hai: Name, WhatsApp number, Company name, Calling country, Users kitne, Email (optional).
   - Demo maange to product tour ka link deta hai (`/product/tour/`). Free trial ka wada nahi karta.
   - Telnyx/Twilio ya AI company ka naam kabhi nahi leta.
   - Page reload karne par chat wahi rehti hai (30 din). Admin reply kare to visitor ko chat mein dikh jata hai.
2. **WhatsApp** (+44 7476 629105, wahi AI)
   - Naya customer message kare to AI khud ON hota hai (`WHATSAPP_AI_DEFAULT=true`).
   - Pehla jawab language menu (1 English / 2 Roman Urdu).
   - Admin → Chats mein har chat ka AI ON/OFF button.
   - Aap admin panel se reply karein, ya WhatsApp Business app (phone) se reply karein, to us chat ka AI khud OFF ho jata hai. Dobara ON karne par agar customer ka message jawab ka intezar kar raha ho to AI foran jawab deta hai.
3. **Admin panel**
   - Naya page **Chats** (`/admin/chats`): saari chats, unread, "Needs you", AI ON/OFF, leads.
   - Chat kholne par poori baat cheet, customer ki details, reply box, AI button.
   - Details mukammal hote hi **Inbox** mein "Chat" type ki lead banti hai (Name, WhatsApp, Company, Country, Users, Email, Channel, Language) aur email notification jati hai.
   - Har nayi lead par aap ke **apne WhatsApp** par alert aata hai (`ADMIN_WHATSAPP_NUMBER`).
   - Customer "insaan se baat" maange ya bot jawab na de sake to chat "Needs you" ho jati hai aur aap ko WhatsApp alert aata hai.

## Database
Kuch manual nahi karna. App start hote hi 2 naye tables khud bante hain: `mkt_chat_conversations`, `mkt_chat_messages` (website ke apne database mein, dialer se alag).

## Render Environment variables

| Key | Value | Zaroori? |
|---|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys → Create key | Haan (AI ke liye) |
| `AI_MODEL` | `claude-haiku-5-5` (sasta, tez). Behtar jawab ke liye `claude-sonnet-5-5` | Nahi |
| `CHAT_WIDGET_ENABLED` | `true` (band karna ho to `false`) | Nahi |
| `TELNYX_API_KEY` | Telnyx Portal → API Keys | WhatsApp ke liye |
| `TELNYX_PUBLIC_KEY` | Telnyx Portal → Keys & Credentials → Public Key | WhatsApp ke liye |
| `WHATSAPP_FROM_NUMBER` | `+447476629105` | WhatsApp ke liye |
| `TELNYX_MESSAGING_PROFILE_ID` | WhatsApp wale messaging profile ki ID | Agar Telnyx maange |
| `WHATSAPP_AI_DEFAULT` | `true` = nayi chat par AI khud ON | Nahi |
| `ADMIN_WHATSAPP_NUMBER` | Aap ka **personal** WhatsApp number (business number nahi), e.g. `+923001234567` | Alerts ke liye |
| `WHATSAPP_ALERT_TEMPLATE` | Approved template ka naam, e.g. `dialnytics_new_lead` | Nahi (neeche dekhein) |
| `WHATSAPP_ALERT_TEMPLATE_LANG` | `en` (template ki language) | Nahi |

## WhatsApp setup (Telnyx, coexistence — phone par WhatsApp Business app bhi chalta rahega)
1. Phone par WhatsApp Business app update karein.
2. Telnyx Portal → Messaging → WhatsApp → Embedded Signup → "existing WhatsApp Business app number" choose karein → +44 7476 629105 → app mein QR/confirmation.
3. WhatsApp number ko ek messaging profile par lagayein. Profile ka **Webhook URL**: `https://dialnytics.uk/webhooks/telnyx/whatsapp`
   - Agar yeh number dialer mein SMS ke liye bhi use hota hai to pehle bata dein (warna dialer ke SMS webhooks badal sakte hain).
4. WABA webhook events mein `messages` dobara subscribe na karein (warna har message do dafa aayega). App duplicate khud rok leti hai, phir bhi.
5. Render mein upar wali WhatsApp keys daal kar Manual Deploy.
6. Test: apne personal WhatsApp se business number par "Hi" bhejein → language menu aana chahiye.

## Lead alert aap ke WhatsApp par
- WhatsApp sirf 24 ghante ke andar free text bhejne deta hai. Agar `WHATSAPP_ALERT_TEMPLATE` khali hai to alert text message hota hai — yeh tab hi pohanchta hai jab pichle 24 ghante mein aap ne apne personal number se business number par koi message bheja ho.
- Pakka alert ke liye Telnyx mein ek **Utility** template banayein: naam `dialnytics_new_lead`, body: `New Dialnytics lead: {{1}}` → Meta approval (24-48 ghante) → Render mein `WHATSAPP_ALERT_TEMPLATE=dialnytics_new_lead`.

## Hifazat aur limits
- WhatsApp webhook har request ka Telnyx signature check karta hai.
- Website chat: 40 messages/ghanta per IP, 150 messages per chat. Ek chat mein AI zyada se zyada 60 jawab deta hai, phir team ko de deta hai.
- Bot card number, password, OTP nahi maangta.
- Admin panel se WhatsApp reply sirf customer ke aakhri message ke 24 ghante ke andar jata hai (WhatsApp ka rule). Us ke baad phone app se reply karein.

## Emergency switch
- Chat button band: `CHAT_WIDGET_ENABLED=false` (purana WhatsApp button wapas aa jata hai).
- WhatsApp par AI band: Admin → Chats → har chat "Stop AI", ya `WHATSAPP_AI_DEFAULT=false` (sirf nayi chats ke liye).

## Files
- Naye: `app/chatbot.py` (AI, knowledge, WhatsApp helpers), `app/chat_routes.py` (routes), `templates/admin_chats.html`, `templates/admin_chat_detail.html`, `static/js/chat-widget.js`, `static/css/chat-widget.css`, `docs/AI_CHATBOT_SETUP.md`
- Badle: `app/main.py`, `app/database.py`, `app/settings.py`, `templates/base.html`, `templates/admin_base.html`, `templates/admin_inbox.html`, `templates/admin_detail.html`, `static/js/admin.js`, `static/css/admin.css`, `requirements.txt` (+cryptography), `render.yaml`

## Abhi ki limitations
- Live Anthropic aur Telnyx accounts par test nahi hua (keys nahi thi). Deploy ke baad website chat aur WhatsApp par ek test zaroor karein.
- WhatsApp par photo/voice note ka matlab AI nahi samajhta (sirf "[image received]" dekhta hai); text likhne ka kehta hai.
