with open('sonar-ai.html', 'r', encoding='utf-8') as f:
    content = f.read()

class_c_logic = """
            // Push Class C to Intermediate Portal
            if (classC.length > 0) {
                const jsonObjC = {
                    "timestamp": new Date().toISOString(),
                    "system": "TARANG_SONAR_AI",
                    "destination": "INTERMEDIATE",
                    "exported_tier": ["C"],
                    "total_detections": classC.length,
                    "detections": classC
                };
                localStorage.setItem('intermediateData', JSON.stringify(jsonObjC));
            }
            
            // Also save locally as a backup
"""

content = content.replace('// Also save locally as a backup', class_c_logic)
with open('sonar-ai.html', 'w', encoding='utf-8') as f:
    f.write(content)
