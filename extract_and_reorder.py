# extract_and_reorder.py
print("Dynamically reordering helper functions globally...")

with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Extract block 1: indices 479 to 762 (exclusive)
# Contains _render_detailed_add and _render_highlevel_add
block1 = lines[479:762]

# Extract block 2: indices 1082 to 1114 (exclusive)
# Contains _finalize_new_project
block2 = lines[1082:1114]

print(f"Block 1 contains {len(block1)} lines.")
print(f"Block 2 contains {len(block2)} lines.")

# Remove block 2 from lines
clean_lines = lines[:1082] + lines[1114:]

# Remove block 1 from clean_lines
# Wait, because block 2 was removed, the indices after block 1 were shifted, 
# but block 1 is before block 2, so the indices for block 1 are unchanged!
clean_lines = clean_lines[:479] + clean_lines[762 - len(block2):]

# Now let's locate "projects = get_projects()" in clean_lines
insert_idx = -1
for i, line in enumerate(clean_lines):
    if "projects = get_projects()" in line:
        insert_idx = i
        break

if insert_idx == -1:
    print("Could not find insertion point!")
    exit(1)

print("Insertion point index:", insert_idx)

# Define full helper content (block 2 defined before block 1 because block 1 calls block 2)
helpers = block2 + ["\n", "\n"] + block1 + ["\n", "\n"]

# Insert globally
final_lines = clean_lines[:insert_idx] + helpers + clean_lines[insert_idx:]

with open("app.py", "w", encoding="utf-8") as f:
    f.writelines(final_lines)

print("Helper functions reordered globally! Let's check syntax.")
