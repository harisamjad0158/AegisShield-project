# AegisShield — Security Release Assessment

## Project overview

AegisShield is a Kubernetes-based DevSecOps project
demonstrating containerized application deployment,
Helm release management, CI/CD, security scanning,
network isolation, and operational validation.

## Technology stack

- Docker
- Kubernetes (KinD)
- Helm
- GitHub Actions
- FastAPI
- PostgreSQL
- Trivy
- Bandit
- pip-audit
- Kubernetes NetworkPolicies
- Horizontal Pod Autoscaler (HPA)
- Vertical Pod Autoscaler (VPA)

## Production deployment

- Payment API image: `aegisshield/payment-api:1.0.3`
- Payment API replicas: 3
- PostgreSQL replicas: 1
- Helm revision at assessment: 7

## Experimental release candidate

Image: `aegisshield/payment-api:1.0.6-test4`

This image has not been promoted to production.

## Testing evidence

| Test | Result |
|---|---|
| Unit tests | 28 passed previously |
| Python dependency smoke tests | Passed |
| Restricted Docker runtime | Passed |
| PostgreSQL connection | Passed |
| Payment API integration | 6/6 passed |
| Candidate Kubernetes integration | Not completed |

The payment integration tests validated database readiness,
payment creation, retrieval, missing-payment handling,
invalid-payment handling, and database persistence
against temporary PostgreSQL.

## Vulnerability assessment

| Severity | Findings |
|---|---:|
| CRITICAL | 0 |
| HIGH | 46 |

The HIGH findings correspond to 11 unique CVEs.

The official Debian Security Tracker reported all 11 CVEs
as open for Debian 13 (Trixie), with no fixed versions listed
at the time of assessment.

These results do not establish runtime exploitability.

## Release decision

**HOLD — NOT APPROVED FOR DEPLOYMENT**

Formal security risk acceptance has not been granted.

The experimental candidate must not be deployed without
explicit authorization and appropriate security approval.

## Outstanding work

1. Assess exploitability and available mitigations.
2. Resolve or formally accept outstanding security risks.
3. Complete candidate Kubernetes integration testing.
4. Obtain release approval before promotion.

## Evidence files

Local security evidence is stored under:

`.security-reports/release-1.0.6-test4/`

Key reports:

- `trivy.json`
- `debian-verified-status.csv`
- `payment-integration-test-verified.txt`
- `final-security-decision.md`

## Rollback principle

Keep the last known-good production image and Helm release
available. Any future deployment or rollback must follow
the approved change procedure.

At assessment time, the deployed Helm revision was 7.

Do not assume that revision 7 will remain the correct
rollback target after future deployments.
