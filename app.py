import streamlit as st
from Pokemon_Stats_Calculator import parse_log

st.title("SDL Pokémon Battle Log Kill Tracker")

log_text = st.text_area(
    "Paste Battle Log Here",
    height=400
)

uploaded_file = st.file_uploader("Or upload a log file", type="txt"
)

if uploaded_file:
    log_text = uploaded_file.read().decode("utf-8")

if st.button("Analyze Log"):
    if log_text.strip():
        kills, deaths = parse_log(log_text)

        st.subheader("Kills")
        st.json(kills)

        st.subheader("Deaths")
        st.json(deaths)
    else:
        st.warning("Please paste a battle log first.")