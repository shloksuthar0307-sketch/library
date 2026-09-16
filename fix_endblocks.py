import os
import re

for root, dirs, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # If block title is not followed by {% endblock %} on the same line
            # Wait, a safer regex:
            # Find {% block title %}... and if there's no {% endblock %} before a newline, add it.
            lines = content.split('\n')
            changed = False
            for i, line in enumerate(lines):
                if '{% block title %}' in line and '{% endblock %}' not in line:
                    lines[i] = line + '{% endblock %}'
                    changed = True
                    
            if changed:
                new_content = '\n'.join(lines)
                # Now we need to remove the extra {% endblock %} at the end of the file if it exists,
                # but only if we added one. Actually, Django templates usually have {% block content %} ... {% endblock %}.
                # If there are two {% endblock %} at the end, let's just let the developer or a simple clean-up handle it. 
                # Wait, if we add an endblock, it might leave an orphaned endblock at the end of the file.
                # Let's count blocks and endblocks. If endblocks > blocks, remove from the end.
                
                blocks_count = len(re.findall(r'{%\s*block\s+\w+\s*%}', new_content))
                endblocks_count = len(re.findall(r'{%\s*endblock\s*%}', new_content))
                
                if endblocks_count > blocks_count:
                    # Remove the last endblock
                    new_content = new_content[::-1].replace('}* kcolbdne *{%', '', 1)[::-1]
                    # Note: reversing string to replace last occurrence is tricky with regex. 
                    # Let's use re.sub with a negative lookahead or just standard rsplit
                    parts = new_content.rsplit('{% endblock %}', 1)
                    new_content = ''.join(parts)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Fixed missing endblock in {filepath}")
