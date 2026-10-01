import re

with open('operator-portal.html', 'r', encoding='utf-8') as f:
    text = f.read()

scripts = re.findall(r'<script>(.*?)</script>', text, re.DOTALL)
print(f"Inline scripts found: {len(scripts)}")
last_script = scripts[-1]

# Check for unclosed brackets or syntax issues
import ast
# We can check JS brackets balance
stack = []
balanced = True
for i, ch in enumerate(last_script):
    if ch in '({[':
        stack.append(ch)
    elif ch in ')}]':
        if not stack:
            print(f"Unmatched closing bracket '{ch}' at pos {i}")
            balanced = False
            break
        top = stack.pop()
        if (top == '(' and ch != ')') or (top == '{' and ch != '}') or (top == '[' and ch != ']'):
            print(f"Mismatched bracket '{top}' vs '{ch}' at pos {i}")
            balanced = False
            break

if balanced and not stack:
    print("JS bracket syntax is 100% BALANCED!")
elif stack:
    print(f"Unclosed brackets remaining: {stack}")
