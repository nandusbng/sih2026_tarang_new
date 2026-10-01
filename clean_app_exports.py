with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find second occurrence of @app.route('/api/v1/export/survey/<survey_id>/csv'
idx1 = -1
idx2 = -1
for i, l in enumerate(lines):
    if "/api/v1/export/survey/<survey_id>/csv" in l:
        if idx1 == -1:
            idx1 = i
        else:
            idx2 = i

print(f"First at {idx1}, Second at {idx2}")
if idx2 != -1:
    # Find where @app.route('/api/v1/export/survey/<survey_id>/pdf' starts
    pdf_idx = -1
    for i in range(idx2, len(lines)):
        if "/api/v1/export/survey/<survey_id>/pdf" in lines[i]:
            pdf_idx = i
            break
    if pdf_idx != -1:
        print(f"Removing lines {idx2} to {pdf_idx}")
        del lines[idx2:pdf_idx]

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

import py_compile
py_compile.compile('app.py', doraise=True)
print("app.py successfully cleaned and compiled!")
