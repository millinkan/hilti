# refactor.py
import re

print("Starting app.py refactoring...")

# Read original app.py
with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Extract Liechtenstein logo from line 185 (0-indexed 184)
# Look for data:image/png;base64,xxxx
l_line = lines[184]
liech_match = re.search(r'data:image/png;base64,([^"]+)', l_line)
if not liech_match:
    print("Liechtenstein logo not found in line 185!")
    exit(1)
liech_base64 = liech_match.group(1)
print("Liechtenstein logo base64 extracted (len={})".format(len(liech_base64)))

# Extract Hilti logo from line 187 (0-indexed 186)
h_line = lines[186]
hilti_match = re.search(r'data:image/png;base64,([^"]+)', h_line)
if not hilti_match:
    print("Hilti logo not found in line 187!")
    exit(1)
hilti_base64 = hilti_match.group(1)
print("Hilti logo base64 extracted (len={})".format(len(hilti_base64)))

# Construct the output list of lines
out_lines = []

# Insert imports and global variables at the top
# Let's insert global variables right after the CURRENCY = "CHF" line (around line 48)
currency_found = False
for i, line in enumerate(lines):
    out_lines.append(line)
    if 'CURRENCY = "CHF"' in line or 'CURRENCY = "EUR"' in line:
        out_lines.append(f'\nLIECHTENSTEIN_LOGO_BASE64 = "{liech_base64}"\n')
        out_lines.append(f'HILTI_LOGO_BASE64 = "{hilti_base64}"\n')
        
        # Set global Plotly dark mode and transparency defaults!
        out_lines.append("\nimport plotly.io as pio\n")
        out_lines.append("plotly_template = pio.templates['plotly_dark']\n")
        out_lines.append("plotly_template.layout.paper_bgcolor = 'rgba(0,0,0,0)'\n")
        out_lines.append("plotly_template.layout.plot_bgcolor = 'rgba(0,0,0,0)'\n")
        out_lines.append("plotly_template.layout.font.color = '#ffffff'\n")
        out_lines.append("plotly_template.layout.font.family = 'Montserrat'\n")
        out_lines.append("pio.templates.default = 'plotly_dark'\n\n")
        currency_found = True

if not currency_found:
    print("WARNING: CURRENCY not found. Inserting logo variables at the top.")
    # Fallback to insert after imports
    out_lines.insert(25, f'\nLIECHTENSTEIN_LOGO_BASE64 = "{liech_base64}"\n')
    out_lines.insert(26, f'HILTI_LOGO_BASE64 = "{hilti_base64}"\n')

# Write output file for testing
with open("app_refactored.py", "w", encoding="utf-8") as f:
    f.writelines(out_lines)

print("First phase done!")
