---
type: llm
weight: 1
---

Scenario: three API keys (model vendor, email provider, object storage) for Acme's Northwind instance.

Pass when the names follow one fixed scheme across all vendors, `<org>-<instance>-<service>` or equivalent (e.g. acme-northwind-email), and it suggests generating them in the provisioning script.

Fail when names follow no single scheme, or it does not mention generating them.
