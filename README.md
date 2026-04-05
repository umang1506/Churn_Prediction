# ChurnShield AI 🚀

**ChurnShield AI** is an advanced, full-stack SaaS platform designed to transform raw customer behavior data into actionable retention strategies using state-of-the-art machine learning. In today’s hyper-competitive e-commerce landscape, retaining a customer is 5x more cost-effective than acquiring a new one. ChurnShield empowers businesses of all sizes—from emerging startups to industry giants like **Flipkart, Amazon, and Zomato**—to protect their revenue by predicting customer churn before it happens.

---

### 🌟 Features
*   **🧠 Intelligent AI Engine:** High-performance **XGBoost** pipeline with verified **86.25% accuracy**.
*   **📊 Universal Ingestion:** Schema-agnostic feature extractor for any CSV/Excel from any business.
*   **🚀 Multi-Tenant SaaS:** Secure **X-API-Key** management for enterprise-scale integration.
*   **📧 Retention Automation:** Dynamic recovery email engine with real-time SMTP/Gmail support.
*   **🛠️ Tech Stack:** Flask, SQLAlchemy, Scikit-Learn, Pandas, Gunicorn, PostgreSQL.

---

### 🚀 Quick Start (Local)
1.  **Clone the Repo:** 
    ```bash
    git clone https://github.com/umang1506/Churn_Prediction.git
    cd ChurnShield
    ```
2.  **Install Requirements:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Setup Environment:**
    Create a `.env` file with your `SMTP_USER` and `SMTP_PASS` (for real emails).
4.  **Run the App:**
    ```bash
    python app.py
    ```

---

### 🔌 API Integration (Flipkart / Amazon Example)
You can integrate ChurnShield into any backend using our REST v1 API:

```python
import requests

response = requests.post(
    "https://your-domain/api/v1/predict-json",
    headers={"X-API-Key": "your_cs_key_here"},
    json={
        "customers": [
            {"customer_id": "F001", "tenure": 12, "total_charges": 500}
        ]
    }
)
print(response.json())
```

---

### 📊 Model Performance
*   **XGBoost Accuracy:** 86.25%
*   **Key Metrics:** Focuses on high Recall to ensure maximum churner detection.
*   **Feature Importance:** Recency, Frequency, and Monetary (RFM) analysis as primary drivers.

---

### 📈 Deployment (Production)
Developed for professional deployment on **Render.com** or **Docker**. A `Procfile` is included for instant web service orchestration.

**ChurnShield AI — Predict Churn. Retain Customers. Grow Revenue.** 🚀✨
