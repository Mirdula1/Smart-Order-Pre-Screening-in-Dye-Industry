import streamlit as st
import requests
from datetime import datetime

API_URL = "http://localhost:8000"

st.title("Recipe Pre-screening System")

#option = st.radio("Choose an action:", ["Select a specific order to view analysis", "Review all existing order analyses","Insert a new order for analysis"])

option = st.radio("Choose an option:", options=["View Selected Batch Order Analysis", "Analyze All the existing Orders", "Insert New Batch Order"])

if option == "View Selected Batch Order Analysis":
    
    st.subheader("Select an Order ID to view its Analysis:")

    with st.spinner("Fetching reports..."):
        response = requests.get(f"{API_URL}/get_orders")
        if response.status_code == 200:
            orders = response.json()
            if orders:
                selected_id = st.selectbox("Choose Order ID", [str(o["id"]) for o in orders])
                if st.button("Get order analysis"):
                    if selected_id:
                        result = requests.get(f"{API_URL}/process_order/{selected_id}").json()
                        st.subheader(f"Analysis for Order : {selected_id}")
                        st.text_area("Order Analysis Report", result.get("report_analysis", "Not found"), height=600, key=f"analysis_{selected_id}")
            else:
                st.warning("No orders available.")
        else:
            st.error("Failed to fetch orders.")

elif option == "Analyze All the existing Orders":
    st.subheader("Analyze Recipe Standards for All Orders")
    if st.button("Analyze All Orders"):
        with st.spinner("Analyzing all orders..."):
            response = requests.get(f"{API_URL}/get_orders")
        if response.status_code == 200:
            orders = response.json()
            if orders:
                for o in orders:
                    oid = o["id"]
                    result = requests.get(f"{API_URL}/process_order/{oid}").json()
                    st.subheader(f"Order ID: {oid}")
                    st.text_area("Order Analysis Report", result.get("report_analysis", "Not found"), height=250, key=f"all_{oid}")
            else:
                st.info("No records found.")

elif option == "Insert New Batch Order":
    st.subheader("Enter Order Details")
    order_data = {
        "std_triangle_code_1": st.text_input("Standard Triangle Code 1"),
        "std_triangle_code_2": st.text_input("Standard Triangle Code 2"),
        "recipe_triangle_code_1": st.text_input("Recipe Triangle Code 1"),
        "recipe_triangle_code_2": st.text_input("Recipe Triangle Code 2"),
        "recipe_type_code": st.text_input("Recipe Type Code"),
        "fastness_type": st.text_input("Fastness Type"),
        "article_dye_check_result": st.text_input("Article Dye Check Result"),
        "check_dye_triangle": st.text_input("Check Dye Triangle"),
        "no_of_stages": st.number_input("No. of Stages", min_value=1),
        "max_recipe_age_in_days": st.number_input("Max Recipe Age in Days", min_value=1),
        "last_update_date": st.date_input("Last Update Date").strftime("%Y-%m-%d"),
        "standard_saved_date": st.date_input("Standard Saved Date", value=datetime.today()).strftime("%Y-%m-%d"),
        "min_no_of_lots": st.number_input("Min No. of Lots", min_value=1),
        "max_delta_e": st.number_input("Max Delta E"),
        "max_delta_l": st.number_input("Max Delta L"),
        "max_delta_c": st.number_input("Max Delta C"),
        "max_delta_h": st.number_input("Max Delta H"),
        "no_of_matching_lots": st.number_input("No. of Matching Lots", min_value=0),
        "de_of_average": st.number_input("Delta E of Avg"),
        "dl_of_average": st.number_input("Delta L of Avg"),
        "dc_of_average": st.number_input("Delta C of Avg"),
        "dh_of_average": st.number_input("Delta H of Avg"),
    }

    if st.button("Submit"):
        with st.spinner("Submitting new order and analyzing order batch..."):
            res = requests.post(f"{API_URL}/add_order", json=order_data)
        if res.status_code == 200:
            result = res.json()
            st.success("Order successfully added!")
            st.markdown(f"Order ID {result['order_id']} - {result['message']}")
            st.text_area("Order Analysis Report", result["report_analysis"], height=300, key="new_analysis")
        else:
            st.error(f"Failed to submit: {res.text}")
