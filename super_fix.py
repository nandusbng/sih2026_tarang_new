import os
from bs4 import BeautifulSoup
import glob

directory = "/Users/sbng/Desktop/ANTIGRAVITY/Smart India Hacathon 2026 new/"
html_files = glob.glob(os.path.join(directory, "*.html"))

for file_path in html_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    changed = False
    
    # 1. Remove Launch Mission Control Button entirely from the DOM
    for btn in soup.find_all(['button', 'a']):
        if btn.get_text() and 'Launch Mission Control' in btn.get_text():
            btn.decompose()
            changed = True

    # 2. Remove logos from sidebars
    for aside in soup.find_all('aside'):
        for img in aside.find_all('img'):
            if 'logoimage.jpg' in img.get('src', '') or 'TARANG' in img.get('alt', ''):
                img.decompose()
                changed = True

    # 3. Remove logos from secondary headers (any header that is not the first one)
    headers = soup.find_all('header')
    if len(headers) > 1:
        for header in headers[1:]:
            for img in header.find_all('img'):
                if 'logoimage.jpg' in img.get('src', '') or 'TARANG' in img.get('alt', ''):
                    img.decompose()
                    changed = True

    if changed:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        print(f"Fixed {os.path.basename(file_path)}")

print("Done")
