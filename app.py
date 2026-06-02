import json
import streamlit as st
from sample_reviews import samples

st.set_page_config(page_title="VaxScope", layout="wide", page_icon="🧬")

def clean_prediction(prediction):
    prediction = dict(prediction)
    if not prediction.get("population"):
        prediction["population"] = ["all_age_groups"]
    if "efficacy_effectiveness" not in prediction.get("topic", []):
        prediction["outcome"] = []
    return prediction

if "selected_review" not in st.session_state:
    st.session_state.selected_review = None

st.sidebar.markdown("""
<div style='padding:8px 0 4px 0'>
    <div style='font-size:1.4rem;font-weight:800;color:white;letter-spacing:-0.02em'>🔍SysvacAI</div>
    <div style='font-size:0.65rem;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:0.12em;margin-top:2px'>Evidence Intelligence</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigation", ["Review Explorer", "About"])

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

.stApp { background: #f4f6fa; font-family: 'Inter', sans-serif; }

section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] > div:first-child {
    background-color: #0b3d91 !important;
}
section[data-testid="stSidebar"] * { color: white !important; }
section[data-testid="stSidebar"] .stRadio label { color: rgba(255,255,255,0.85) !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.2) !important; }

.block-container { padding: 2rem 2.5rem; max-width: 1300px; }

/* ── Review card (explorer) ── */
.review-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 22px 26px;
    margin-bottom: 14px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.05);
    transition: box-shadow 0.2s;
}
.review-card:hover { box-shadow: 0 4px 18px rgba(0,0,0,0.1); }

/* ── Badges ── */
.badge {
    display: inline-block;
    background: #e8f1ff;
    color: #0b3d91;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-right: 6px;
    margin-bottom: 6px;
    letter-spacing: 0.02em;
}

/* ── Stat boxes (study overview) ── */
.stat-box {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 18px 20px;
    text-align: center;
}
.stat-box-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #0b3d91;
    line-height: 1.2;
}
.stat-box-label {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #9ca3af;
    margin-top: 4px;
}

/* ── Section header ── */
.section-title {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #6b7280;
    margin: 0 0 10px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #e5e7eb;
}

/* ── Characteristic row ── */
.char-row {
    display: flex;
    flex-direction: column;
    gap: 14px;
}
.char-item-label {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #9ca3af;
    margin-bottom: 3px;
}
.char-item-value {
    font-size: 0.88rem;
    color: #1f2937;
    font-weight: 500;
}

/* ── AMSTAR panel ── */
.amstar-panel {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 20px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.05);
    position: sticky;
    top: 1rem;
}
.amstar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid #f0f0f0;
}
.amstar-title {
    font-size: 0.85rem;
    font-weight: 700;
    color: #111827;
    letter-spacing: -0.01em;
}
.rating-pill {
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.04em;
}
.rating-high     { background: #d1fae5; color: #065f46; }
.rating-moderate { background: #fef3c7; color: #92400e; }
.rating-low      { background: #fee2e2; color: #991b1b; }
.rating-critically { background: #fce7f3; color: #9d174d; }

.amstar-met {
    font-size: 0.78rem;
    color: #6b7280;
    margin-bottom: 16px;
}
.amstar-met strong { color: #111827; }

/* ── AMSTAR item row ── */
.amstar-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 9px 0;
    border-bottom: 1px solid #f3f4f6;
    font-size: 0.8rem;
}
.amstar-item:last-child { border-bottom: none; }
.amstar-icon { flex-shrink: 0; margin-top: 1px; }
.amstar-item-text { flex: 1; }
.amstar-item-name { color: #374151; font-weight: 500; line-height: 1.4; }
.amstar-item-val  { font-size: 0.7rem; color: #9ca3af; margin-top: 1px; }
.icon-yes  { color: #10b981; font-size: 1rem; }
.icon-part { color: #f59e0b; font-size: 1rem; }
.icon-no   { color: #ef4444; font-size: 1rem; }
.icon-na   { color: #d1d5db; font-size: 1rem; }

/* ── Abstract box ── */
.abstract-box {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 20px 24px;
    font-size: 0.86rem;
    color: #374151;
    line-height: 1.8;
}

/* ── Back button ── */
.stButton > button {
    background: white !important;
    border: 1px solid #d1d5db !important;
    color: #374151 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 6px 16px !important;
}
.stButton > button:hover {
    border-color: #0b3d91 !important;
    color: #0b3d91 !important;
}

#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────

def rating_class(r):
    r = str(r).lower()
    if "critically" in r: return "rating-critically"
    if "low" in r: return "rating-low"
    if "moderate" in r: return "rating-moderate"
    return "rating-high"

def amstar_icon(value):
    v = str(value).strip()
    if v == "Yes":        return "<span class='icon-yes'>✔</span>", v
    if v == "Partial Yes": return "<span class='icon-part'>◑</span>", v
    if v in ("No","Unclear"): return "<span class='icon-no'>✖</span>", v
    return "<span class='icon-na'>—</span>", v

FLAW_EXPLANATIONS = {
    "Item 1 - PICO Components Present": "PICO elements not clearly described.",
    "Item 2 - Protocol / PROSPERO": "No PROSPERO registration or CRD number found.",
    "Item 3 - Study Design Explanation": "Rationale for study designs not explained.",
    "Item 4 - Comprehensive Literature Search": "Literature search not comprehensive.",
    "Item 5 - Study Selection in Duplicate": "Study selection not performed in duplicate.",
    "Item 6 - Duplicate Data Extraction": "Data extraction not performed in duplicate.",
    "Item 7 - Excluded Studies List": "No list of excluded studies with reasons.",
    "Item 8 - Included Studies Description": "Included studies not described in adequate detail.",
    "Item 9 - RoB Assessment Technique": "RoB tools not properly applied or reported.",
    "Item 10 - Funding Sources Reported": "Funding sources for included studies not reported.",
    "Item 11 - Statistical Combination Methods": "Meta-analysis methods not appropriate or justified.",
    "Item 12 - RoB Impact on Findings": "RoB impact on findings not considered.",
    "Item 13 - RoB in Discussion": "RoB not addressed when interpreting results.",
    "Item 14 - Heterogeneity Explained": "Heterogeneity not explained or discussed.",
    "Item 15 - Publication Bias Investigation": "Publication bias not assessed or discussed.",
    "Item 16 - Conflict of Interest Disclosure": "Conflicts of interest not disclosed.",
}

ITEM_SHORT = {
    "Item 1 - PICO Components Present":         "Item1. Research questions include PICO?",
    "Item 2 - Protocol / PROSPERO":             "Item2. Registered in PROSPERO?",
    "Item 3 - Study Design Explanation":        "Item3. Study design selection explained?",
    "Item 4 - Comprehensive Literature Search": "Item4. Comprehensive search conducted?",
    "Item 5 - Study Selection in Duplicate":    "Item5. Selection in duplicate?",
    "Item 6 - Duplicate Data Extraction":       "Item6. Data extraction in duplicate?",
    "Item 7 - Excluded Studies List":           "Item7. Excluded studies listed with reasons?",
    "Item 8 - Included Studies Description":    "Item8. Included studies described adequately?",
    "Item 9 - RoB Assessment Technique":        "Item9. Satisfactory RoB technique used?",
    "Item 10 - Funding Sources Reported":       "Item10. Funding sources reported?",
    "Item 11 - Statistical Combination Methods":"Item11. Appropriate statistical methods?",
    "Item 12 - RoB Impact on Findings":         "Item12. RoB impact on findings considered?",
    "Item 13 - RoB in Discussion":              "Item13. RoB considered in discussion?",
    "Item 14 - Heterogeneity Explained":        "Item14. Heterogeneity explained?",
    "Item 15 - Publication Bias Investigation": "Item15. Publication bias investigated?",
    "Item 16 - Conflict of Interest Disclosure":"Item16. Conflicts of interest disclosed?",
}


# ── Explorer ───────────────────────────────────────────

def show_explorer():
    st.markdown("<h2 style='color:#c0522a;font-weight:400;letter-spacing:-0.01em;margin-bottom:4px'>SysvacAI Evidence Intelligence</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#6b7280;font-size:0.88rem'>AI-assisted structured extraction from immunization systematic reviews for NITAG evidence workflows.</p>", unsafe_allow_html=True)
    st.write("")

    st.markdown(f"""
    <div style='display:flex;gap:28px;margin-bottom:1.5rem;flex-wrap:wrap;border-bottom:1px solid #e5e7eb;padding-bottom:1.2rem'>
        <div>
            <span style='font-size:1.15rem;font-weight:700;color:#0b3d91'>{len(samples)}</span>
            <span style='font-size:0.65rem;color:#9ca3af;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin-left:6px'>Reviews</span>
        </div>
        <div>
            <span style='font-size:1.15rem;font-weight:700;color:#0b3d91'>Immunization</span>
            <span style='font-size:0.65rem;color:#9ca3af;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin-left:6px'>Domain</span>
        </div>
        <div>
            <span style='font-size:1.05rem;font-weight:700;color:#0b3d91'>Single-Review Analysis</span>
            <span style='font-size:0.65rem;color:#9ca3af;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin-left:6px'>Mode</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    for i, sample in enumerate(samples):
        prediction = clean_prediction(sample["prediction"])
        amstar = sample.get("amstar2", {})
        rating = amstar.get("overall_rating", "—")
        rc = rating_class(rating)

        badges = f"<span class='badge'>{prediction.get('disease','unknown')}</span>"
        for t in prediction.get("topic", []):
            badges += f"<span class='badge'>{t.replace('_',' ')}</span>"
        for t in prediction.get("review_type", []):
            badges += f"<span class='badge'>{t.replace('_',' ')}</span>"

        with st.container():
            st.markdown(f"""
            <div class='review-card' style='padding-bottom:8px'>
                <div style='display:flex;align-items:flex-start;justify-content:space-between;gap:12px'>
                    <div style='font-size:1rem;font-weight:700;color:#111827;line-height:1.4;flex:1'>{sample['title']}</div>
                    <span class='rating-pill {rc}' style='flex-shrink:0'>{rating}</span>
                </div>
                <div style='margin:10px 0 8px'>{badges}</div>
                <div style='font-size:0.83rem;color:#6b7280;line-height:1.7;margin-bottom:6px'>{sample['abstract'][:260]}...</div>
            </div>
            <div style='margin-top:-18px;margin-bottom:14px;padding:0 22px 16px 22px;background:white;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 14px 14px;display:flex;justify-content:flex-end'>
            </div>
            """, unsafe_allow_html=True)

            col_spacer, col_btn = st.columns([6, 1])
            with col_btn:
                if st.button("Review →", key=f"open_{i}"):
                    st.session_state.selected_review = i
                    st.rerun()


# ── Detail View ────────────────────────────────────────

def show_review():
    sample = samples[st.session_state.selected_review]
    prediction = clean_prediction(sample["prediction"])
    amstar = sample.get("amstar2", {})
    items = amstar.get("items", {})
    rating = amstar.get("overall_rating", "—")
    rc = rating_class(rating)
    criteria_met = sum(1 for v in items.values() if str(v) in ("Yes", "Partial Yes"))

    if st.button("← Back to Dashboard"):
        st.session_state.selected_review = None
        st.rerun()

    st.write("")

    # Title + badges
    badges = f"<span class='badge'>{prediction.get('disease','unknown')}</span>"
    for t in prediction.get("topic", []):
        badges += f"<span class='badge'>{t.replace('_',' ')}</span>"
    for t in prediction.get("review_type", []):
        badges += f"<span class='badge'>{t.replace('_',' ')}</span>"

    st.markdown(
        f"<div style='font-size:1.45rem;font-weight:800;color:#111827;line-height:1.35;margin-bottom:10px'>{sample['title']}</div>"
        f"<div style='margin-bottom:1.2rem'>{badges}</div>",
        unsafe_allow_html=True
    )

    # ── Publication Details  ──
    pub = sample.get("publication", {})
    if pub:
        authors = pub.get("authors", "")
        year    = pub.get("year", "")
        journal = pub.get("journal", "")
        parts = []
        if authors: parts.append(f"<span style='color:#374151'>👤 {authors}</span>")
        if year:    parts.append(f"<span style='color:#374151'>📅 {year}</span>")
        if journal: parts.append(f"<span style='color:#6b7280;font-style:italic'>📖 {journal}</span>")
        if parts:
            st.markdown(
                f"<div style='display:flex;gap:24px;align-items:center;flex-wrap:wrap;"
                f"font-size:0.84rem;padding:10px 0 14px 0;border-bottom:1px solid #e5e7eb;margin-bottom:4px'>"
                + " · ".join(parts) +
                "</div>",
                unsafe_allow_html=True
            )

    # ── Left (Abstract + Overview) / Right (AMSTAR) ──
    left, right = st.columns([2, 1], gap="large")

    with left:
        st.markdown("<div class='section-title'>Abstract</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='abstract-box'>{sample['abstract']}</div>", unsafe_allow_html=True)
        st.write("")

        # Study Overview — 
        st.markdown("<div class='section-title'>Study Overview</div>", unsafe_allow_html=True)
        s1, s2, s3 = st.columns(3)
        participants = prediction.get('num_participants')
        p_str = f"{participants:,}" if isinstance(participants, int) else "—"
        with s1:
            st.markdown(f"<div class='stat-box'><div class='stat-box-value'>{prediction.get('num_studies','—')}</div><div class='stat-box-label'>Studies</div></div>", unsafe_allow_html=True)
        with s2:
            st.markdown(f"<div class='stat-box'><div class='stat-box-value'>{p_str}</div><div class='stat-box-label'>Participants</div></div>", unsafe_allow_html=True)
        with s3:
            st.markdown(f"<div class='stat-box'><div class='stat-box-value' style='font-size:1.1rem'>{prediction.get('date_of_last_lit','—')}</div><div class='stat-box-label'>Date of Last Literature Search</div></div>", unsafe_allow_html=True)
        st.write("")

        # Study Characteristics
        st.markdown("<div class='section-title'>Study Characteristics</div>", unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        lbl = "font-size:0.68rem;color:#9ca3af;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:3px"
        val = "font-size:0.88rem;color:#1f2937;font-weight:500;margin-bottom:14px"
        pop     = ", ".join(prediction.get("population", [])).replace("_", " ")
        stype   = ", ".join(prediction.get("study_type", [])).replace("_", " ")
        outcome = ", ".join(prediction.get("outcome", [])).replace("_", " ")
        topic   = ", ".join(prediction.get("topic", [])).replace("_", " ")
        with cc1:
            st.markdown(f"<p style='{lbl}'>Population Focus</p><p style='{val}'>{pop or '—'}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='{lbl}'>Study Types</p><p style='{val}'>{stype or '—'}</p>", unsafe_allow_html=True)
        with cc2:
            st.markdown(f"<p style='{lbl}'>Outcomes</p><p style='{val}'>{outcome or '—'}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='{lbl}'>Topics</p><p style='{val}'>{topic or '—'}</p>", unsafe_allow_html=True)

        snippets = sample.get("evidence_snippets", [])
        if snippets:
            st.write("")
            st.markdown("<div class='section-title'>Evidence Snippets</div>", unsafe_allow_html=True)
            for s in snippets:
                st.info(s)

    with right:
        st.markdown(
            f"<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:6px'>"
            f"<span style='font-size:0.85rem;font-weight:700;color:#111827'>AMSTAR 2 Quality</span>"
            f"<span class='badge rating-{rc.replace('rating-','')}' style='border-radius:999px'>{rating}</span></div>"
            f"<p style='font-size:0.78rem;color:#6b7280;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid #e5e7eb'>"
            f"<b style='color:#111827'>{criteria_met}</b> items met</p>",
            unsafe_allow_html=True
        )

        item4_details = amstar.get("item4_details", {})

        for key, value in items.items():
            label = ITEM_SHORT.get(key, key)
            v = str(value).strip()
            if v == "Yes":
                icon, color = "🟢", "#065f46"
            elif v == "Partial Yes":
                icon, color = "🟡", "#92400e"
            elif v in ("No", "Unclear"):
                icon, color = "🔴", "#991b1b"
            else:
                icon, color = "⚪", "#9ca3af"

            st.markdown(
                f"<div style='display:flex;align-items:flex-start;gap:8px;padding:7px 0;border-bottom:1px solid #f3f4f6'>"
                f"<span style='font-size:0.65rem;margin-top:3px'>{icon}</span>"
                f"<div><div style='font-size:0.79rem;color:#374151;font-weight:500;line-height:1.4'>{label}</div>"
                f"<div style='font-size:0.69rem;color:{color};font-weight:600;margin-top:1px'>{v}</div></div></div>",
                unsafe_allow_html=True
            )

            if "Item 4" in key and item4_details:
                with st.expander("Search strategy sub-checks"):
                    for k, sv in item4_details.items():
                        sicon = "🟢" if sv == "Yes" else "🔴"
                        sv_color = "#065f46" if sv == "Yes" else "#991b1b"
                        st.markdown(
                            f"<div style='font-size:0.78rem;color:#374151;padding:4px 0;display:flex;gap:6px;align-items:center'>"
                            f"<span>{sicon}</span><span>{k}</span>"
                            f"<span style='margin-left:auto;font-weight:600;color:{sv_color};font-size:0.7rem'>{sv}</span></div>",
                            unsafe_allow_html=True
                        )

    st.write("")
    combined_output = {"prediction": prediction, "amstar2": sample.get("amstar2")}
    st.download_button(
        "⬇ Download JSON",
        data=json.dumps(combined_output, indent=2),
        file_name="vaxscope_output.json",
        mime="application/json"
    )


def show_about():
    st.markdown("<h3 style='color:#c0522a;font-weight:700;letter-spacing:-0.01em;margin-bottom:4px'>About SYSVAC AI</h3>", unsafe_allow_html=True)
    st.markdown("""SYSVAC AI is an evidence intelligence platform for immunization systematic reviews.<br>
This demonstration presents AI-assisted extraction of review characteristics, evidence snippets, and AMSTAR-2 quality assessments from immunization reviews.
""", unsafe_allow_html=True)

if page == "About":
    show_about()
else:
    if st.session_state.selected_review is None:
        show_explorer()
    else:
        show_review()
