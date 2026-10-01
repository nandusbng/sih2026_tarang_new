import re
import subprocess
import glob

html_files = glob.glob('*.html')
for hf in html_files:
    with open(hf, 'r', encoding='utf-8') as f:
        content = f.read()
    
    scripts = re.findall(r'<script(?![^>]*src=)[^>]*>(.*?)</script>', content, re.DOTALL)
    for idx, sc in enumerate(scripts):
        if 'tailwind.config' in sc or 'window.location' in sc:
            continue
        # Use an isolated temporary name so existing checked-in test fixtures
        # are never overwritten or removed during a syntax pass.
        test_file = f'__syntaxcheck_{hf}_{idx}.js'
        with open(test_file, 'w', encoding='utf-8') as tf:
            tf.write(sc)
        
        proc = subprocess.run(['node', '--check', test_file], capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"SYNTAX ERROR in {hf} (script {idx}):")
            print(proc.stderr[:400])
        else:
            # print(f"OK: {hf} (script {idx})")
            pass
        try:
            import os
            os.remove(test_file)
        except:
            pass

print("Inspection complete.")
