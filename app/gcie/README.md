# GCIE Case Record Knowledge Base — development version

Additive SQLAlchemy table `gcie_coaching_cases`; no existing student/session columns are altered.
Endpoints: POST/GET /gcie/cases, GET/PUT /gcie/cases/{id}, POST /gcie/cases/{id}/approve, GET /gcie/knowledge/search?q=...
All cases start in draft; approved cases are immutable and are the only cases eligible for knowledge search.
Approval requires a documented problem, intervention, and outcome. Approval is restricted by the existing app owner-auth middleware; this is not yet a multi-user authorization system.
This initial search uses keyword matching, **not** embeddings, RAG, or machine learning.
Do not enter identifiable student data into an external model without permission.
Deployment requires an independent database backup and staging tests. No production migration has been performed.
