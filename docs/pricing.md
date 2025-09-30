# kalliste-alpha — Pricing (v0.1 draft)

**Model:** Hosted cloud subscriptions (usage + seats) with a free dev tier, plus enterprise.  
Anchors: vector DBs charge storage + ops (reads/writes) and gate higher SLAs/features on paid tiers. Pinecone serverless shows $0.33/GB-mo, $4 per million writes, $16 per million reads (as reference, not a target) and explains the ops model. Qdrant Cloud advertises a free dev cluster (≈1GB RAM / 4GB disk) as an on-ramp. LangSmith/LlamaCloud use free→paid dev funnels. [Sources: Pinecone pricing & docs; Qdrant docs; LangSmith/LlamaCloud]  

## Tiers (initial)

- **Free (dev)**  
  Projects: 1 • Storage: **1 GB** • Calls: **200k/mo** • Community support

- **Pro ($19/user/mo)**  
  Projects: 5 • Storage: **10 GB** • Calls: **5M/mo** • OAuth SSO-lite • Activity logs

- **Team ($149/org/mo + $15/user/mo)**  
  Projects: 20 • Storage: **50 GB** • Calls: **20M/mo** • Org SSO (OIDC/SAML) • RBAC • Backups • Audit

- **Enterprise (annual, custom)**  
  SSO/SAML • VPC/on-prem • HA/SLA (99.9–99.95%) • Full audit/retention • Private networking • Priority support

## Overage (starting points)
- **JSON-RPC calls:** $0.30 per million  
- **Storage:** $0.30 per GB-month

> These are intentionally below vector DB read pricing to fit a “memory service” cost profile; tune against your true COGS and customer usage.

## Notes
- “Cloud storage will cost money” — usage is metered for storage + JSON-RPC requests.  
- Repo stays open for local use (see LICENSE).  
- Enterprise mirrors what buyers expect from adjacent infra (RBAC, observability, HA, VPC/on-prem).  

References: Pinecone serverless pricing/ops, Qdrant Cloud free tier, LangSmith/LlamaCloud pricing pages.  
