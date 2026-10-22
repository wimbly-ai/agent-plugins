---
name: onboarding
description: Guide Wimbly onboarding or repair a connection by checking setup progress and linking to the next mailbox, LinkedIn, or profile-review step.
---

# Wimbly onboarding

Guide the partner to a working Wimbly account, one step at a time. This skill
checks setup progress; the partner completes connections and profile reviews
on Wimbly's website. Wimbly accounts are currently enrolled by its team.

## Connect and read progress

Use the bundled `wimbly` connection and call `get_setup_status` with empty
arguments. During onboarding, use this tool to read progress and the website
to complete setup steps. If the connection needs authentication, guide the
partner to the host's Connect or sign-in action and let Wimbly's OAuth flow
finish.
An email code belongs on Wimbly's sign-in page, never in this conversation.

If the account is not enrolled, explain that enrollment is required and link
to https://www.wimbly.ai/contact for contacting the Wimbly team. Do not claim to have
created an account, requested access, or sent a message.

If the tool is unavailable or fails, say progress could not be checked and
offer https://app.wimbly.ai/auth/signed-in to continue on the website. Report
only a setup state returned by a successful tool call.

## Guide the next step

Use the returned `step` and `nextUrl`. Present the link and the one action
the partner needs to take. Open it with the host's normal link-opening
capability when available; otherwise show a clickable link.

| Step | What to explain |
| --- | --- |
| `connect_mailbox` | Connect Gmail or Outlook on Wimbly's page. The mailbox's provider asks for permission there. If firm administrator approval is required, the partner follows the page's instructions. |
| `connect_linkedin` | Choose one of the methods Wimbly's page offers. Passwords, session details and security challenges stay on that page. The browser-session method requires the mail extension; the credentials and archive paths do not. An archive request can complete this step before the archive arrives. |
| `about_you` | Review or correct personal background on Wimbly's About you page, then press Continue. |
| `icp` | Review the kinds of clients the partner wants to win work from on Wimbly's ideal-client page, then press Continue. This connection cannot save or edit a profile. |
| `ready` | Confirm that setup is complete. The mail panel is optional, and its installation is available on the account page. Setup completion does not establish that mailbox or LinkedIn history has finished importing. |

When `setupComplete` is true but `step` is earlier than `ready`, explain the
specific repair or review needed without calling the account new or
restarting the whole onboarding journey. Skip completed steps.

After a browser handoff, wait for the partner to return or say they finished,
then call `get_setup_status` again. Their report triggers a check; only a
fresh tool result establishes completion. A reopened conversation starts
with the same read, so no local checklist or conversation memory is needed.
Do not poll while the partner is completing a page.

Finish when the server returns `ready`. The same connection provides
Wimbly's other available tools for the partner's later requests. Completing
onboarding starts no research, mailbox read or outreach on its own.
