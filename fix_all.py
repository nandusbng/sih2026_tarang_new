import os
import glob
import re

directory = "/Users/sbng/Desktop/ANTIGRAVITY/Smart India Hacathon 2026 new/"
html_files = glob.glob(os.path.join(directory, "*.html"))

for file_path in html_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 1. Remove Launch Mission Control Button
    # It looks like: <button ...>...Launch Mission Control...</button>
    content = re.sub(r'<button[^>]*>.*?Launch Mission Control.*?</button>', '', content, flags=re.DOTALL)
    
    # 2. Remove duplicate logos in the sidebar (<aside>)
    # Find <aside... and remove <img ... logoimage.jpg ...> inside it.
    def remove_logo_in_aside(match):
        aside_content = match.group(0)
        aside_content = re.sub(r'<img[^>]*logoimage\.jpg[^>]*>', '', aside_content)
        return aside_content
        
    content = re.sub(r'<aside.*?</aside>', remove_logo_in_aside, content, flags=re.DOTALL)

    # 3. Remove duplicate logos in secondary headers
    # Secondary headers usually have class="fixed top-20 left-64..."
    def remove_logo_in_second_header(match):
        header_content = match.group(0)
        header_content = re.sub(r'<img[^>]*logoimage\.jpg[^>]*>', '', header_content)
        return header_content
        
    content = re.sub(r'<header class="fixed top-20[^>]*>.*?</header>', remove_logo_in_second_header, content, flags=re.DOTALL)

    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {os.path.basename(file_path)}")

# Also fix auth.js to put the logout button on the right side
auth_file = os.path.join(directory, "js/auth.js")
with open(auth_file, 'r', encoding='utf-8') as f:
    auth_content = f.read()

auth_content = auth_content.replace(
    "const headerRight = document.querySelector('header .flex.items-center.gap-space-md.shrink-0');",
    "const headerRight = document.querySelectorAll('header .flex.items-center.gap-space-md.shrink-0')[1] || document.querySelector('header .flex.items-center.gap-space-md.shrink-0');"
)

with open(auth_file, 'w', encoding='utf-8') as f:
    f.write(auth_content)

print("Done")
