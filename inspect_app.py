with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('/api/v1/xtf/upload')
print(text[idx:idx+2500])
