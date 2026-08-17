import streamlit as st
import requests
from category_labels import decode_category
import pandas as pd
import altair as alt

API_URL_RECOMMENDER = "https://core-5y5r.onrender.com/recommender"
API_URL_TRENDS      = "https://core-5y5r.onrender.com/trends"

CATEGORY_CODES = ['All','DEFOBCS', 'DEFOPENS', 'DEFRSEBCS', 'EWSS', 'GNT1S', 'GNT2S', 'GNT3S', 'GOBCS', 'GOPENS', 'GSCS', 'GSEBCS', 'GSTS', 'GVJS', 'LNT2S', 'LOBCS', 'LOPENS', 'LSCS', 'LSEBCS', 'LSTS', 'LVJS', 'PWDOBCS', 'PWDOPENS', 'PWDROBCS', 'TFWS', 'EWS', 'ORPHAN', 'DEFROBCS', 'PWDRSCS', 'LNT1S', 'LNT3S', 'PWDROBC', 'DEFROBCSS', 'ORPHANS', 'DEFRNT1S', 'DEFRNT3S', 'DEFRSEBC', 'DEFRSCS', 'GNT2H', 'GOBCH', 'GOPENH', 'GSCH', 'GSEBCH', 'GSTH', 'LOBCH', 'LOPENH', 'LSEBCH', 'GSCO', 'GVJO', 'LOPENO', 'PWDOPENH', 'GNT1O', 'GOPENO', 'GSEBCO', 'GVJH', 'LNT2H', 'GOBCO', 'LSCH', 'GSTO', 'LOBCO', 'LSCO', 'GNT3H', 'LSEBCO', 'GNT3O', 'LNT1H', 'LSTH', 'LVJH', 'GNT2O', 'LSTO', 'GNT1H', 'LNT3H', 'PWDOBCH', 'LNT2O', 'LVJO', 'LNT1O', 'LNT3O', 'PWDROBCH', 'DEFSCS', 'PWDSCH', 'DEFSEBCS', 'PWDSEBCH', 'PWDRSTS', 'PWDSCS', 'PWDSEBCS', 'PWDRNT2S', 'MI', 'PWDRSEBCS', 'DEFRVJS', 'DEFRNT2S', 'PWDRNT3S', 'DEFRNT1SS', 'DEFRNT2SS', 'PWDRSEBC', 'DEFRVJSS', 'DEFRNT3SS', 'PWDRSCH', 'PWDRSTH', 'DEFRSTS', 'PWDRSEBCH', 'DEFRSCSS', 'PWDRVJS', 'PWDRNT2H', 'PWDRNT1S', 'DEFSTS', 'PWDSTS']

BRANCHES = ['All','Artificial Intelligence and Data Science', 'Artificial Intelligence and Machine Learning', 'Civil Engineering', 'Computer Engineering', 'Computer Engineering (Software Engineering)', 'Computer Science and Engineering', 'Computer Science and Engineering (Artificial Intelligence)', 'Computer Science and Engineering (Internet of Things and Cyber Security Including Block Chain', 'Computer Science and Engineering(Artificial Intelligence and Machine Learning)', 'Computer Science and Engineering(Data Science)', 'Electrical Engineering', 'Electronics and Computer Engineering', 'Electronics and Telecommunication Engg', 'Information Technology', 'Instrumentation and Control Engineering', 'Manufacturing Science and Engineering', 'Mechanical Engineering', 'Metallurgy and Material Technology', 'Printing and Packing Technology']

DIVISIONS = ["All", "Amravati Division", "Aurangabad Division", "Mumbai Division", "Nagpur Division", "Nashik Division", "Pune Division"]

PAGE_SIZE = 10  # must satisfy backend's ge=5, le=30

st.set_page_config(page_title="CoRe - MHT-CET College Finder", page_icon="🐦‍🔥", layout="centered")

st.markdown(
    """
    <style>
    .block-container { padding-top: 2.5rem; max-width: 780px; }
    .core-subtitle { color: #6b7280; font-size: 0.95rem; margin-top: -0.6rem; margin-bottom: 1.5rem; }
    .college-name { font-size: 1.05rem; font-weight: 600; margin-bottom: 0.1rem; }
    .college-branch { color: #6b7280; font-size: 0.85rem; margin-bottom: 0.6rem; }
    .cutoff-pill {
        display: inline-block; padding: 2px 10px; border-radius: 999px;
        background: #f0f2f6; font-size: 0.8rem; margin-right: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("CoRe")
st.markdown('<p class="core-subtitle">Find engineering colleges you\'re eligible for, based on your MHT-CET percentile.</p>', unsafe_allow_html=True)


def fetch_page(filters: dict, page: int):
    """Hits /recommender with the given filters + page, stores result + filters + page in session_state."""
    params = {**filters, "page": page, "page_size": PAGE_SIZE}
    response = requests.get(API_URL_RECOMMENDER, params=params, timeout=15)
    data = response.json()
    if response.status_code != 200:
        st.error(f"Request failed: {data.get('detail', 'Unknown error')}")
        return
    st.session_state["results"] = data
    st.session_state["current_page"] = page
    st.session_state["active_filters"] = filters


with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        percentile = st.number_input("Your percentile", min_value=0.0, max_value=100.0, step=1.0, format="%.2f")
        branch = st.selectbox("Preferred branch", BRANCHES)
    with col2:
        category = st.selectbox("Your category", CATEGORY_CODES, format_func=decode_category)
        division = st.selectbox("Preferred division", DIVISIONS)

    search_clicked = st.button("Find Colleges", use_container_width=True, type="primary")

st.write("")

if search_clicked:
    with st.spinner("Searching colleges that match your profile..."):
        filters = {
            "percentile": percentile,
            "category": category,
            "branch": branch,
            "division": division,
        }
        try:
            fetch_page(filters, page=1)  # new search always starts at page 1
        except Exception as e:
            st.error(f"Couldn't reach the server: {e}")
            st.stop()

if "results" in st.session_state:
    data = st.session_state["results"]
    total = data["count"]

    if total == 0:
        st.warning("No colleges matched. Try lowering your percentile or widening branch/division to 'All'.")
    else:
        st.success(f"Found {total} eligible college{'s' if total != 1 else ''} for your profile.")
        st.write("")
        for college in data["eligible_colleges"]:
            with st.container(border=True):
                st.markdown(f'<div class="college-name">{college["college"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="college-branch">{college["branch"]}</div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                c1.metric("Min Cutoff", f"{college['min_cutoff']:.2f}")
                c2.metric("Max Cutoff", f"{college['max_cutoff']:.2f}")
                normalized = min(college["max_cutoff"] / 100.0, 1.0)
                st.progress(normalized)
                if st.button("View cutoff trend", key=college["branch_code"]):
                    trend_response = requests.get(
                        API_URL_TRENDS,
                        params={"branch_code": college["branch_code"], "category": category},
                    )
                    trend_data = trend_response.json()
                    if trend_response.status_code != 200:
                        st.error(f"Couldn't load trend: {trend_data.get('detail', 'Unknown error')}")
                    elif trend_data["count"] == 0:
                        st.info("Not enough historical data for a trend.")
                    else:
                        df = pd.DataFrame(trend_data["trends"])
                        y_min = df["percentile"].min() - 1
                        y_max = df["percentile"].max() + 1

                        chart = alt.Chart(df).mark_line(point=True).encode(
                            x="round:O",
                            y=alt.Y("percentile:Q", scale=alt.Scale(domain=[y_min, y_max])),
                            color="year:N",
                        )
                        st.altair_chart(chart, use_container_width=True)

        # --- Pagination controls ---
        current_page = st.session_state["current_page"]
        total_pages = -(-total // PAGE_SIZE)  # ceil division, no extra import needed

        st.write("")
        nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
        with nav_col1:
            if current_page > 1:
                if st.button("← Previous", use_container_width=True):
                    fetch_page(st.session_state["active_filters"], page=current_page - 1)
                    st.rerun()
        with nav_col2:
            st.markdown(
                f"<div style='text-align:center; color:#6b7280;'>Page {current_page} of {total_pages}</div>",
                unsafe_allow_html=True,
            )
        with nav_col3:
            if current_page < total_pages:
                if st.button("Next →", use_container_width=True):
                    fetch_page(st.session_state["active_filters"], page=current_page + 1)
                    st.rerun()