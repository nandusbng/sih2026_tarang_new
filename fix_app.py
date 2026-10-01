with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

chatbot_marker = "# ---------------------------------------------------------\n# Chatbot API Route"
if chatbot_marker in content:
    # Extract the chatbot code
    parts = content.split(chatbot_marker)
    chatbot_code = chatbot_marker + parts[1]
    
    # Remove from bottom
    content = parts[0]
    
    # Insert before main
    main_marker = "# ===========================================================================\n# MAIN"
    if main_marker in content:
        content = content.replace(main_marker, chatbot_code + "\n" + main_marker)
        
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully moved chatbot route.")
    else:
        print("Main marker not found.")
else:
    print("Chatbot marker not found.")
