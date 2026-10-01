with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("                writer.write(annotated)", "                if writer.isOpened():\n                    writer.write(annotated)")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
