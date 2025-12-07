import streamlit as st
import pandas as pd
import os
from runner import run_tracking
from history_manager import load_history, save_history
from datetime import datetime
import glob
import uuid

# Password check
APP_PASSWORD = os.getenv("APP_PASSWORD")
password_input = st.sidebar.text_input("🔐 Enter access password", type="password")

if APP_PASSWORD and password_input != APP_PASSWORD:
    st.sidebar.error("Incorrect password.")
    st.stop()

# Force re-run checkbox (outside the password gate)
force_rerun = st.sidebar.checkbox("🔁 Force re-query even if prompt seen before", value=False)

# --- SETUP ---
st.set_page_config(page_title="LLM Visibility Tracker", layout="wide")
st.title("🧠 LLM Visibility Tracker")

PROMPT_SETS_DIR = "data/prompt_sets"
PROMPT_UPLOAD_PATH = "data/prompts.csv"
RESULTS_PATH = "data/results.csv"
os.makedirs(PROMPT_SETS_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)

# --- SIDEBAR SETTINGS ---
st.sidebar.header("Select Chatbots")
platforms = {
    "OpenAI": st.sidebar.checkbox("OpenAI", value=True),
    "Gemini": st.sidebar.checkbox("Gemini", value=False),
    "Claude": st.sidebar.checkbox("Claude", value=False),
    "Perplexity": st.sidebar.checkbox("Perplexity", value=False),
    "Grok": st.sidebar.checkbox("Grok", value=False),
}

brand = st.sidebar.text_input("Brand to track (exact match or keywords)", value="")

# --- PROMPT SOURCE SELECTOR ---
st.subheader("📂 Prompt Source")

mode = st.radio("Prompt Input Mode", ["Upload new", "Use previous"])
prompts_df = None
selected_filename = None

if mode == "Upload new":
    uploaded_file = st.file_uploader("Upload your prompt CSV file", type="csv", key="new-upload")

    if uploaded_file is not None:
        try:
            prompts_df = pd.read_csv(uploaded_file)

            if "prompt" not in prompts_df.columns:
                st.error("❌ Your CSV must contain a 'prompt' column.")
            else:
                if "prompt_id" not in prompts_df.columns:
                    prompts_df["prompt_id"] = [str(uuid.uuid4())[:8] for _ in range(len(prompts_df))]

                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                safe_name = uploaded_file.name.replace(" ", "_")
                selected_filename = f"{timestamp}_{safe_name}"
                full_path = os.path.join(PROMPT_SETS_DIR, selected_filename)
                prompts_df.to_csv(full_path, index=False)

                st.success(f"✅ {len(prompts_df)} prompts uploaded and saved as {selected_filename}.")

        except Exception as e:
            st.error(f"❌ Failed to read CSV: {e}")

elif mode == "Use previous":
    saved_files = sorted(glob.glob(os.path.join(PROMPT_SETS_DIR, "*.csv")), reverse=True)
    file_names = [os.path.basename(f) for f in saved_files]

    if file_names:
        selected_filename = st.selectbox("Select a previously uploaded prompt set:", file_names)
        if selected_filename:
            full_path = os.path.join(PROMPT_SETS_DIR, selected_filename)
            prompts_df = pd.read_csv(full_path)
            st.success(f"✅ Loaded {len(prompts_df)} prompts from {selected_filename}.")
    else:
        st.info("No previous prompt files found. Upload one to get started.")

# --- LOGGING FUNCTION ---
def ui_log(message, level="info"):
    if level == "info":
        st.info(message)
    elif level == "success":
        st.success(message)
    elif level == "warning":
        st.warning(message)
    elif level == "error":
        st.error(message)

# --- RUN TRACKING ---
if st.button("Run LLM Tracking"):
    if prompts_df is None:
        st.error("No prompts loaded. Upload or select a prompt file.")
        st.stop()

    if len(prompts_df) == 0:
        st.error("Prompt file is empty.")
        st.stop()

    with st.status("🚀 Running LLM Tracking...", expanded=True) as status_box:
        st.info(f"Loaded {len(prompts_df)} prompts.")
        st.write(prompts_df.head())

        results = run_tracking(
            prompts_df,
            platform_toggles=platforms,
            brand_keywords=[b.strip() for b in brand.lower().split(",")],
            force=force_rerun,
            log=ui_log
        )

        if results and isinstance(results, list) and "response" in results[0]:
            save_history(results)
            df_out = pd.DataFrame(results)
            df_out.to_csv(RESULTS_PATH, index=False)
            status_box.update(label="✅ Tracking complete.", state="complete")
            st.success("✅ Results saved.")
        else:
            st.error("❌ No results returned. Something went wrong.")
            st.write("Debug: `results` content:")
            st.write(results)
            status_box.update(label="❌ Tracking failed. Check logs.", state="error")

# --- SHOW RESULTS ---
st.subheader("📊 Previous Results (Grouped by Run)")

history_data = load_history()
if history_data:
    df = pd.DataFrame(history_data)

    # Group and reverse
    grouped_runs = list(df.groupby("timestamp", sort=False))
    for ts, group in reversed(grouped_runs):
        with st.expander(f"🕒 Run at {ts} — {len(group)} results", expanded=False):
            display_df = group.drop(columns=["response"])
            st.dataframe(display_df)
else:
    st.info("No results yet.")

# --- EXPORT RESULTS FILE ---
st.subheader("📥 Download Last Results")

if os.path.exists(RESULTS_PATH):
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        st.download_button("⬇️ Download results.csv", f, file_name="results.csv")
else:
    st.info("No results file available yet.")