import re

# Read dashboard
dashboard = open('dashboard.html', 'r').read()

# Extract dashboard header
header_match = re.search(r'<header.*?</header>', dashboard, flags=re.DOTALL)
header_html = header_match.group(0)

# Fix links in header
header_html = header_html.replace('href="#"', 'href="logistics.html"')
header_html = header_html.replace('<button class="hidden sm:flex', '<a href="mission-ops.html" class="hidden sm:flex')
header_html = header_html.replace('Launch Mission Control</span></button>', 'Launch Mission Control</span></a>')

# Save updated dashboard
dashboard = dashboard[:header_match.start()] + header_html + dashboard[header_match.end():]
open('dashboard.html', 'w').write(dashboard)

# Replace headers in other files
for f in ['expert-verification.html', 'logistics.html', 'mission-ops.html']:
    content = open(f, 'r').read()
    
    # In logistics.html, the layout has left-64 for the header.
    # But we want the uniform full-width header.
    # So we'll replace the old header with the new one.
    new_content = re.sub(r'<header.*?</header>', header_html, content, flags=re.DOTALL)
    
    # Adjust logistics.html aside so it doesn't get covered by the new h-20 full width header
    if f == 'logistics.html':
        new_content = new_content.replace('top-0 h-full', 'top-20 h-[calc(100vh-5rem)]')
        # Also fix main pt-16 to pt-20
        new_content = new_content.replace('pt-16', 'pt-20')
        new_content = new_content.replace('pt-5 pb-6', 'pt-5 pb-6 overflow-y-auto')
    elif f == 'expert-verification.html':
        # Adjust top-16 to top-20
        new_content = new_content.replace('top-16', 'top-20')
        new_content = new_content.replace('h-[calc(100vh-4rem)]', 'h-[calc(100vh-5rem)]')
        # fix main pt-16 to pt-20
        new_content = new_content.replace('pt-16', 'pt-20')
    
    open(f, 'w').write(new_content)

print("Headers standardized across all pages.")
