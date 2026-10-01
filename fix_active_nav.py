import re
import os

base_dir = "/Users/sbng/Desktop/ANTIGRAVITY/Smart India Hacathon 2026 new"

files = {
    'dashboard.html': 'Overview',
    'sonar-ai.html': 'Sonar AI Analyzer',
    'expert-verification.html': 'Expert Verification',
    'logistics.html': 'Fleet Logistics &amp; Routing',
    'mission-ops.html': None
}

active_class = 'px-space-md py-space-xs transition-all bg-surface-container-low text-secondary font-semibold rounded-xl'
inactive_class = 'font-body-md text-body-md px-space-md py-space-xs rounded-xl text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-all'

def make_link(text, href, is_active):
    classes = active_class if is_active else inactive_class
    aria = ' aria-current="page"' if is_active else ''
    return f'<a{aria} class="{classes}" data-path="dummy" href="{href}">{text}</a>'

for filename, active_text in files.items():
    path = os.path.join(base_dir, filename)
    try:
        content = open(path, 'r').read()
    except:
        continue
    
    # We will replace the entire <nav> block inside the header to be safe
    # Find the nav block inside the header
    header_match = re.search(r'<header.*?</header>', content, flags=re.DOTALL)
    if not header_match:
        continue
    
    header_html = header_match.group(0)
    nav_match = re.search(r'<nav[^>]*>.*?</nav>', header_html, flags=re.DOTALL)
    if not nav_match:
        continue
    
    nav_html = nav_match.group(0)
    
    # Construct new inner HTML for the nav
    links = [
        ('Overview', 'dashboard.html'),
        ('Sonar AI Analyzer', 'sonar-ai.html'),
        ('Expert Verification', 'expert-verification.html'),
        ('Fleet Logistics &amp; Routing', 'logistics.html')
    ]
    
    new_nav_inner = ''
    for text, href in links:
        is_active = (text == active_text)
        new_nav_inner += make_link(text, href, is_active)
        
    # Reconstruct the nav tag itself to preserve its classes
    nav_open_tag = re.search(r'<nav[^>]*>', nav_html).group(0)
    new_nav_html = f'{nav_open_tag}{new_nav_inner}</nav>'
    
    new_header_html = header_html[:nav_match.start()] + new_nav_html + header_html[nav_match.end():]
    new_content = content[:header_match.start()] + new_header_html + content[header_match.end():]
    
    open(path, 'w').write(new_content)

print("Navigation active states fixed for all 5 pages.")
