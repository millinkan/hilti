# refactor_all.py
import re

print("Running deep refactoring on app.py...")

# Read original app.py
with open("app.py", "r", encoding="utf-8") as f:
    original_code = f.read()

# 1. Extract the base64 logos
lines = original_code.splitlines()

liech_line = lines[184]
liech_match = re.search(r'data:image/png;base64,([^"]+)', liech_line)
if not liech_match:
    print("Liechtenstein logo not found in line 185!")
    exit(1)
liech_base64 = liech_match.group(1)

hilti_line = lines[186]
hilti_match = re.search(r'data:image/png;base64,([^"]+)', hilti_line)
if not hilti_match:
    print("Hilti logo not found in line 187!")
    exit(1)
hilti_base64 = hilti_match.group(1)

# 2. Extract the intelligence logic from tab_copilot (lines 1208 to 1350)
# Let's locate "with tab_copilot:" in the file and print where it is
copilot_start = original_code.find("with tab_copilot:")
if copilot_start == -1:
    print("with tab_copilot: not found!")
    exit(1)

# Find the next tab start "with tab_interdept:"
copilot_end = original_code.find("with tab_interdept:")
if copilot_end == -1:
    print("with tab_interdept: not found!")
    exit(1)

copilot_block = original_code[copilot_start:copilot_end]
# We will parse out the local response generation logic from copilot_block
# Let's extract the response generation part, which is after "if prompt := st.chat_input"
# Let's find "query = prompt.lower().strip()"
query_start = copilot_block.find("query = prompt.lower().strip()")
if query_start == -1:
    print("query_start not found in copilot block!")
    exit(1)

# The response processing logic ends right before "with st.chat_message(\"assistant\"):" or similar
# Let's check how the block ends
# In the original, the block has:
#         with st.chat_message("assistant"):
#             st.markdown(response)
#         st.session_state.copilot_messages.append({"role": "assistant", "content": response})
response_end_marker = 'with st.chat_message("assistant"):\n            st.markdown(response)'
resp_marker_idx = copilot_block.find(response_end_marker)
if resp_marker_idx == -1:
    # try single quote
    response_end_marker = "with st.chat_message('assistant'):\n            st.markdown(response)"
    resp_marker_idx = copilot_block.find(response_end_marker)

if resp_marker_idx == -1:
    print("response_end_marker not found in copilot block!")
    exit(1)

intelligence_logic = copilot_block[query_start:resp_marker_idx]
print("Extracted intelligence logic of len={}".format(len(intelligence_logic)))

# Now let's perform replacements in the code string

# Replacement A: Define global variables and Plotly dark overrides near imports
# We replace currency definition with currency + global variables + Plotly dark mode config
original_currency_block = 'CURRENCY = "CHF"'
if original_currency_block not in original_code:
    original_currency_block = 'CURRENCY = "EUR"'

new_currency_block = f"""{original_currency_block}

LIECHTENSTEIN_LOGO_BASE64 = "{liech_base64}"
HILTI_LOGO_BASE64 = "{hilti_base64}"

import plotly.io as pio
plotly_template = pio.templates['plotly_dark']
plotly_template.layout.paper_bgcolor = 'rgba(0,0,0,0)'
plotly_template.layout.plot_bgcolor = 'rgba(0,0,0,0)'
plotly_template.layout.font.color = '#ffffff'
plotly_template.layout.font.family = 'Montserrat'
pio.templates.default = 'plotly_dark'
"""
code = original_code.replace(original_currency_block, new_currency_block, 1)

# Replacement B: Main window header logos replaced by premium hamburger and arrow
original_logos_block = """l_col1, l_col2, _ = st.columns([1, 1, 6])
with l_col1:
    st.image(f"data:image/png/base64," + liech_base64 + '", width=250)
with l_col2:
    st.image(f"data:image/png/base64," + hilti_base64 + '", width=100)"""

# Actually, the original lines are:
# l_col1, l_col2, _ = st.columns([1, 1, 6])
# with l_col1:
#     st.image(f"data:image/png;base64,iVBORw...K5CYII=", width=250)
# with l_col2:
#     st.image(f"data:image/png;base64,iVBORw...kJggg==", width=100)

# We can search and replace the whole block dynamically.
# Let's locate the column definition:
logos_def_start = code.find("l_col1, l_col2, _ = st.columns([1, 1, 6])")
if logos_def_start == -1:
    print("l_col1 definition not found!")
    exit(1)

# Find st.title("Project Prioritization")
title_start = code.find('st.title("Project Prioritization")')
if title_start == -1:
    print('st.title not found!')
    exit(1)

new_header_block = """l_col1, l_col2, _ = st.columns([0.5, 0.5, 7.0])
with l_col1:
    st.markdown("<span style='font-size: 2.2rem; color: #D2051E; font-weight: bold; cursor: pointer; user-select: none;' title='Menu'>≡</span>", unsafe_allow_html=True)
with l_col2:
    st.markdown("<span style='font-size: 2.2rem; color: #D2051E; font-weight: bold; cursor: pointer; user-select: none;' title='Back'>←</span>", unsafe_allow_html=True)


"""
code = code[:logos_def_start] + new_header_block + code[title_start:]

# Replacement C: Update CSS overrides block to add the custom styles
css_override_start = """    .stTabs [data-baseweb="tab-highlight"] {
        background-color: rgba(210, 5, 30, 0.95);
        height: 3px;
    }
</style>"""

css_override_replacement = """    .stTabs [data-baseweb="tab-highlight"] {
        background-color: rgba(210, 5, 30, 0.95);
        height: 3px;
    }
    
    /* Custom Sidebar Cards Navigation */
    div[data-testid="stRadio"] > label {
        display: none !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 12px !important;
        background-color: transparent !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 14px 18px !important;
        color: #e0e0e0 !important;
        cursor: pointer !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        width: 100% !important;
        margin: 0 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"] div:first-child {
        display: none !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"]:hover {
        background: rgba(210, 5, 30, 0.12) !important;
        border-color: rgba(210, 5, 30, 0.4) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 16px rgba(210, 5, 30, 0.2) !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"][data-checked="true"],
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"]:has(input[checked]) {
        background: linear-gradient(135deg, #D2051E 0%, #96000F 100%) !important;
        border-color: #D2051E !important;
        color: white !important;
        font-weight: 600 !important;
        box-shadow: 0 6px 20px rgba(210, 5, 30, 0.45) !important;
    }
    
    /* Glassmorphic Top KPI Cards */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 18px 24px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    div[data-testid="metric-container"]:hover {
        background: rgba(255, 255, 255, 0.06) !important;
        border-color: rgba(210, 5, 30, 0.3) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 24px rgba(210, 5, 30, 0.15) !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.9rem !important;
        font-weight: 700 !important;
        color: #D2051E !important;
        font-family: 'Montserrat', sans-serif !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        color: #a0a0a0 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
    }
    
    /* Global Glassmorphic Plotly Card Containers */
    div[data-testid="stPlotlyChart"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 20px !important;
        padding: 20px !important;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35) !important;
        backdrop-filter: blur(15px) !important;
        -webkit-backdrop-filter: blur(15px) !important;
        margin-bottom: 24px !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    div[data-testid="stPlotlyChart"]:hover {
        background: rgba(255, 255, 255, 0.05) !important;
        border-color: rgba(210, 5, 30, 0.25) !important;
        box-shadow: 0 12px 40px rgba(210, 5, 30, 0.18) !important;
        transform: translateY(-3px) !important;
    }
    
    /* Floating AI Assistant Trigger & Drawer overlay */
    .copilot-float-container {
        position: fixed !important;
        bottom: 25px !important;
        right: 25px !important;
        z-index: 1000000 !important;
    }
    .copilot-drawer-content {
        position: fixed !important;
        bottom: 90px !important;
        right: 25px !important;
        width: 420px !important;
        height: 620px !important;
        background: rgba(20, 20, 20, 0.65) !important;
        backdrop-filter: blur(35px) !important;
        -webkit-backdrop-filter: blur(35px) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 24px !important;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6) !important;
        z-index: 999999 !important;
        padding: 20px !important;
        display: flex !important;
        flex-direction: column !important;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
        animation: drawerSlideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    @keyframes drawerSlideIn {
        from { opacity: 0; transform: translateY(20px) scale(0.95); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }
    .chat-scroll-container {
        overflow-y: auto !important;
        height: calc(100% - 130px) !important;
        margin-bottom: 70px !important;
        padding-right: 5px !important;
    }
    .chat-scroll-container::-webkit-scrollbar {
        width: 6px;
    }
    .chat-scroll-container::-webkit-scrollbar-track {
        background: transparent;
    }
    .chat-scroll-container::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.15);
        border-radius: 3px;
    }
    .chat-scroll-container::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.3);
    }
    .copilot-drawer-content div[data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 10px 15px !important;
        margin-bottom: 12px !important;
    }
    .copilot-drawer-content div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {
        background: rgba(210, 5, 30, 0.1) !important;
        border-color: rgba(210, 5, 30, 0.2) !important;
    }
    .copilot-drawer-content div[data-testid="stChatInput"] {
        position: absolute !important;
        bottom: 20px !important;
        left: 20px !important;
        width: calc(100% - 40px) !important;
        background: rgba(30, 30, 30, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 12px !important;
        z-index: 1000000 !important;
    }
</style>

<script>
    const applyFloatStyles = () => {
        const doc = window.parent.document;
        const buttons = doc.querySelectorAll('button');
        buttons.forEach(btn => {
            if (btn.textContent.includes('💬 Hilti Portfolio Copilot')) {
                const container = btn.closest('div[data-testid="element-container"]');
                if (container) {
                    container.style.position = 'fixed';
                    container.style.bottom = '25px';
                    container.style.right = '25px';
                    container.style.zIndex = '1000000';
                    
                    btn.style.background = 'linear-gradient(135deg, #D2051E, #96000F)';
                    btn.style.color = 'white';
                    btn.style.border = '1px solid rgba(255,255,255,0.2)';
                    btn.style.borderRadius = '50px';
                    btn.style.padding = '12px 28px';
                    btn.style.fontWeight = 'bold';
                    btn.style.fontSize = '0.95rem';
                    btn.style.boxShadow = '0 8px 32px rgba(210, 5, 30, 0.4)';
                    btn.style.transition = 'all 0.2s ease-in-out';
                }
            }
            if (btn.textContent === '✕' && btn.closest('.copilot-drawer-content')) {
                btn.style.background = 'transparent';
                btn.style.border = 'none';
                btn.style.color = 'rgba(255,255,255,0.6)';
                btn.style.fontSize = '1.2rem';
                btn.style.fontWeight = 'bold';
                btn.style.cursor = 'pointer';
            }
        });
    };
    setTimeout(applyFloatStyles, 100);
    const observer = new MutationObserver(applyFloatStyles);
    observer.observe(window.parent.document.body, { childList: true, subtree: true });
</script>"""

code = code.replace(css_override_start, css_override_replacement, 1)

# Replacement D: Replace st.sidebar block entirely
sidebar_start = code.find("with st.sidebar:")
if sidebar_start == -1:
    print("with st.sidebar: not found!")
    exit(1)

# Let's find projects = get_projects() which marks the end of the sidebar block
sidebar_end = code.find("projects = get_projects()")
if sidebar_end == -1:
    sidebar_end = code.find("projects = load_projects()")
if sidebar_end == -1:
    print("sidebar_end indicator not found!")
    exit(1)

new_sidebar_block = """with st.sidebar:
    # 1. Co-branding HTML Logos
    st.markdown(
        f\"\"\"
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 25px; padding: 12px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; backdrop-filter: blur(8px); box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
            <img src="data:image/png;base64,{LIECHTENSTEIN_LOGO_BASE64}" style="max-height: 38px; width: auto; opacity: 0.95;">
            <img src="data:image/png;base64,{HILTI_LOGO_BASE64}" style="max-height: 38px; width: auto; opacity: 0.95;">
        </div>
        \"\"\",
        unsafe_allow_html=True
    )
    
    # 2. Page Navigation Section Title
    st.markdown("<h3 style='color: #ffffff; margin-top: 5px; margin-bottom: 12px; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 700; opacity: 0.75;'>Navigation</h3>", unsafe_allow_html=True)
    
    # Store page navigation in session state
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "📊 Dashboard"
        
    pages = ["📊 Dashboard", "📋 Ranking", "📈 Project Details", "🎲 Risk", "🕹️ Scenario Simulation", "🤝 Interdepartmental Hub", "➕ Add Project", "📖 User Guide"]
    
    selected_page = st.radio(
        "Navigation",
        pages,
        index=pages.index(st.session_state["current_page"]),
        label_visibility="collapsed"
    )
    st.session_state["current_page"] = selected_page
    
    st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)
    
    # 3. Compact Collapsible Panel for Configuration Widgets
    with st.expander("⚙️ Controls & Parameters", expanded=False):
        st.subheader("Scoring Weights")
        st.caption("Total net profit is the primary signal; break-even speed is the tiebreaker.")
        weight_value = st.slider("Weight: total net profit", 0.0, 1.0, 0.75, 0.05)
        weight_speed = st.slider("Weight: break-even speed", 0.0, 1.0, 0.25, 0.05)
        
        st.divider()
        st.subheader("Prioritization Algorithm")
        prio_method = st.selectbox("Select Method", ["Composite", "WSJF", "ROI"], help="WSJF: Value/Duration. ROI: Value/Cost. Composite: Weighted NP + Speed.")
        
        st.divider()
        st.subheader("Prototype Phase 2: Constraints")
        st.caption("Budget and Resource constraints for advanced optimization.")
        execution_mode = st.radio("Execution Mode", ["Sequential", "Parallel"], help="Determine how projects overlap.")
        
        enable_budget = st.checkbox("Enable Total Budget Limit", value=True)
        total_budget = st.number_input("Total Budget (CHF)", value=50000000.0, step=1000000.0, format="%.0f") if enable_budget else None
        
        enable_monthly = st.checkbox("Enable Monthly Spend Limit")
        max_monthly_spend = st.number_input("Max Monthly Spend (CHF)", value=2000000.0, step=500000.0, format="%.0f") if enable_monthly else None
        
        enable_concurrency = st.checkbox("Enable Concurrency Limit")
        max_concurrency = st.number_input("Max Concurrent Projects", value=10, min_value=1, step=1) if enable_concurrency else None
        
        st.divider()
        st.subheader("Portfolio Generator")
        st.caption("Regenerate the sample portfolio from scratch (overwrites CSVs).")
        seed = st.number_input("Random seed", value=42, step=1)
        n_projects = st.number_input("Number of projects", value=100, min_value=10, max_value=500, step=10)
        if st.button("Regenerate sample data", type="secondary"):
            save_projects(generate_projects(n_projects=int(n_projects), seed=int(seed)))
            st.cache_data.clear()
            st.success(f"Generated {int(n_projects)} projects.")
            st.rerun()

st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)


"""

code = code[:sidebar_start] + new_sidebar_block + code[sidebar_end:]

# Replacement E: Comment out the st.tabs line
tabs_line_start = code.find("tab_dashboard, tab_ranking, tab_charts, tab_simulation, tab_scenario, tab_copilot, tab_interdept, tab_add, tab_guide = st.tabs(")
if tabs_line_start == -1:
    print("st.tabs line not found!")
    exit(1)

# Find the matching closing parenthesis ")\n"
tabs_line_end = code.find(")\n", tabs_line_start)
if tabs_line_end == -1:
    tabs_line_end = code.find(")", tabs_line_start)

# We can replace this st.tabs statement with session state initialization
replacement_tabs = 'current_page = st.session_state.get("current_page", "📊 Dashboard")\n'
code = code[:tabs_line_start] + replacement_tabs + code[tabs_line_end+2:]

# Replacement F: Replace "with tab_dashboard:" and remove duplicate metric block
# The dashboard starts with "with tab_dashboard:"
tab_db_idx = code.find("with tab_dashboard:")
if tab_db_idx == -1:
    print("with tab_dashboard: not found!")
    exit(1)

# Inside tab_dashboard:
#     st.subheader("Portfolio Dashboard")
#     
#     # Selected Portfolio KPIs
#     st.markdown("#### Selected Portfolio Overview")
#     db_c1, db_c2, db_c3, db_c4 = st.columns(4)
#     ...
#     st.markdown("---")
#
# We want to replace "with tab_dashboard:" with "if current_page == '📊 Dashboard':"
# and we want to remove the metrics block entirely (lines 359-370 in original)
# Let's locate the metrics block in the code:
db_overview_start = code.find('st.markdown("#### Selected Portfolio Overview")', tab_db_idx)
if db_overview_start == -1:
    print("Selected Portfolio Overview not found!")
    exit(1)

# The block ends after the st.markdown("---") or similar.
# Let's find "st.markdown(\"--- \")" or "st.markdown(\"---\")"
db_overview_end = code.find('st.markdown("---")', db_overview_start)
if db_overview_end == -1:
    print("st.markdown(---) not found inside Dashboard overview!")
    exit(1)

# Remove the overview block
code = code.replace("with tab_dashboard:", "if current_page == '📊 Dashboard':", 1)
code = code[:db_overview_start] + "pass" + code[db_overview_end + len('st.markdown("---")'):]

# Replacement G: Replace remaining "with tab_..." wrappers with conditional blocks
tab_replacements = [
    ("with tab_ranking:", "elif current_page == '📋 Ranking':"),
    ("with tab_charts:", "elif current_page == '📈 Project Details':"),
    ("with tab_simulation:", "elif current_page == '🎲 Risk':"),
    ("with tab_scenario:", "elif current_page == '🕹️ Scenario Simulation':"),
    ("with tab_interdept:", "elif current_page == '🤝 Interdepartmental Hub':"),
    ("with tab_add:", "elif current_page == '➕ Add Project':"),
    ("with tab_guide:", "elif current_page == '📖 User Guide':")
]

for orig_tab, new_tab in tab_replacements:
    if orig_tab not in code:
        print(f"WARNING: {orig_tab} not found!")
    code = code.replace(orig_tab, new_tab, 1)

# Replacement H: Remove tab_copilot completely from the middle of the file
# Let's find "with tab_copilot:" in the modified code
copilot_tab_start = code.find("with tab_copilot:")
if copilot_tab_start == -1:
    print("with tab_copilot: not found for removal!")
    exit(1)

# Find the next tab start, which is "elif current_page == '🤝 Interdepartmental Hub':"
interdept_tab_start = code.find("elif current_page == '🤝 Interdepartmental Hub':")
if interdept_tab_start == -1:
    print("Interdepartmental Hub tab start not found!")
    exit(1)

# Remove the entire Copilot tab block from the middle of the file
code = code[:copilot_tab_start] + code[interdept_tab_start:]

# Replacement I: Append the new Floating AI Assistant Widget code at the very end of app.py!
floating_copilot_code = f"""

# --------------------------------------------------------------------------
# Floating AI Portfolio Copilot Widget (Phase 2 Premium Drawer)
# --------------------------------------------------------------------------

# Initialize copilot state
if "show_copilot" not in st.session_state:
    st.session_state["show_copilot"] = False

# 1. Render the beautiful floating circle button in the bottom right corner
st.markdown('<div class="copilot-float-container">', unsafe_allow_html=True)
if st.button("💬 Hilti Portfolio Copilot", key="copilot_float_trigger", type="secondary"):
    st.session_state["show_copilot"] = not st.session_state["show_copilot"]
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# 2. Render the glassmorphic overlay drawer if active
if st.session_state["show_copilot"]:
    st.markdown('<div class="copilot-drawer-content">', unsafe_allow_html=True)
    
    # Header with title and close button
    col_header_left, col_header_right = st.columns([8, 2])
    with col_header_left:
        st.markdown("<h4 style='margin: 0; color: white; font-family: Montserrat; font-weight: 700;'>💬 Portfolio Copilot</h4>", unsafe_allow_html=True)
    with col_header_right:
        if st.button("✕", key="close_copilot_drawer_btn", type="secondary", help="Close Copilot"):
            st.session_state["show_copilot"] = False
            st.rerun()
            
    st.markdown("<div style='border-bottom: 1px solid rgba(255,255,255,0.1); margin-top: 10px; margin-bottom: 15px;'></div>", unsafe_allow_html=True)
    
    # Initialize message history
    if "copilot_messages" not in st.session_state:
        st.session_state.copilot_messages = [
            {{
                "role": "assistant",
                "content": "Welcome to your Hilti Portfolio Copilot! I am a smart assistant powered by the active prioritizations and scheduling filters.\\n\\n"
                           "Here are some examples of what you can ask me:\\n"
                           "- **'Compare P-0001 and P-0002'**: Show a detailed side-by-side metric comparison.\\n"
                           "- **'What if we reduce budget to 15M CHF?'**: Instantly simulate a new budget constraint.\\n"
                           "- **'What are our top 3 projects?'**: Analyze the current top ranked projects.\\n"
                           "- **'Which archetype is most expensive?'**: Analyze the distribution of costs."
            }}
        ]
        
    # Scrollable chat messages container
    st.markdown('<div class="chat-scroll-container">', unsafe_allow_html=True)
    for msg in st.session_state.copilot_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Native chat input absolute-positioned inside the drawer
    if prompt := st.chat_input("Ask a question about your portfolio...", key="copilot_chat_input"):
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.copilot_messages.append({{"role": "user", "content": prompt}})
        
        # Process answer locally using the exact same intelligence logic!
        query = prompt.lower().strip()
        response = ""
        
        # Extracted local intelligence logic:
{intelligence_logic}
        
        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.copilot_messages.append({{"role": "assistant", "content": response}})
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
"""

code += floating_copilot_code

# Save the refactored code to app.py!
with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Full deep refactoring of app.py completed successfully!")
