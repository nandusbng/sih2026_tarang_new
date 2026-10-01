with open("operator-portal.html", "r") as f:
    content = f.read()
    
# Replace: el.value = `TRG-2026-SRV-${rand}`;
content = content.replace("el.value = `TRG-2026-SRV-${rand}`;", "el.value = crypto.randomUUID();")

with open("operator-portal.html", "w") as f:
    f.write(content)
