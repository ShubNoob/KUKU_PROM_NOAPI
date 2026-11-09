"""
Streamlit app for the Promo Extractor.

    streamlit run app.py

- Run on scripts: upload a zip of episode .txt files; rules mode (default) needs no API
  key and runs a 50-episode show in seconds.
- View results: upload a promos.json from an earlier run (e.g. from the Colab notebook).
Scripts are processed in a temporary folder for this session only and are not stored.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Promo Extractor", page_icon="🎬", layout="wide")
HERE = Path(__file__).parent

MODELS = {"rules": "", "openai": "gpt-5-mini", "anthropic": "claude-sonnet-5-5",
          "gemini": "gemini-flash-latest", "openai_compatible": ""}
KEYS = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY", "openai_compatible": "OPENAI_API_KEY"}


def secret(name: str) -> str:
    try:                                   # Streamlit Cloud: Settings -> Secrets
        return st.secrets.get(name, "")
    except Exception:                      # no secrets file when running locally
        return ""


# ----------------------------------------------------------------------------- sidebar
st.sidebar.title("🎬 Promo Extractor")
mode = st.sidebar.radio("Mode", ["Run on scripts", "View results"])

if mode == "View results":
    up = st.sidebar.file_uploader("promos.json from a run", type="json")
    if up:
        st.session_state["result"] = json.load(up)
        st.session_state["files"] = {}

else:
    zip_up = st.sidebar.file_uploader("Episode scripts (.zip of .txt files)", type="zip")
    provider = st.sidebar.selectbox(
        "Engine", list(MODELS),
        format_func=lambda p: {"rules": "Rules (no API key)", "openai": "OpenAI",
                               "anthropic": "Claude", "gemini": "Gemini",
                               "openai_compatible": "OpenAI-compatible"}[p])
    model, key, key_env = "", "", KEYS.get(provider, "")
    if provider != "rules":
        model = st.sidebar.text_input("Model", MODELS[provider])
        key = st.sidebar.text_input(f"API key ({key_env})", type="password",
                                    value=secret(key_env))
        st.sidebar.caption("LLM mode makes ~6 calls per episode; try a few episodes first.")
    episodes = st.sidebar.text_input("Episodes", "", help="e.g. 1-3 or 1,5,9; empty = all")

    if st.sidebar.button("Find promos", type="primary", disabled=zip_up is None):
        work = Path(tempfile.mkdtemp())
        zpath = work / "scripts.zip"
        zpath.write_bytes(zip_up.getvalue())
        env = dict(os.environ)
        if key:
            env[key_env] = key
        cmd = [sys.executable, str(HERE / "run.py"), str(zpath), "--out", str(work / "out"),
               "--provider", provider, "--show", Path(zip_up.name).stem]
        if model:
            cmd += ["--model", model]
        if episodes.strip():
            cmd += ["--episodes", episodes.strip()]
        log, lines = st.empty(), []
        with st.spinner("Finding promos..."):
            p = subprocess.Popen(cmd, cwd=HERE, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True)
            for line in p.stdout:
                lines.append(line.rstrip())
                log.code("\n".join(lines[-12:]))
            p.wait()
        out = work / "out"
        if p.returncode == 0 and (out / "promos.json").exists():
            log.empty()
            st.session_state["result"] = json.loads((out / "promos.json").read_text())
            st.session_state["files"] = {f.name: f.read_bytes() for f in sorted(out.iterdir())}
        else:
            st.error("The run failed. The last lines of its log are shown above.")

data = st.session_state.get("result")
files = st.session_state.get("files", {})


# ----------------------------------------------------------------------------- landing
if not data:
    st.title("Promo Extractor")
    st.markdown(
        "Finds **20–60 second promo clips** in a microdrama's screenplays: a hook in the "
        "first 3 seconds, a cliffhanger at the cut, and clear to someone who has never seen "
        "the show. Every promo comes with its episode, exact timestamps, hook, cliffhanger "
        "and why it works, ranked by what to post first.\n\n"
        "**To try it:** upload a zip of episode `.txt` scripts in the sidebar and press "
        "**Find promos**. Rules mode needs no API key.\n\n"
        "Code and method: [github.com/ShubNoob/KUKU_PROM_NOAPI]"
        "(https://github.com/ShubNoob/KUKU_PROM_NOAPI)")
    st.caption("Scripts are processed in a temporary folder for this session and not stored.")
    st.stop()


# ----------------------------------------------------------------------------- results
meta, promos, rejected = data["meta"], data["promos"], data.get("rejected_hooks", [])
tiers = {str(k): v for k, v in meta["tier_counts"].items()}
st.title(f"Promos · {meta.get('show', '')}")
c = st.columns(5)
c[0].metric("Episodes", meta["episodes"])
c[1].metric("Clips judged", meta["clips_judged"])
c[2].metric("Ready to post", tiers.get("1", 0))
c[3].metric("Rejected by checks", meta["rejected_before_judging"])
c[4].metric("Engine", meta["model"])
if meta.get("stopped_early"):
    st.warning(f"Partial run: {meta['stopped_early']}")

dl = st.columns(4)
dl[0].download_button("promos.json", json.dumps(data, indent=2), "promos.json")
for col, name in zip(dl[1:], ("promos.csv", "shortlist.md", "hand_check.csv")):
    if name in files:
        col.download_button(name, files[name], name)


def card(r):
    s = r["segments"][0]
    head = f"#{r['rank']} · " if r.get("rank") else ""
    with st.container(border=True):
        st.markdown(f"**{head}{r['title']}** · `{r['clip_id']}` · Episode {s['episode']} · "
                    f"**{s['start_ts']} → {s['end_ts']}** ({r['duration']:.0f}s)")
        st.markdown(f"🪝 **Hook:** {r['hook_text']}  \n"
                    f"⏸️ **Cliffhanger:** {r['cliffhanger_text']}  \n"
                    f"💡 **Why it works:** {r['why_it_works']}")
        cols = st.columns(3)
        cols[0].caption(f"Hook {r['hook_intensity_score']}/10")
        cols[1].caption(f"Cliffhanger {r['cliffhanger_intensity_score']}/10")
        cols[2].caption(f"Middle {r['middle_story_engagement_score']}/10")
        if r.get("rank_reason"):
            st.caption(f"Rank reason: {r['rank_reason']}")
        if r.get("timing_note"):
            st.caption(f"⚠️ {r['timing_note']}")
        if r.get("overlaps_with"):
            st.caption(f"Overlaps with {', '.join(r['overlaps_with'])}")


t1 = [r for r in promos if r["tier"] == 1]
t2 = [r for r in promos if r["tier"] == 2]
t3 = [r for r in promos if r["tier"] == 3]
tab1, tab2, tab3 = st.tabs([f"🏆 Ready to post ({len(t1)})", f"✂️ Needs a trim ({len(t2)})",
                            f"🗑️ Rejected ({len(t3) + len(rejected)})"])
with tab1:
    if not t1:
        st.info("No clip passed every check.")
    for r in sorted(t1, key=lambda r: r.get("rank") or 0):
        card(r)
with tab2:
    if not t2:
        st.info("No clip in this tier.")
    for r in t2:
        st.warning(r["tier_reason"])
        card(r)
with tab3:
    for r in t3:
        st.error(r["tier_reason"])
        card(r)
    if rejected:
        st.subheader("Rejected before judging")
        st.table([{k: x[k] for k in ("clip_id", "stage", "reason")} for x in rejected])
