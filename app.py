import streamlit as st
import asyncio
import os
from loc_counter import GitHubLOCCounter
from cost_calculator import CostCalculator
from report_generator import ReportGenerator
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Streamlit app
st.title("Project Cost Estimator")
st.markdown("Estimate the cost of your software project based on LOC and COCOMO model.")

# GitHub Inputs
st.header("GitHub Repository Details")
repo_url = st.text_input("GitHub Repository URL", "https://github.com/Ayushpani/eMenu1")
token = st.text_input("GitHub Personal Access Token", type="password")
include_tests = st.checkbox("Include Test Files", value=True)
max_file_size_mb = st.number_input("Max File Size (MB)", min_value=0.1, value=1.0, step=0.1)
exclude_extensions = st.text_input("Exclude Extensions (comma-separated)", "css,jpg,png,pdf,db,sql")

# Cost Inputs
st.header("Cost Estimation Parameters")
avg_salary = st.number_input("Average Monthly Developer Salary (Rs.)", min_value=0.0, value=50000.0, step=1000.0)
num_members = st.number_input("Number of Team Members", min_value=1, value=4, step=1)
additional_hw_cost = st.number_input("Additional Hardware Cost (Rs.)", min_value=0.0, value=0.0, step=1000.0)

# Calculate Button
if st.button("Calculate Cost"):
    try:
        # Validate inputs
        if not repo_url or not token:
            st.error("Repository URL and token are required")
            raise ValueError("Repository URL and token are required")
        if max_file_size_mb <= 0:
            st.error("Max file size must be positive")
            raise ValueError("Max file size must be positive")
        if avg_salary < 0 or num_members < 1 or additional_hw_cost < 0:
            st.error("Invalid cost parameters")
            raise ValueError("Invalid cost parameters")

        # Fetch LOC
        with st.spinner("Fetching LOC from GitHub..."):
            exclude_ext_list = [ext.strip() for ext in exclude_extensions.split(',') if ext.strip()]
            counter = GitHubLOCCounter(
                repo_url=repo_url,
                token=token,
                include_tests=include_tests,
                max_file_size_mb=max_file_size_mb,
                exclude_extensions=exclude_ext_list
            )
            loc_counts = asyncio.run(counter.run())
            loc = loc_counts.get("total", 0)
            st.success(f"Total LOC: {loc}")

        # Calculate Costs
        with st.spinner("Calculating costs..."):
            calculator = CostCalculator(
                loc=loc,
                avg_salary=avg_salary,
                num_members=num_members,
                additional_hw_cost=additional_hw_cost
            )
            cost_data = calculator.calculate_costs()
            cost_data["eaf"] = 1.0
            st.success("Cost estimation completed")

        # Display Results
        st.header("Results")
        st.write(f"**LOC**: {cost_data['loc']}")
        st.write(f"**KLOC**: {cost_data['kloc']}")
        st.write(f"**Effort (E)**: {cost_data['effort']} Person-Months")
        st.write(f"**Time (T)**: {cost_data['time']} Months")
        st.write(f"**People (P)**: {cost_data['people']} Persons")
        st.write(f"**Developer Cost**: Rs. {cost_data['developer_cost']}")
        st.write(f"**Final System Cost**: Rs. {cost_data['final_system_cost']}")
        st.write(f"**Paid Software Cost**: Rs. {cost_data['paid_sw_cost']}")
        st.write(f"**Miscellaneous Cost**: Rs. {cost_data['misc_cost']}")
        st.write(f"**Total Cost**: Rs. {cost_data['total_cost']}")

        # Generate Report
        with st.spinner("Generating report..."):
            generator = ReportGenerator(cost_data)
            pdf_file = generator.generate_pdf()
            text_file = generator.generate_text()

            # Provide Download Links
            st.header("Download Report")
            with open(pdf_file, "rb") as f:
                st.download_button("Download PDF Report", f, file_name="project_cost_report.pdf")
            with open(text_file, "rb") as f:
                st.download_button("Download Text Report", f, file_name="project_cost_report.txt")

        # Display LOC Breakdown
        st.header("LOC Breakdown by File Extension")
        for ext, count in loc_counts.items():
            if ext != "total":
                percentage = (count / loc * 100) if loc > 0 else 0
                st.write(f".{ext}: {count} lines ({percentage:.1f}%)")

    except Exception as e:
        logger.error(f"Error in calculation: {e}")
        st.error(f"Error: {e}. Check app.log for details.")

# Display Log File
if os.path.exists('loc_counter.log'):
    with open('loc_counter.log', 'r') as f:
        st.text_area("LOC Counter Log", f.read(), height=200)