with open('login.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace body background and base colors
html = html.replace('background-color: #020b15;', 'background-color: #f8fafc;')
html = html.replace('linear-gradient(180deg, #020b15 0%, #041427 100%)', 'linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)')
html = html.replace('color: #e2e8f0;', 'color: #0f172a;')

# Card styles
old_card = """    .marine-card {
      background: rgba(7, 26, 46, 0.78);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid rgba(20, 184, 166, 0.25);
      box-shadow: 0 20px 45px -10px rgba(0, 0, 0, 0.65), 0 0 25px rgba(20, 184, 166, 0.08);
    }"""

new_card = """    .marine-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      box-shadow: 0 10px 30px -5px rgba(15, 23, 42, 0.08), 0 1px 3px rgba(0, 0, 0, 0.04);
    }"""

html = html.replace(old_card, new_card)

# Replace dark color utility classes
html = html.replace('bg-[#020b15]', 'bg-white')
html = html.replace('bg-[#031326]', 'bg-slate-50')
html = html.replace('bg-[#031120]', 'bg-slate-100')
html = html.replace('bg-[#041324]', 'bg-white')
html = html.replace('bg-[#071d34]', 'bg-slate-50')
html = html.replace('bg-[#08223f]', 'bg-slate-100')
html = html.replace('border-slate-800', 'border-slate-200')
html = html.replace('border-slate-700/80', 'border-slate-300')
html = html.replace('border-slate-700', 'border-slate-200')
html = html.replace('text-white', 'text-slate-900')
html = html.replace('text-slate-300', 'text-slate-700')
html = html.replace('text-slate-400', 'text-slate-500')
html = html.replace('text-sky-400', 'text-teal-700')
html = html.replace('bg-seafoam text-ocean-navy', 'bg-teal-600 text-white')
html = html.replace('hover:bg-teal-400', 'hover:bg-teal-700')
html = html.replace('hover:text-white', 'hover:text-slate-900')

with open('login.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('login.html converted to clean light theme successfully!')
