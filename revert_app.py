import os
with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace("parsed_data['metadata']['survey']['survey_id']", "parsed_data['metadata']['survey_id']")
code = code.replace("parsed_data['metadata']['summary']['total_pings']", "parsed_data['metadata']['total_pings']")
code = code.replace("parsed_data['metadata']['summary']['channel_count']", "parsed_data['metadata']['channel_count']")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)
