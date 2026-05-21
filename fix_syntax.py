# fix_syntax.py
print("Fixing app.py syntax error...")

# Read current app.py
with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Locate helper functions
# def _render_detailed_add starts at line 856 (index 855)
# elif current_page == '➕ Add Project' starts at line 1115 (index 1114)
helper_start = 855
helper_end = 1114

helper_lines = lines[helper_start:helper_end]
print("Helper functions block length (lines):", len(helper_lines))

# Remove the helper functions from their current location
clean_lines = lines[:helper_start] + lines[helper_end:]

# Find where to insert them. We can insert right before the main block.
# Let's search for "projects = get_projects()" in the clean lines.
insert_idx = -1
for i, line in enumerate(clean_lines):
    if "projects = get_projects()" in line:
        insert_idx = i
        break

if insert_idx == -1:
    print("Could not find insertion point!")
    exit(1)

print("Inserting helper functions globally at index:", insert_idx)

# Insert the helper lines
final_lines = clean_lines[:insert_idx] + helper_lines + clean_lines[insert_idx:]

# Save the final fixed app.py
with open("app.py", "w", encoding="utf-8") as f:
    f.writelines(final_lines)

print("Syntax fix completed successfully!")
