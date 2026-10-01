import re
import os

base_dir = "/Users/sbng/Desktop/ANTIGRAVITY/Smart India Hacathon 2026 new"
pages = ['dashboard.html', 'sonar-ai.html', 'expert-verification.html', 'logistics.html', 'mission-ops.html']

for page in pages:
    page_path = os.path.join(base_dir, page)
    try:
        html = open(page_path, 'r').read()
    except Exception as e:
        print(f"Skipping {page}: {e}")
        continue
    
    # 1. Remove the TARANG text and SIH text block
    # It looks like: <div class="flex flex-col justify-center"> ... </div>
    # But let's be more specific
    pattern1 = r'<div class="flex flex-col justify-center">\s*<div class="flex items-center gap-space-xs">\s*<span class="font-headline-sm[^>]*>TARANG</span>\s*<span class="font-label-code[^>]*>SIH 2026</span>\s*</div>\s*<span class="font-label-sm[^>]*>Smart India Hackathon • MoES / INCOIS Track</span>\s*</div>'
    
    html = re.sub(pattern1, '', html, flags=re.DOTALL)
    
    # 2. Remove the INSAT-3DR block
    pattern2 = r'<div class="hidden 2xl:flex items-center gap-space-xs bg-surface-ice[^>]*>\s*<span class="relative flex h-2.5 w-2.5">\s*<span class="animate-ping[^>]*></span>\s*<span class="relative inline-flex[^>]*></span>\s*</span>\s*<span class="font-label-code[^>]*>INSAT-3DR SYNCED</span>\s*<span class="font-label-code[^>]*>• 12 HOTSPOTS</span>\s*</div>'
    
    html = re.sub(pattern2, '', html, flags=re.DOTALL)
    
    open(page_path, 'w').write(html)

print("Text removed successfully.")
