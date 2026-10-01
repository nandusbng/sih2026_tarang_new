import re
import os

base_dir = "/Users/sbng/Desktop/ANTIGRAVITY/Smart India Hacathon 2026 new"

# 1. Copy the Sonar AI file
sonar_src = os.path.join(base_dir, "stitch_project/stitch_tarang_marine_intelligence_platform/tarang_sonar_ai_detection_console/code.html")
sonar_dest = os.path.join(base_dir, "sonar-ai.html")
os.system(f'cp "{sonar_src}" "{sonar_dest}"')

# 2. Add Supabase to sonar-ai.html
content = open(sonar_dest, 'r').read()
content = content.replace('</script>\n</head>', '</script><script type="module" src="js/supabase-config.js"></script>\n</head>')
open(sonar_dest, 'w').write(content)

# 3. Get the perfect header from dashboard.html
dashboard = open(os.path.join(base_dir, 'dashboard.html'), 'r').read()
header_match = re.search(r'<header.*?</header>', dashboard, flags=re.DOTALL)
header_html = header_match.group(0)

# Fix the href for Sonar AI inside this master header
header_html = re.sub(r'<a([^>]+)href="dashboard.html"([^>]*)>Sonar AI Analyzer</a>', r'<a\1href="sonar-ai.html"\2>Sonar AI Analyzer</a>', header_html)

# Let's save this updated header back to dashboard.html
dashboard = dashboard[:header_match.start()] + header_html + dashboard[header_match.end():]
open(os.path.join(base_dir, 'dashboard.html'), 'w').write(dashboard)

# 4. Apply this master header and adjust layout for ALL pages
pages = ['dashboard.html', 'expert-verification.html', 'logistics.html', 'mission-ops.html', 'sonar-ai.html']

for page in pages:
    page_path = os.path.join(base_dir, page)
    html = open(page_path, 'r').read()
    
    # Replace the header
    html = re.sub(r'<header.*?</header>', header_html, html, flags=re.DOTALL)
    
    # Adjust sidebars and spacing if needed
    if page == 'sonar-ai.html':
        # the aside might need top-20
        html = html.replace('top-16', 'top-20')
        html = html.replace('h-[calc(100vh-4rem)]', 'h-[calc(100vh-5rem)]')
        html = html.replace('pt-16', 'pt-20')
        # Sonar AI has a specific layout too, let's just make sure it doesn't overlap
    
    open(page_path, 'w').write(html)

print("Setup complete for all pages.")
