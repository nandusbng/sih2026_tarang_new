import os
import re

html_files = [f for f in os.listdir('.') if f.endswith('.html')]
for f in html_files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Add defer to local JS scripts if not already present
    content = re.sub(r'<script src="(/?[^"]+\.js)"(?![^>]*defer)[^>]*>', r'<script src="\1" defer>', content)
    
    # Add loading="lazy" to images if not already present
    content = re.sub(r'<img([^>]*src="[^"]+"[^>]*)>', lambda m: f'<img{m.group(1)} loading="lazy">' if 'loading=' not in m.group(1) else m.group(0), content)
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
print("Optimized HTML files.")
