import streamlit as st
import pandas as pd
import re
from pathlib import Path
from datetime import datetime
import json

from extractor import extract_text_from_image, classify_and_extract

st.set_page_config(page_title="Transport Log Extractor", layout="wide")

st.title("Transport Log Extractor")
st.caption("Upload document images — the app will classify and extract data for Freightways and Shuffle (Rolling Cargo).")

# ── Session state ──────────────────────────────────────────────────────────────
if "freightways" not in st.session_state:
    st.session_state.freightways = []
if "shuffle" not in st.session_state:
    st.session_state.shuffle = []
if "unknown" not in st.session_state:
    st.session_state.unknown = []

# ── Upload ─────────────────────────────────────────────────────────────────────
uploaded_files = st.file_uploader(
    "Upload document images",
    type=["jpg", "jpeg", "png", "webp", "bmp"],
    accept_multiple_files=True,
)

if uploaded_files:
    if st.button("Process images", type="primary"):
        progress = st.progress(0, text="Starting...")
        results = {"freightways": [], "shuffle": [], "unknown": []}

        for i, file in enumerate(uploaded_files):
            progress.progress((i) / len(uploaded_files), text=f"Processing {file.name}...")
            image_bytes = file.read()

            try:
                raw_text = extract_text_from_image(image_bytes)
                company, record = classify_and_extract(raw_text, file.name)
                results[company].append(record)
            except Exception as e:
                results["unknown"].append({
                    "filename": file.name,
                    "error": str(e),
                })

        st.session_state.freightways.extend(results["freightways"])
        st.session_state.shuffle.extend(results["shuffle"])
        st.session_state.unknown.extend(results["unknown"])
        progress.progress(1.0, text="Done!")
        st.success(
            f"Processed {len(uploaded_files)} image(s): "
            f"{len(results['freightways'])} Freightways, "
            f"{len(results['shuffle'])} Shuffle, "
            f"{len(results['unknown'])} unrecognised."
        )

# ── Results tabs ───────────────────────────────────────────────────────────────
if st.session_state.freightways or st.session_state.shuffle or st.session_state.unknown:
    st.divider()
    tab1, tab2, tab3 = st.tabs([
        f"Freightways ({len(st.session_state.freightways)})",
        f"Shuffle / Rolling Cargo ({len(st.session_state.shuffle)})",
        f"Unrecognised ({len(st.session_state.unknown)})",
    ])

    with tab1:
        if st.session_state.freightways:
            df_f = pd.DataFrame(st.session_state.freightways)
            st.dataframe(df_f, use_container_width=True)
        else:
            st.info("No Freightways documents yet.")

    with tab2:
        if st.session_state.shuffle:
            df_s = pd.DataFrame(st.session_state.shuffle)
            st.dataframe(df_s, use_container_width=True)
        else:
            st.info("No Shuffle / Rolling Cargo documents yet.")

    with tab3:
        if st.session_state.unknown:
            df_u = pd.DataFrame(st.session_state.unknown)
            st.dataframe(df_u, use_container_width=True)
        else:
            st.success("All documents were recognised.")

    # ── Export ─────────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Export")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.session_state.freightways:
            df_f = pd.DataFrame(st.session_state.freightways)
            st.download_button(
                "Download Freightways CSV",
                data=df_f.to_csv(index=False),
                file_name=f"freightways_{datetime.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )

    with col2:
        if st.session_state.shuffle:
            df_s = pd.DataFrame(st.session_state.shuffle)
            st.download_button(
                "Download Shuffle CSV",
                data=df_s.to_csv(index=False),
                file_name=f"shuffle_{datetime.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )

    with col3:
        if st.session_state.freightways and st.session_state.shuffle:
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                pd.DataFrame(st.session_state.freightways).to_excel(
                    writer, sheet_name="Freightways", index=False
                )
                pd.DataFrame(st.session_state.shuffle).to_excel(
                    writer, sheet_name="Shuffle", index=False
                )
            st.download_button(
                "Download combined Excel",
                data=buffer.getvalue(),
                file_name=f"transport_logs_{datetime.today().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    # ── Clear ──────────────────────────────────────────────────────────────────
    if st.button("Clear all results"):
        st.session_state.freightways = []
        st.session_state.shuffle = []
        st.session_state.unknown = []
        st.rerun()
