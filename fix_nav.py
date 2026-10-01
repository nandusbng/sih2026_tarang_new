import glob
import re

files = glob.glob('*.html')
for file in files:
    if file == 'survey-operator.html':
        continue
    with open(file, 'r') as f:
        content = f.read()
    
    # We want to replace href="survey-operator.html">Survey Operator</a> with href="operator-portal.html">Survey Operator</a>
    # Also handle the label text "Survey Operator" inside the anchor tag
    content = re.sub(r'href="survey-operator.html"([^>]*)>Survey Operator</a>', r'href="operator-portal.html"\1>Survey Operator</a>', content)
    
    with open(file, 'w') as f:
        f.write(content)
