import glob
import re

files = glob.glob('*.html')
for file in files:
    if file == 'login.html':
        continue
    
    with open(file, 'r') as f:
        content = f.read()
    
    # Remove the old absolute positioned logout button
    old_logout_pattern = re.compile(r'<a href="login.html" onclick="sessionStorage.clear\(\)" style="position: absolute; right: 16px; top: 12px; z-index: 99999;" class="flex items-center gap-1 px-3 py-1\.5 rounded-lg bg-slate-800 hover:bg-red-600 text-white text-xs font-bold shadow-md cursor-pointer transition-colors border border-slate-700">\s*<span class="material-symbols-outlined text-\[16px\]">logout</span> LOGOUT\s*</a>\s*</header>', re.MULTILINE)
    
    content = old_logout_pattern.sub('</header>', content)
    
    with open(file, 'w') as f:
        f.write(content)
    print(f"Removed old logout from {file}")

