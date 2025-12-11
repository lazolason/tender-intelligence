from keyword_rules import EXCLUDE_KEYWORDS

test_titles = [
    'Supply and Installation of Load Bodies fitted to Eskom Iveco Trucks',
    'OIL SPILLAGE MANAGEMENT FOR A PERIOD OF 5 YEARS',
    'APPOINTMENT OF A SPECIALIST QUALITY CONTROL INSPECTORATE (QCI) SERVICE',
    'Provision of Property Management Minor Works',
    'Training title ISO 14064 Greenhouse Gas'
]

print('Checking why these are not excluded:\n')
for title in test_titles:
    text = title.lower()
    matched = [kw for kw in EXCLUDE_KEYWORDS if kw in text]
    print(f'{title[:65]}')
    print(f'  Matched: {matched if matched else "NONE - NOT EXCLUDED!"}')
    print()
