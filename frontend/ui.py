import streamlit as st
import requests

st.title("MHT-CET college recommender")

percentile = st.slider("Enter your percentile: ", 0, 100)
category = st.selectbox("Select category", ['DEFOBCS', 'DEFOPENS', 'DEFRSEBCS', 'EWSS', 'GNT1S', 'GNT2S', 'GNT3S', 'GOBCS', 'GOPENS', 'GSCS', 'GSEBCS', 'GSTS', 'GVJS', 'LNT2S', 'LOBCS', 'LOPENS', 'LSCS', 'LSEBCS', 'LSTS', 'LVJS', 'PWDOBCS', 'PWDOPENS', 'PWDROBCS', 'TFWS', 'EWS', 'ORPHAN', 'DEFROBCS', 'PWDRSCS', 'LNT1S', 'LNT3S', 'PWDROBC', 'DEFROBCSS', 'ORPHANS', 'DEFRNT1S', 'DEFRNT3S', 'DEFRSEBC', 'DEFRSCS', 'GNT2H', 'GOBCH', 'GOPENH', 'GSCH', 'GSEBCH', 'GSTH', 'LOBCH', 'LOPENH', 'LSEBCH', 'GSCO', 'GVJO', 'LOPENO', 'PWDOPENH', 'GNT1O', 'GOPENO', 'GSEBCO', 'GVJH', 'LNT2H', 'GOBCO', 'LSCH', 'GSTO', 'LOBCO', 'LSCO', 'GNT3H', 'LSEBCO', 'GNT3O', 'LNT1H', 'LSTH', 'LVJH', 'GNT2O', 'LSTO', 'GNT1H', 'LNT3H', 'PWDOBCH', 'LNT2O', 'LVJO', 'LNT1O', 'LNT3O', 'PWDROBCH', 'DEFSCS', 'PWDSCH', 'DEFSEBCS', 'PWDSEBCH', 'PWDRSTS', 'PWDSCS', 'PWDSEBCS', 'PWDRNT2S', 'MI', 'PWDRSEBCS', 'DEFRVJS', 'DEFRNT2S', 'PWDRNT3S', 'DEFRNT1SS', 'DEFRNT2SS', 'PWDRSEBC', 'DEFRVJSS', 'DEFRNT3SS', 'PWDRSCH', 'PWDRSTH', 'DEFRSTS', 'PWDRSEBCH', 'DEFRSCSS', 'PWDRVJS', 'PWDRNT2H', 'PWDRNT1S', 'DEFSTS', 'PWDSTS'])
branch = st.selectbox("Enter preferred branch: ", ['Artificial Intelligence and Data Science', 'Artificial Intelligence and Machine Learning', 'Civil Engineering', 'Computer Engineering', 'Computer Engineering (Software Engineering)', 'Computer Science and Engineering', 'Computer Science and Engineering (Artificial Intelligence)', 'Computer Science and Engineering (Internet of Things and Cyber Security Including Block Chain', 'Computer Science and Engineering(Artificial Intelligence and Machine Learning)', 'Computer Science and Engineering(Data Science)', 'Electrical Engineering', 'Electronics and Computer Engineering', 'Electronics and Telecommunication Engg', 'Information Technology', 'Instrumentation and Control Engineering', 'Manufacturing Science and Engineering', 'Mechanical Engineering', 'Metallurgy and Material Technology', 'Printing and Packing Technology'])

if st.button("Find Colleges"):
    try:
        response = requests.get("https://core-5y5r.onrender.com/recommender", params={
            "percentile": percentile,
            "category": category,
            "branch": branch
        })
    except Exception as e:
        st.error("Server is waking up, Please try again in few minutes.")
        st.stop()

    data = response.json()

    if data['count'] == 0:
        st.warning("No colleges found with given data.")
    else:
        st.success(f"Found {data['count']} eligible colleges.")
        for college in data["Eligible colleges"]:
            st.write(f"**{college['college']} - {college['branch']} ({college['cutoff_percentile']})")


