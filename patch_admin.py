with open('admin-dashboard.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Replace classes
c = c.replace('class="h-full bg-[#020b15]"', 'class="h-full bg-slate-50"')
c = c.replace('bg-[#020b15]', 'bg-slate-50')
c = c.replace('bg-[#031326]', 'bg-white')
c = c.replace('bg-[#08223f]', 'bg-slate-100')
c = c.replace('text-slate-100', 'text-slate-900')
c = c.replace('text-white', 'text-slate-900')
c = c.replace('border-slate-800', 'border-slate-200')
c = c.replace('divide-slate-800/60', 'divide-slate-200')
c = c.replace('text-slate-300', 'text-slate-700')
c = c.replace('text-slate-400', 'text-slate-500')

# Update CSS in <style>
old_style = """  <style>
    .marine-panel {
      background: linear-gradient(135deg, rgba(3, 19, 38, 0.95), rgba(2, 11, 21, 0.98));
      backdrop-filter: blur(12px);
    }
    .marine-card {
      background: rgba(3, 19, 38, 0.7);
      border: 1px solid rgba(20, 184, 166, 0.2);
      transition: all 0.2s ease-in-out;
    }
    .marine-card:hover {
      border-color: rgba(20, 184, 166, 0.4);
    }
    .custom-scrollbar::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
      background: rgba(3, 18, 36, 0.5);
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
      background: rgba(20, 184, 166, 0.3);
      border-radius: 4px;
    }
  </style>"""

new_style = """  <style>
    body {
      background-color: #f8fafc;
      color: #0f172a;
      font-family: 'Inter', sans-serif;
    }
    .marine-panel {
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(12px);
      border-color: #e2e8f0;
    }
    .marine-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      transition: all 0.2s ease-in-out;
      box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04);
    }
    .marine-card:hover {
      border-color: #cbd5e1;
      box-shadow: 0 6px 18px -4px rgba(15, 23, 42, 0.06);
    }
    .custom-scrollbar::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
      background: #f1f5f9;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
      background: #cbd5e1;
      border-radius: 4px;
    }
  </style>"""

if old_style in c:
    c = c.replace(old_style, new_style)

# Active button style in script
c = c.replace("bg-seafoam text-ocean-navy shadow-sm", "bg-teal-600 text-white shadow-sm")
c = c.replace("hover:bg-[#08223f]", "hover:bg-slate-100 hover:text-slate-900")

with open('admin-dashboard.html', 'w', encoding='utf-8') as f:
    f.write(c)

print('admin-dashboard.html successfully converted to light theme!')
