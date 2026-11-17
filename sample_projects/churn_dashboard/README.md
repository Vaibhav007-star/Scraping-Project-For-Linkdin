# Customer Churn Prediction & Retention Intelligence Platform

An end-to-end Machine Learning pipeline that predicts customer churn probability and flags retention risks before contract renewals.

## Business Problem
Subscription SaaS enterprises lose millions annually due to silent customer attrition. Identifying at-risk customers only when cancellation requests arrive is too late. The customer success team needed an automated, daily risk scoring engine to proactively intervene on accounts exhibiting drop-offs in product engagement.

## Technical Solution & Architecture
- **Data Engineering**: Processed 120,000+ historical account events, contract data, support ticket volumes, and in-app clickstream logs using Polars and DuckDB.
- **Feature Engineering**: Built rolling 30/60/90-day activity trends, NPS delta indicators, and ticket resolution latency metrics.
- **Model Training**: Trained an optimized XGBoost Classifier with Bayesian hyperparameter tuning. Handled severe class imbalance (8:1) via focal loss and SMOTE-Tomek links.
- **Explainability**: Integrated SHAP (SHapley Additive exPlanations) values to output the exact top-3 risk drivers for each customer flag in the UI.
- **Deployment**: Exposed low-latency (14ms) batch and real-time REST inference endpoints with an interactive analytical monitoring dashboard.

## Quantifiable Impact & Results
- **ROC-AUC**: Achieved **0.91 AUC** and an **F1-score of 0.89** on out-of-time test sets.
- **Retention**: Enabled early intervention that decreased quarterly gross churn by **18.3%**.
- **ARR Saved**: Protected **$1.42M** in recurring revenue within the first 6 months of rollout.

## Tech Stack
- **Languages & Frameworks**: Python, Polars, Scikit-Learn, XGBoost, SHAP
- **Serving & Frontend**: FastAPI, Streamlit, HTML5 Canvas
- **Validation**: Playwright, PyTest
