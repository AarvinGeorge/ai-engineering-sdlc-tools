# Summary style

Each entry's summary says what was done and why it mattered. Write it from the user's requests,
the session title and the commit subjects. Never from tool output.

## HR style (default)

For a reader who does not work in software: HR, a client, a manager.

- 30 words or fewer.
- Plain language. Short sentences.
- The outcome, and why it mattered. Not the steps.
- No internal document numbers, plan codes, branch names, commit hashes, file paths or tool names.
- An abbreviation is spelled out or left out. Common ones a lay reader knows (AI, HR, PDF) may stay.
- Incidents and failures are recorded honestly, in neutral words. Say what happened and what was
  done about it. No blame, no drama, no hiding.
- Past tense, no "I". Start with the verb: "Built", "Fixed", "Planned", "Reviewed".

**What the scan checks, and what it does not.** `scan.py` catches codes and personal data: file
paths, branch names, commit hashes, document numbers, abbreviations, over-long summaries, emails,
phone numbers, key-like strings and the never-list. It cannot judge tone or content: drama or blame,
step-by-step lists instead of an outcome, or tool names written as ordinary words. Apply those rules
yourself; a clean scan does not mean the summary is good.

## Detailed style

For a technical reader, when the user asks for detail.

- Still 30 words or fewer.
- Keeps technical names: components, file names, branch names, tools.
- Still no secrets, emails, phone numbers or names on the never-list. The scan checks these in
  every style.

## Bad and good, HR style

All examples are invented.

1. **File path removed.**
   - Bad: "Edited src/auth/login.py and tests/test_login.py to fix the redirect."
   - Good: "Fixed the sign-in page so customers return to where they were after logging in."

2. **Abbreviation spelled out.**
   - Bad: "Added SSO for the Alpha app."
   - Good: "Added single sign-on to the Alpha app, so staff use their work account instead of a
     separate password."

3. **Incident written neutrally.**
   - Bad: "Huge mess: test script spammed a real customer, totally my fault, panic fix."
   - Good: "A test message reached a real customer by mistake. Testing was changed to use only
     invented contacts, and the customer was told."

4. **Branch name and commit hash removed.**
   - Bad: "Merged feat/checkout-v2 (a1b2c3d) into main."
   - Good: "Finished the new checkout page for the Beta site and made it live for all visitors."

5. **Internal document number removed.**
   - Bad: "Updated doc 42 per plan item P3.2."
   - Good: "Updated the release plan for the Alpha app so the team knows what ships next month."

6. **Steps replaced by the outcome.**
   - Bad: "Ran the tests, read the logs, changed three settings, re-ran the tests, and pushed."
   - Good: "Fixed a slow report page; it now opens in under two seconds."

7. **Tool name removed.**
   - Bad: "Used pytest and Playwright to build an end-to-end suite."
   - Good: "Added automatic checks that test the whole sign-up flow before each release."

8. **Too long, cut to the point.**
   - Bad: "Spent the afternoon going through the whole onboarding flow with the design notes,
     comparing each screen, writing down every difference, and then fixing most of them one by
     one until it matched."
   - Good: "Brought the onboarding screens in line with the agreed design."

## Merging and splitting

- Several sessions on one piece of work in a day become one entry.
- One long session that covered two separate pieces becomes two entries, each with its own summary.
