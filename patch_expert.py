with open('expert-verification.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("localStorage.getItem('marineAnalystData')", "localStorage.getItem('intermediateData')")

with open('expert-verification.html', 'w', encoding='utf-8') as f:
    f.write(content)
