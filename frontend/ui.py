import streamlit as st
import requests

st.set_page_config(page_title="CoRe - MHT-CET College Finder", page_icon="🎓", layout="centered")
st.title("CoRe")

percentile = st.number_input("Enter your percentile: ", min_value= 0, max_value=100)
category = st.selectbox("Select category", ['DEFOBCS', 'DEFOPENS', 'DEFRSEBCS', 'EWSS', 'GNT1S', 'GNT2S', 'GNT3S', 'GOBCS', 'GOPENS', 'GSCS', 'GSEBCS', 'GSTS', 'GVJS', 'LNT2S', 'LOBCS', 'LOPENS', 'LSCS', 'LSEBCS', 'LSTS', 'LVJS', 'PWDOBCS', 'PWDOPENS', 'PWDROBCS', 'TFWS', 'EWS', 'ORPHAN', 'DEFROBCS', 'PWDRSCS', 'LNT1S', 'LNT3S', 'PWDROBC', 'DEFROBCSS', 'ORPHANS', 'DEFRNT1S', 'DEFRNT3S', 'DEFRSEBC', 'DEFRSCS', 'GNT2H', 'GOBCH', 'GOPENH', 'GSCH', 'GSEBCH', 'GSTH', 'LOBCH', 'LOPENH', 'LSEBCH', 'GSCO', 'GVJO', 'LOPENO', 'PWDOPENH', 'GNT1O', 'GOPENO', 'GSEBCO', 'GVJH', 'LNT2H', 'GOBCO', 'LSCH', 'GSTO', 'LOBCO', 'LSCO', 'GNT3H', 'LSEBCO', 'GNT3O', 'LNT1H', 'LSTH', 'LVJH', 'GNT2O', 'LSTO', 'GNT1H', 'LNT3H', 'PWDOBCH', 'LNT2O', 'LVJO', 'LNT1O', 'LNT3O', 'PWDROBCH', 'DEFSCS', 'PWDSCH', 'DEFSEBCS', 'PWDSEBCH', 'PWDRSTS', 'PWDSCS', 'PWDSEBCS', 'PWDRNT2S', 'MI', 'PWDRSEBCS', 'DEFRVJS', 'DEFRNT2S', 'PWDRNT3S', 'DEFRNT1SS', 'DEFRNT2SS', 'PWDRSEBC', 'DEFRVJSS', 'DEFRNT3SS', 'PWDRSCH', 'PWDRSTH', 'DEFRSTS', 'PWDRSEBCH', 'DEFRSCSS', 'PWDRVJS', 'PWDRNT2H', 'PWDRNT1S', 'DEFSTS', 'PWDSTS'])
branch = st.selectbox("Select preferred branch: ", ['Artificial Intelligence and Data Science', 'Artificial Intelligence and Machine Learning', 'Civil Engineering', 'Computer Engineering', 'Computer Engineering (Software Engineering)', 'Computer Science and Engineering', 'Computer Science and Engineering (Artificial Intelligence)', 'Computer Science and Engineering (Internet of Things and Cyber Security Including Block Chain', 'Computer Science and Engineering(Artificial Intelligence and Machine Learning)', 'Computer Science and Engineering(Data Science)', 'Electrical Engineering', 'Electronics and Computer Engineering', 'Electronics and Telecommunication Engg', 'Information Technology', 'Instrumentation and Control Engineering', 'Manufacturing Science and Engineering', 'Mechanical Engineering', 'Metallurgy and Material Technology', 'Printing and Packing Technology'])
division = st.selectbox("Select preferred division :", ["Amravati Division", "Aurangabad Division", "Mumbai Division", "Nagpur Division", "Nashik Division", "Pune Division"])

st.divider()

if st.button("Find Colleges"):
    with st.spinner("Fetching colleges"):
        try:
            response = requests.get("https://core-5y5r.onrender.com/recommender", params={
                "percentile": percentile,
                "category": category,
                "branch": branch,
                "division": division
            })
            data = response.json()
        except Exception as e:
            st.error("Server is waking up, Please try again in few minutes.")
            st.stop()


    if data['count'] == 0:
        st.warning("No colleges found with given data.")
    else:
        st.success(f"Found {data['count']} eligible colleges.")
        for i, college in enumerate(data["eligible_colleges"], start=1):
            with st.expander(f"{i}. {college['college']}"):
                st.markdown(f"**Branch:** {college['branch']}")
                st.markdown(f"**Min Cutoff:** `{college['min_cutoff']:.2f}`")
                st.markdown(f"**Max Cutoff:** `{college['max_cutoff']:.2f}`")
 
                cutoff_range = college['max_cutoff'] - college['min_cutoff']
                normalized = min(college['max_cutoff'] / 100.0, 1.0)
                st.progress(normalized, text=f"Cutoff up to {college['max_cutoff']:.2f}")

if st.button("All colleges:"):
    try:
        response = requests.get("https://core-5y5r.onrender.com/colleges", params={
            "division": division
        })
        data = response.json()
    except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

    
    if data['count'] == 0:
        st.warning("No colleges found with given data.")
    else:
        st.success(f"Found {data['count']} eligible colleges.")
        for i, college in enumerate(data["Total colleges"], start=1):
            st.markdown(f"**College Code** {college['college_code']} **College Name** {college['college_name']}") 
            

