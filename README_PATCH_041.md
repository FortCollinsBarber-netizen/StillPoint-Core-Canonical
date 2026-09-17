# Patch 041 — iCloud Authentication Boundary Correction

Patch 041 closes a production-discovered trust-boundary defect in Patch 039.

Real iCloud messages demonstrated that Apple's receiver-generated `Authentication-Results`
headers can appear after one or more `Received` trace fields. Patch 039 incorrectly treated
"before the first Received" as a universal authority rule and therefore discarded legitimate
Apple DMARC, DKIM, and SPF results even though the message had been retrieved directly from
the authenticated iCloud IMAP mailbox.

Earned correction:

- direct authenticated iCloud IMAP retrieval is the provider-local trust boundary;
- only exact Apple sender-authentication service IDs are promoted to authoritative evidence:
  `dmarc.icloud.com`, `dkim-verifier.icloud.com`, and `spf.icloud.com`;
- each trusted Apple service must report its expected method;
- header position remains preserved as audit evidence but no longer manufactures or destroys authority;
- non-Apple Authentication-Results remain audit-only;
- conflicting DMARC/SPF/DKIM results remain fail-closed in the deterministic safety gate;
- the independent Reply-To, attachment, group-mail, ambiguity, sensitivity, and commitment gates are unchanged;
- Patch 040 provenance tests are generalized so the provenance guard itself does not become stale jurisdiction;
- no schema, governance, standing delegation, warrant, autonomous class, release condition, or external-action authority is widened.

The production evidence that motivated the patch showed valid iCloud DMARC, DKIM, and SPF
results for the CCU sender and valid results for Zillow. Zillow remains blocked independently
because its Reply-To differs from its authenticated sender.

The governing distinction is: header position is evidence about provenance; it is not itself provenance.
