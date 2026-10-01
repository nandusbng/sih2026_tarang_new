import os
import re

base_dir = "/Users/sbng/Desktop/ANTIGRAVITY/Smart India Hacathon 2026 new"
stitch_dir = os.path.join(base_dir, "stitch_project/stitch_tarang_marine_intelligence_platform")

pages = {
    'dashboard.html': ('tarang_ai_marine_debris_maritime_logistics', 'Overview'),
    'sonar-ai.html': ('tarang_sonar_ai_detection_console', 'Sonar AI Detection'),
    'expert-verification.html': ('tarang_expert_verification_dashboard', 'Verification Console'),
    'logistics.html': ('logistics_rov_route_planning', 'Logistics & Dispatch'),
    'mission-ops.html': ('tarang_mission_operations_command', None)
}

active_class = 'px-space-md py-2 transition-all bg-primary-container text-on-primary font-semibold rounded-lg shadow-sm'
inactive_class = 'px-space-md py-2 rounded-lg font-body-sm text-body-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-all'

def make_link(text, href, is_active):
    classes = active_class if is_active else inactive_class
    aria = ' aria-current="page"' if is_active else ''
    return f'<a{aria} class="{classes}" data-path="dummy" href="{href}">{text}</a>'

# 1. Get the perfect master header from dashboard
dash_src = open(os.path.join(stitch_dir, 'tarang_ai_marine_debris_maritime_logistics/code.html'), 'r').read()
header_match = re.search(r'<header.*?</header>', dash_src, flags=re.DOTALL)
master_header = header_match.group(0)

# We need to construct the standard <nav> for the master header
nav_match = re.search(r'<nav[^>]*>.*?</nav>', master_header, flags=re.DOTALL)
nav_open_tag = re.search(r'<nav[^>]*>', nav_match.group(0)).group(0)

links = [
    ('Overview', 'dashboard.html'),
    ('Sonar AI Detection', 'sonar-ai.html'),
    ('Verification Console', 'expert-verification.html'),
    ('Logistics &amp; Dispatch', 'logistics.html')
]

# We also need to fix the button to link to mission-ops
master_header = re.sub(r'<button class="flex items-center gap-space-xs bg-secondary text-on-secondary(.*?)" type="button">(.*?)</button>', r'<a href="mission-ops.html" class="flex items-center gap-space-xs bg-secondary text-on-secondary\1">\2</a>', master_header, flags=re.DOTALL)


# Process each page from FRESH source
for filename, (src_folder, active_text) in pages.items():
    src_path = os.path.join(stitch_dir, src_folder, 'code.html')
    html = open(src_path, 'r').read()
    
    # Inject Firebase
    html = html.replace('</script>\n</head>', '</script><script type="module" src="js/supabase-config.js"></script>\n</head>')
    if '</script></head>' in html:
        html = html.replace('</script></head>', '</script><script type="module" src="js/supabase-config.js"></script>\n</head>')
    
    # Generate the nav specific for this page
    new_nav_inner = ''
    for text, href in links:
        # Note: HTML entities might not match exactly if not careful, but we use strict text match
        is_active = (text.replace('&amp;', '&') == active_text) if active_text else False
        new_nav_inner += make_link(text, href, is_active)
    new_nav_html = f'{nav_open_tag}{new_nav_inner}</nav>'
    
    page_header = master_header[:nav_match.start()] + new_nav_html + master_header[nav_match.end():]
    
    # Find the original primary header to replace
    orig_header_match = re.search(r'<header.*?</header>', html, flags=re.DOTALL)
    
    # Some pages (like logistics) have sidebars and SECOND headers.
    # We must ensure we only replace the FIRST header, which acts as the top bar.
    # Actually, logistics.html in original Stitch DOES NOT HAVE A TOP BAR!
    # Let's check: The <aside> is top-0, the <header> is top-0 left-64.
    # If the original page didn't have a full-width top bar, replacing the first <header> will replace the internal one!
    
    if filename == 'logistics.html':
        # Original logistics: <aside> then <header>
        # We want to PREPEND the master header to the body, and push everything down
        body_match = re.search(r'<body[^>]*>', html)
        html = html[:body_match.end()] + "\n" + page_header + "\n" + html[body_match.end():]
        # Push aside down
        html = html.replace('top-0 h-full w-64', 'top-20 h-[calc(100vh-5rem)] w-64')
        # Push inner header down
        html = html.replace('top-0 left-64', 'top-20 left-64')
        # Push main down (pt-16 -> pt-36 because 20+16 = 36, or just pt-20 if no inner header)
        # Logistics inner header is h-16, so main should be pt-[9rem] (144px)
        html = html.replace('pt-16', 'pt-[9rem]')
        
    elif filename == 'expert-verification.html' or filename == 'sonar-ai.html':
        # These had a full-width top bar (h-16).
        # We replace the first header with our h-20 master header.
        html = html[:orig_header_match.start()] + page_header + html[orig_header_match.end():]
        # Push aside from top-16 to top-20
        html = html.replace('top-16', 'top-20')
        html = html.replace('h-[calc(100vh-4rem)]', 'h-[calc(100vh-5rem)]')
        # Push main from pt-16 to pt-20
        html = html.replace('pt-16', 'pt-20')
    else:
        # Dashboard or Mission Ops
        # Dashboard already has this structure, just replace the header
        if orig_header_match:
            html = html[:orig_header_match.start()] + page_header + html[orig_header_match.end():]
    
    open(os.path.join(base_dir, filename), 'w').write(html)

print("Rebuild complete. Navigation should now be flawless and layout intact.")
