import os

html_files = [f for f in os.listdir('.') if f.endswith('.html')]
chatbot_script = '<script src="/js/chatbot.js" defer></script>'

for f in html_files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if chatbot_script not in content:
        # Inject just before </body>
        if '</body>' in content:
            content = content.replace('</body>', f'{chatbot_script}\n</body>')
        else:
            content += f'\n{chatbot_script}'
            
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Injected chatbot into {f}")
print("Finished injecting chatbot.")
