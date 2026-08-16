---
title: Playbook Template
tags:
  - soc
  - triage
  - incident-management
category: soc
type: template
status: draft
classification: internal
version: "0.1"
review_owner: soc-lead
review_interval_days: 90
last_reviewed: 2026-08-15
next_review: 2026-11-13
changelog:
  - date: 2026-08-15
    change: Initial template creation
---

# SOP-SOC-XXX - Playbook Title

> **Scope:** SOC Service - 1st Line, 2nd Line, 3rd Line
> **Role:** Incident Commander, SOC Analyst, Platform Engineer
> **Status:** DRAFT

---

## Purpose

Define the purpose and objective of this playbook. Specify which alerts or threat scenarios this document applies to.

---

## Verification and Triage

Step-by-step instructions to verify the alert and rule out false positives:

1. **Verify Telemetry:** Check log sources and verify event details.
2. **Review Context:** Investigate user, asset, and environment context.
3. **Determine Classification:** Classify the incident priority (P1-P4) using the criteria in the general triage SOP.

---

## Containment Steps

Specific, sequential actions to contain the security incident and prevent further impact:

* **Step 1:** Isolate the affected host or account.
* **Step 2:** Revoke session tokens or change credentials.
* **Step 3:** Restrict network access to target segments.

---

## Eradication and Remediation

Steps to clean up and restore systems to a secure state:

* **Step 1:** Remove malicious artifacts (files, registry keys, persistence mechanisms).
* **Step 2:** Restore from trusted backups if necessary.
* **Step 3:** Apply permanent patches or security group restrictions.

---

## Post-Incident Review

Every P1 security incident requires a formal post-mortem within 5 business days per SOP-SOC-009. Ensure all action items are captured, assigned priority levels (P0-P2), and tracked within their target SLAs.

---

## MITRE ATT&CK Mapping

List the techniques and tactics addressed by this playbook:

* **Tactic:** [e.g. Credential Access (TA0006)]
* **Technique:** [e.g. Brute Force (T1110)]
