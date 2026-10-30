"""Free browser tools. Everything runs in the visitor's browser; nothing typed into a tool is sent to the server."""
TOOLS = [
    ('best-time-to-call', 'Best Time to Call Planner', 'See when your working hours overlap with your customer’s business hours, in both time zones.', 'clock', 'Planning'),
    ('a2p-10dlc-readiness-quiz', 'A2P 10DLC Readiness Quiz', 'Seven quick questions to see if your business is ready to register for US texting.', 'message', 'Texting'),
    ('follow-up-cadence-planner', 'Follow-Up Cadence Planner', 'Turn a follow-up plan into real call and text dates, and download it to your calendar.', 'calendar', 'Sales'),
    ('phone-number-list-cleaner', 'Phone Number List Cleaner', 'Paste a messy list and get clean, de-duplicated numbers in international (E.164) format.', 'phone', 'Data'),
    ('call-center-staffing-calculator', 'Call Center Staffing Calculator', 'An Erlang C calculator for small teams: how many agents you need to answer on time.', 'users', 'Planning'),
    ('area-code-lookup', 'Area Code Lookup', 'Look up any USA or Canada area code, or find the codes for a city or state.', 'search', 'Numbers'),
    ('sms-character-counter', 'SMS Segment & Character Counter', 'Count characters and SMS segments as you type, and spot characters that make texts cost more.', 'doc', 'Texting'),
    ('cold-call-script-generator', 'Cold Call Script Generator', 'Pick your industry and call type and get a ready-to-edit call script.', 'headset', 'Sales'),
]
TOOL_MAP = {t[0]: t for t in TOOLS}
