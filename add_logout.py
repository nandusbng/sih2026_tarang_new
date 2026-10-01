import glob
import re

logout_btn = """
<a href="login.html" onclick="sessionStorage.clear()" style="position: absolute; right: 16px; top: 12px; z-index: 99999;" class="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-red-600 text-white text-xs font-bold shadow-md cursor-pointer transition-colors border border-slate-700">
  <span class="material-symbols-outlined text-[16px]">logout</span> LOGOUT
</a>
"""

files = glob.glob('*.html')
for file in files:
    if file == 'login.html':
        continue
    
    with open(file, 'r') as f:
        content = f.read()
    
    # If already has logout, skip
    if 'LOGOUT' in content and 'login.html' in content:
        continue
        
    # Find the closing </header> tag and insert the button right before it
    # We use absolute positioning relative to the header (which is sticky/fixed)
    # or relative to viewport if header doesn't establish context.
    
    # Actually, we can just insert it right before </header>
    if '</header>' in content:
        content = content.replace('</header>', f"{logout_btn}\n</header>")
        with open(file, 'w') as f:
            f.write(content)
        print(f"Added logout to {file}")

