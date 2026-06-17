# Phase 2 Sql Portfolio
Generated: 2026-06-17T04:01:01.108076+00:00
```json
{
  "queries": [
    {
      "query_id": 1,
      "filename": "01_dau_wau_mau.sql",
      "business_question": "How many distinct active users do we have on a daily, weekly (rolling 7-day), and monthly (rolling 30-day) basis? This helps track user engagement trends and identify growth or decline in active usage.",
      "row_count": 120,
      "execution_time_ms": 103.4,
      "status": "passed"
    },
    {
      "query_id": 2,
      "filename": "02_new_and_activated_users.sql",
      "business_question": "How many new users sign up each day, and what fraction complete their first successful export (activation) within 7 days? This identifies whether the onboarding experience is effective at converting signups into value-generating users.",
      "row_count": 121,
      "execution_time_ms": 73.8,
      "status": "passed"
    },
    {
      "query_id": 3,
      "filename": "03_time_to_first_export.sql",
      "business_question": "What is the distribution of days from user signup to first successful task export across the user base? Understanding this helps set expectations for onboarding timelines and identify users who may need additional support.",
      "row_count": 14915,
      "execution_time_ms": 58.3,
      "status": "passed"
    },
    {
      "query_id": 4,
      "filename": "04_full_task_funnel.sql",
      "business_question": "What proportion of tasks progress through each stage of the document processing pipeline (Upload -> OCR -> Anonymization -> Risk Detection -> Autofill -> Review -> Export), and where do the biggest drop-offs occur? This identifies the weakest conversion points.",
      "row_count": 7,
      "execution_time_ms": 219.7,
      "status": "passed"
    },
    {
      "query_id": 5,
      "filename": "05_device_funnel.sql",
      "business_question": "How does the task conversion funnel differ between device types (desktop vs mobile vs tablet)? Device-specific drop-offs can indicate UI/UX issues that only affect certain platforms.",
      "row_count": 21,
      "execution_time_ms": 245.5,
      "status": "passed"
    },
    {
      "query_id": 6,
      "filename": "06_channel_funnel.sql",
      "business_question": "How does the task conversion funnel and export rate vary by the user's acquisition channel (organic, paid, referral, etc.)? This helps marketing teams understand which channels bring users who not only sign up but also successfully complete tasks.",
      "row_count": 5,
      "execution_time_ms": 189.4,
      "status": "passed"
    },
    {
      "query_id": 7,
      "filename": "07_d1_d7_d30_retention.sql",
      "business_question": "Of users active on a given day, what fraction return on day +1, day +7, and day +30? D1/D7/D30 retention is a standard SaaS metric that measures product stickiness and long-term engagement.",
      "row_count": 120,
      "execution_time_ms": 172.8,
      "status": "passed"
    },
    {
      "query_id": 8,
      "filename": "08_cohort_retention_matrix.sql",
      "business_question": "For each weekly signup cohort, what fraction of users are active in each subsequent week? The retention matrix (cohort vs. week number) reveals whether newer cohorts engage better or worse than older ones over time.",
      "row_count": 156,
      "execution_time_ms": 116.0,
      "status": "passed"
    },
    {
      "query_id": 9,
      "filename": "09_feature_adoption.sql",
      "business_question": "How does adoption of key product features (OCR, anonymization, risk detection, autofill) trend over time? Which features are gaining or losing adoption share compared to the total task volume?",
      "row_count": 605,
      "execution_time_ms": 208.5,
      "status": "passed"
    },
    {
      "query_id": 10,
      "filename": "10_user_lifecycle_segments.sql",
      "business_question": "How many users fall into each lifecycle stage (new, active, retained, resurrected, churned, dormant) on a given day? Understanding the distribution of user states helps the product team evaluate the impact of engagement initiatives and spot churn trends early.",
      "row_count": 329,
      "execution_time_ms": 202.6,
      "status": "passed"
    },
    {
      "query_id": 11,
      "filename": "11_three_day_active_users.sql",
      "business_question": "Which users are active on three consecutive days, and what patterns exist in consecutive-day engagement? Consistent daily usage is a strong signal of product-market fit and user habit formation.",
      "row_count": 120,
      "execution_time_ms": 131.2,
      "status": "passed"
    },
    {
      "query_id": 12,
      "filename": "12_first_successful_task.sql",
      "business_question": "For each user, what was the first task that they successfully exported, and how long did it take them from signup to that first success? This measures time-to-value for new users.",
      "row_count": 14915,
      "execution_time_ms": 197.4,
      "status": "passed"
    },
    {
      "query_id": 13,
      "filename": "13_latest_task
```

*(Full data in phase2_sql_portfolio.json)*
