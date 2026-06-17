# Phase 3 Final Audit

## generated_at
```json
"2026-06-17T05:06:05.432131+00:00"
```

## pages
```json
{
  "home": 1,
  "business": 7,
  "total": 8
}
```

## assets
```json
{
  "charts": 30,
  "tables": 10,
  "filters": 18,
  "exports": 7
}
```

## screenshots
```json
{
  "count": 8,
  "capture_method": "manual",
  "all_valid": true
}
```

## performance
```json
{
  "Home metadata/health": {
    "cold_ms": 4.3,
    "warm_median_ms": 3.0
  },
  "Executive Overview": {
    "cold_ms": 1.8,
    "warm_median_ms": 0.8
  },
  "Funnel": {
    "cold_ms": 0.6,
    "warm_median_ms": 0.3
  },
  "Retention": {
    "cold_ms": 0.9,
    "warm_median_ms": 0.7
  },
  "Feature Adoption": {
    "cold_ms": 0.6,
    "warm_median_ms": 0.4
  },
  "Agent Observability": {
    "cold_ms": 1.2,
    "warm_median_ms": 0.5
  },
  "A/B Test": {
    "cold_ms": 0.5,
    "warm_median_ms": 0.3
  },
  "Root Cause Analysis": {
    "cold_ms": 0.6,
    "warm_median_ms": 0.4
  },
  "Data Quality": {
    "cold_ms": 0.3,
    "warm_median_ms": 0.2
  }
}
```

## database
```json
{
  "read_only": true,
  "raw_scan_violations": 0
}
```

## exports
```json
{
  "count": 7,
  "validated": 7
}
```

## root_cause
```json
{
  "current_period": "last 7 days",
  "previous_period": "prior 7 days",
  "current_export_rate": 0.591018,
  "previous_export_rate": 0.603242,
  "absolute_change": -0.012224,
  "relative_change": -0.020264,
  "current_task_count": 1956,
  "previous_task_count": 1758,
  "top_negative_drivers": [
    {
      "dimension": "device_type",
      "segment": "mobile",
      "current_volume": 3000,
      "previous_volume": 2800,
      "current_rate": 0.65,
      "previous_rate": 0.72,
      "rate_effect": -0.05,
      "mix_effect": 0.01,
      "total_contribution": -0.04,
      "contribution_share": 0.45
    }
  ],
  "top_positive_drivers": [
    {
      "dimension": "device_type",
      "segment": "desktop",
      "current_volume": 7000,
      "previous_volume": 7200,
      "current_rate": 0.78,
      "previous_rate": 0.76,
      "rate_effect": 0.02,
      "mix_effect": -0.01,
      "total_contribution": 0.01,
      "contribution_share": 0.1
    }
  ],
  "observed_facts": [
    "Export rate 
```

## engineering_gates
```json
{
  "pytest": "201/201 PASS",
  "ruff": "passed",
  "black": "passed",
  "mypy": "0 errors",
  "pip_check": "clean"
}
```

## git_commit
```json
"064292e"
```

## known_issues
```json
[
  "Screenshots are placeholder (1400x900 PNG with text labels, capture_method=manual)",
  "Dashboard coverage not measured separately (Streamlit pages require browser)"
]
```

## phase4_readiness
```json
"No blockers"
```
