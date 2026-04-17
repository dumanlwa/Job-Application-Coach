import os
import sys

import requests

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")

payload = {
    "job_description": '''About the job
Binance is a leading global blockchain ecosystem behind the world’s largest cryptocurrency exchange by trading volume and registered users. We are trusted by 300+ million people in 100+ countries for our industry-leading security, user fund transparency, trading engine speed, deep liquidity, and an unmatched portfolio of digital-asset products. Binance offerings range from trading and finance to education, research, payments, institutional services, Web3 features, and more. We leverage the power of digital assets and blockchain to build an inclusive financial ecosystem to advance the freedom of money and improve financial access for people around the world.

We are looking for a skilled Data Analyst to join our Financial Products Business team, focusing on derivatives products including Futures trading and Options trading. You will play a key role in building and maintaining data dashboards and intermediate data tables to track product performance and support business decisions.

Responsibilities:

Develop and maintain Datawind / Sensor Dashboards for derivatives products (Futures, Options)
Build and manage intermediate data tables to support dashboard analytics and reporting
Monitor and analyze product performance metrics to provide actionable insights
Collaborate with product teams to conduct ad-hoc product analysis beyond dashboard scope when needed
Ensure data accuracy, consistency, and timely delivery of reports

Requirements:

Proven experience as a Data Analyst, preferably in financial products or derivatives trading
Strong skills in data visualization tools and dashboard development.
Proficient in SQL and data engineering for building intermediate data tables
Familiarity with derivatives products such as Futures and Options.
Analytical mindset with strong problem-solving skills
Ability to work collaboratively in a fast-paced environment
''',
    "resume_text": '''Education
City University of Hong Kong Expected June 2026
Bachelor of Science in Data Science - CGPA: 3.79/4.3 Hong Kong
Relevant Coursework: Machine Learning, Artificial Intelligence, Large Language Models, Data Structures,
Database Systems, Convex Optimization, Multivariable Calculus, Advanced Statistics, Financial Engineering
Experience
Hong Kong Exchanges and Clearing Limited June 2025 – Aug 2025
Data Science Intern Hong Kong
• Engineered features from the TB-scale Order-Trade data using Hetu SQL to analyze market
microstructure, specifically identifying divergence between institutional and retail execution strategies
• Built a semi-supervised classification model to categorize 500+ Exchange Participants, leveraging clustering
algorithms (k-means/DBSCAN) to label aggressive institutional vs. passive retail strategies for regulatory
monitoring
• Designed scalable ETL pipelines for financial data, implementing automated validation and PII masking across
AWS S3/Huawei OBS to ensure data integrity and compliance
Reinsurance Group of America, Incorporated July 2024 – Dec 2024
Analyst Intern Hong Kong
• Developed Python/PyQt6-based tools (Random Sampling Tool, Employee Distribution List Tool) to automate
manual reporting workflows, reducing process time by 70% and minimizing human errors
• Collaborated with the Internal Audit Team to execute financial analysis and reconciliations using Power BI and
MS Excel, validating internal controls to ensure regulatory compliance
Sigtica Limited June 2024 – July 2024
Data Engineer Intern Hong Kong
• Implemented RESTful APIs using Flask and MySQL for an internal file management system, enabling reliable
storage, retrieval, and tracking of documents
• Developed automated Python/SQL data pipelines to streamline task assignment and status tracking between
managers and employees
• Optimized Docker container configurations (CPU pinning, thread allocation), achieving 3x faster processing of
large datasets via improved multi-core parallelization
Projects
Time Series Forecasting § | Python, Pandas, Scikit-learn, TensorFlow/Keras, StatsModels May 2025
• Designed deep learning models (GRU, LSTM, RNN) on the DJIA 30 stock data, with GRU achieving the
best performance: (MAE: $1.49, MAPE: 0.97%)
• Engineered quantitative signals including RSI, Bollinger Bands, and MACD, combined with seasonal
decomposition to isolate trend components from market noise
Sentiment & Geo-Spatial Analysis § | Python, Pandas, Scikit-learn, PyTorch, Torch-geometric Apr 2025
• Developed a GATv2 (Graph Attention Network) to predict business performance metrics using Yelp reviews,
modelling spatial dependencies between entities as a graph structure
• Implemented DNN/CNN models achieving 93.6% accuracy in sentiment classification, utilizing these scores as
alternative data signals for performance prediction
Awards & Activities
Dean’s Honours List: Sem A-B 2022/23, Sem A-B 2023/24, Sem B 2024/25, Sem A 2025/26
Top Scholarship for International Students at City University of Hong Kong: 180,000 HKD annually
HK Tech Tiger Program: Top 5% in the Department of Data Science
Student Mentor in the School of Data Science at City University of Hong Kong
Skills
Programming Languages: C++, Python, R, SQL, HTML/CSS, Java
Frameworks & Technologies: Scikit-learn, Pandas, NumPy, TensorFlow/Keras, OpenCV, PyQt6, Flask
Tools & Platforms: Docker, Git, MySQL, AWS S3, Huawei OBS, Hetu SQL, Power BI, Tableau
''',
 }



def test_health() -> bool:
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=15)
        response.raise_for_status()
        print("HEALTH:", response.status_code, response.json())
        return True
    except requests.exceptions.RequestException as exc:
        print("HEALTH CHECK FAILED")
        print(f"- Base URL: {BASE_URL}")
        print(f"- Error: {exc}")
        print("- Start the API first: .\\.venv\\Scripts\\python.exe app.py")
        return False


def test_full_analysis():
    try:
        response = requests.post(
            f"{BASE_URL}/api/full-analysis",
            json=payload,
            timeout=120,
        )
        print("FULL ANALYSIS STATUS:", response.status_code)
        data = response.json()
        if response.status_code != 200:
            print(data)
            return

        expected_keys = ["run_id", "job_analysis", "resume_match", "updated_cv", "cover_letter", "scoring"]
        missing = [key for key in expected_keys if key not in data]
        if missing:
            print("MISSING KEYS:", missing)
        else:
            print("RESPONSE KEYS OK")

        print("run_id:", data.get("run_id"))
        print("updated_cv length:", len(data.get("updated_cv", "")))
        print("cover_letter length:", len(data.get("cover_letter", "")))
        print("scoring keys:", list((data.get("scoring") or {}).keys()))
    except requests.exceptions.RequestException as exc:
        print("FULL ANALYSIS REQUEST FAILED")
        print(f"- Base URL: {BASE_URL}")
        print(f"- Error: {exc}")


if __name__ == "__main__":
    healthy = test_health()
    if not healthy:
        sys.exit(1)
    test_full_analysis()
