import glob
import sys
import subprocess

try:
    from bs4 import BeautifulSoup
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup

files = glob.glob('*.html')

logout_html = """
<a href="login.html" onclick="sessionStorage.clear()" class="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-red-600 text-white font-bold text-[12px] transition-colors shadow-md cursor-pointer ml-4 border border-slate-700">
  <span class="material-symbols-outlined text-[16px]">logout</span> LOGOUT
</a>
"""
logout_soup = BeautifulSoup(logout_html, 'html.parser').a

back_html = """
<button onclick="history.back()" class="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-surface-ice hover:bg-surface-container-high text-on-surface font-bold text-sm transition-colors shadow-sm cursor-pointer mr-4 border border-border-subtle">
  <span class="material-symbols-outlined text-[18px]">arrow_back</span> Back
</button>
"""
back_soup = BeautifulSoup(back_html, 'html.parser').button

for file in files:
    if file == 'login.html':
        continue
    
    with open(file, 'r') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    header = soup.find('header')
    if header:
        # Find the rightmost flex container to append logout
        # The first child of header is usually a flex container (justify-between)
        header_container = header.find('div', class_=lambda c: c and 'flex' in c and 'justify-between' in c)
        
        if header_container:
            # The right side is usually the last child div of the header_container
            right_side = header_container.find_all('div', recursive=False)
            if right_side:
                target_div = right_side[-1]
                
                # Check if logout already exists
                if not target_div.find('a', string=lambda t: t and 'LOGOUT' in t):
                    target_div.append(logout_soup.__copy__())
            
            # For intermediate pages, add back button
            if file in ['survey-operator.html', 'sonar-ai.html']:
                # The left side is usually the first child div
                left_side = right_side[0]
                if not left_side.find('button', string=lambda t: t and 'Back' in t):
                    left_side.insert(0, back_soup.__copy__())

    with open(file, 'w') as f:
        f.write(str(soup))
    print(f"Processed {file}")

