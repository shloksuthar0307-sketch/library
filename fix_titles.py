import os
import re

for root, dirs, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Replace {% block title %}<title>Something</title>{% endblock %} 
            # with {% block title %}Something{% endblock %}
            new_content = re.sub(
                r'{%\s*block title\s*%}\s*<title>\s*(.*?)\s*</title>\s*{%\s*endblock\s*%}',
                r'{% block title %}\1{% endblock %}',
                content
            )
            
            # Also catch the case where {% endblock %} was missing or on another line?
            # Actually, let's just do a simpler search:
            # Replace <title> inside {% block title %} if it exists.
            
            # If the regex above didn't change anything, try to remove <title> and </title> right after block title
            if new_content == content:
                new_content = re.sub(r'({%\s*block title\s*%})\s*<title>\s*(.*?)\s*</title>', r'\1 \2 ', new_content)
                
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Fixed titles in {filepath}")
