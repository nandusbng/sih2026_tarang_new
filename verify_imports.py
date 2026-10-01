"""Verify all supporting modules import cleanly and app.py has no issues."""
import sys, ast, os
sys.path.insert(0, os.path.dirname(__file__))

results = []

# 1. Syntax check app.py
with open('app.py', 'r', encoding='utf-8') as f:
    src = f.read()
try:
    ast.parse(src)
    results.append('PASS  app.py syntax OK')
except SyntaxError as e:
    results.append(f'FAIL  app.py syntax error line {e.lineno}: {e.msg}')

# 2. Import supporting modules
for mod in ['supabase_service', 'tarang_geo', 'dbscan_service', 'tarang_status', 'xtf_parser']:
    try:
        __import__(mod)
        results.append(f'PASS  {mod} imports OK')
    except Exception as e:
        results.append(f'FAIL  {mod}: {e}')

# 3. Check no old role aliases remain in require_roles
old_aliases = ['marine_analyst', 'gov_authority']
issues = []
for i, line in enumerate(src.splitlines(), 1):
    if 'require_roles' in line or 'authorize_request' in line:
        for alias in old_aliases:
            if f"'{alias}'" in line:
                issues.append(f'  Line {i}: {line.strip()}')
if issues:
    results.append(f'WARN  Old role aliases found in {len(issues)} require_roles calls:')
    results.extend(issues)
else:
    results.append('PASS  No old role aliases in require_roles decorators')

# 4. Check reject_cleanup bug is fixed
if 'return record_cleanup_decision(target_id)' in src:
    results.append('FAIL  reject_cleanup bug still present: calls record_cleanup_decision() as plain function')
else:
    results.append('PASS  reject_cleanup bug fixed (inline logic)')

# 5. Count route definitions
route_count = src.count("@app.route(")
results.append(f'INFO  Total @app.route decorators: {route_count}')

# Print all
for r in results:
    print(r, flush=True)

failures = [r for r in results if r.startswith('FAIL')]
if failures:
    print(f'\n{len(failures)} FAILURE(S) FOUND', flush=True)
    sys.exit(1)
else:
    print('\nAll checks passed.', flush=True)
