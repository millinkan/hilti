with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
in_copilot_block = False
drawer_indent = ""

for i, line in enumerate(lines):
    if 'if st.session_state["show_copilot"]:' in line:
        in_copilot_block = True
        drawer_indent = line[:len(line) - len(line.lstrip())]
        new_lines.append(line)
        new_lines.append(drawer_indent + "    with st.container():\n")
        new_lines.append(drawer_indent + "        st.markdown('<div class=\"copilot-drawer-anchor\"></div>', unsafe_allow_html=True)\n")
        continue
        
    if in_copilot_block:
        # Check if we exited the block by checking indentation
        if line.strip() and not line.startswith(drawer_indent + " "):
            in_copilot_block = False
            new_lines.append(line)
            continue
            
        # Skip the old raw HTML div tags
        if "st.markdown('<div class=\"copilot-drawer-content\">', unsafe_allow_html=True)" in line:
            continue
        if "st.markdown('</div>', unsafe_allow_html=True)" in line and "chat-scroll-container" not in lines[i-5:i+5]: # Be careful not to remove the scroll container div
            # Actually, let's just remove ANY empty </div> that was meant for the drawer
            if "</div>" in line and "chat-scroll-container" not in "".join(lines[i-10:i]):
                continue

        # Indent the line by 4 spaces
        if line.strip():
            new_lines.append("    " + line)
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

# Add the javascript injection at the very end
js_injection = """
# Inject JS to style the container
import streamlit.components.v1 as components
components.html('''
<script>
    const doc = window.parent.document;
    const anchors = doc.querySelectorAll('.copilot-drawer-anchor');
    anchors.forEach(anchor => {
        const container = anchor.closest('div[data-testid="stVerticalBlock"]');
        if (container) {
            container.classList.add('copilot-drawer-content');
        }
    });
</script>
''', height=0, width=0)
"""
new_lines.append(js_injection)

with open("app.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Updated app.py successfully")
