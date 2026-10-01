import os
from bs4 import BeautifulSoup
import glob

directory = "/Users/sbng/Desktop/ANTIGRAVITY/Smart India Hacathon 2026 new/"
html_files = glob.glob(os.path.join(directory, "*.html"))

for file_path in html_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    header = soup.find('header')
    if not header:
        continue
        
    changed = False
    
    # Remove Launch Mission Control Button
    for btn in header.find_all(['button', 'a']):
        if 'Launch Mission Control' in btn.get_text():
            btn.decompose()
            changed = True

    # Remove duplicate logos
    imgs = header.find_all('img')
    logo_imgs = [img for img in imgs if 'logoimage.jpg' in img.get('src', '') or 'TARANG' in img.get('alt', '')]
    
    if len(logo_imgs) > 1:
        # Keep the first one, remove the rest
        for img in logo_imgs[1:]:
            img.decompose()
            changed = True

    if changed:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        print(f"Processed {os.path.basename(file_path)}")

print("Done")
