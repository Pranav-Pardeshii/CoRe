import streamlit as st
import requests

st.title("MHT-CET college recommender")

percentile = st.number_input("Enter your percentile: ", min_value=0, max_value=100)
caste = st.selectbox("Select category", ["GOPENS", "GSCS", "GSTS", "GOBCS", "GSEBCS", "LOPENS", "TFWS", "EWS"])
branch = st.selectbox("Enter preferred branch: ", ['Artificial Intelligence and Data Science', 'Artificial Intelligence and Machine Learning', 'Civil Engineering', 'Computer Engineering', 'Computer Engineering (Software Engineering)', 'Computer Science and Engineering', 'Computer Science and Engineering (Artificial Intelligence)', 'Computer Science and Engineering (Internet of Things and Cyber Security Including Block Chain', 'Computer Science and Engineering(Artificial Intelligence and Machine Learning)', 'Computer Science and Engineering(Data Science)', 'Electrical Engineering', 'Electronics and Computer Engineering', 'Electronics and Telecommunication Engg', 'Information Technology', 'Instrumentation and Control Engineering', 'Manufacturing Science and Engineering', 'Mechanical Engineering', 'Metallurgy and Material Technology', 'Printing and Packing Technology'])

if st.button("Find Colleges"):
    response = requests.get("http://localhost:8000/recommender", params={
        "percentile": percentile,
        "caste": caste,
        "branch": branch
    })

    data = response.json()

    if data['count'] == 0:
        st.warning("No colleges found with given data.")
    else:
        st.success(f"Found {data['count']} eligible colleges.")
        for college in data["Eligible colleges"]:
            st.write(f"**{college['college']} - {college['branch']} ({college['cutoff_percentile']})")


