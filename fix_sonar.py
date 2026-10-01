import re

with open('sonar-analyst.html', 'r') as f:
    content = f.read()

# We want to remove all the static <article> tags inside #anomalies-container
# Let's find '<div class="flex flex-col gap-space-md" id="anomalies-container">'
start_idx = content.find('<div class="flex flex-col gap-space-md" id="anomalies-container">')
if start_idx != -1:
    end_container = content.find('</div>\n</div>\n<!-- RIGHT 28% COLUMN', start_idx)
    if end_container != -1:
        # Replace everything in between with just the opening tag
        content = content[:start_idx] + '<div class="flex flex-col gap-space-md" id="anomalies-container">\n' + content[end_container:]

with open('sonar-analyst.html', 'w') as f:
    f.write(content)
