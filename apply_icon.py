import base64
import re

img_path = r"C:\Users\amalj\.gemini\antigravity\brain\b6b9aee9-8982-4a4a-8bd4-dd1e311d926f\media__1779100717540.png"
with open(img_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")

app_path = "app.py"
with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the copilot float container CSS
old_css = """.copilot-float-container {
        position: fixed !important;
        bottom: 25px !important;
        right: 25px !important;
        z-index: 1000000 !important;
    }"""

new_css = f""".copilot-float-container {{
        position: fixed !important;
        bottom: 25px !important;
        right: 25px !important;
        z-index: 1000000 !important;
    }}
    .copilot-float-container button {{
        background-image: url("data:image/png;base64,{b64}") !important;
        background-size: cover !important;
        background-position: center !important;
        width: 60px !important;
        height: 60px !important;
        border-radius: 50% !important;
        color: transparent !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
        transition: transform 0.2s !important;
    }}
    .copilot-float-container button p {{
        display: none !important;
    }}
    .copilot-float-container button:hover {{
        transform: scale(1.1) !important;
    }}"""

content = content.replace(old_css, new_css)

# Remove the text from the button so it just shows the icon
content = content.replace('if st.button("💬 Hilti Portfolio Copilot", key="copilot_float_trigger", type="secondary"):', 'if st.button("", key="copilot_float_trigger", type="secondary"):')

with open(app_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated app.py successfully!")
