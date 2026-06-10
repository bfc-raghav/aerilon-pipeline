# Aerilon Release Pipeline (Hackathon Problem 2)
Code change → signed evidence → four federated org sign-offs → OTA to the drone, in minutes.
Start with PREP_GUIDE.md. Architecture: release.yml fans one core pipeline out to four
acceptance gates whose policies live in policies/org-*/ and whose approvers live in
GitHub Environments. The Pi runs agent/update_agent.py to verify, install, health-check
and auto-rollback releases.
