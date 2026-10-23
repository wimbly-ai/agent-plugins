---
name: onboarding
description: Guide Wimbly onboarding or repair a connection by checking setup progress and linking to the next mailbox, LinkedIn, or profile-review step.
---

# Wimbly onboarding

Read progress through the bundled `wimbly` connection. The partner completes
connections and reviews on Wimbly's pages. Wimbly accounts are enrolled by its team.

## Read progress

Call `get_setup_status` with `{}`. If authentication is needed, use the host's
Connect or sign-in action and let Wimbly's OAuth flow finish. Email codes,
passwords and security challenges belong on the sign-in page.

For an unenrolled account, explain that enrollment is required and link to
https://www.wimbly.ai/contact. Report only what a successful tool call establishes.
If the tool is unavailable or fails, say progress could not be checked and offer
https://app.wimbly.ai/auth/signed-in. This skill creates no account or access request.

## Show the current step

Every initial step is required. Never offer Skip, Not now, or to finish a
required step later. The card can stay open while the partner chats. When
incomplete setup prevents their requested Wimbly work, explain that setup comes
first and keep the current step available.

In a host that renders the tool's MCP App, let the card hold the checklist and
current action. On a fresh setup, say only: “Four short steps. First, your mailbox.”
For a resumed setup, use one short line naming the current step. Avoid repeating
the card's steps or posting another checklist. The card opens Wimbly's pages,
checks progress in place and updates the conversation when a step finishes.
Only an actual rendered card establishes that this host supports the UI.

In native Codex, Claude Code, or a host that does not render the card, use the
returned `step` and `nextUrl` to explain one action and show a clickable trusted
link. Use the host's normal link-opening action when available.

| Step | Text and link fallback |
| --- | --- |
| `connect_mailbox` | Connect Gmail or Outlook on Wimbly's page. Choose the provider and start consent there; the link itself does not start consent. Follow any firm administrator approval instructions on that page. |
| `connect_linkedin` | Choose a method offered on Wimbly's page. Browser-session connection requires the mail extension; credentials and archive paths do not. An export request completes this setup step before the file arrives. If the server records a request: “LinkedIn export requested. Upload the ZIP in Wimbly when it's ready.” An archive already ready still needs uploading; only an active connection or an imported archive establishes ingestion. |
| `about_you` | Review or correct your background on Wimbly's About you page, then press Continue. |
| `icp` | Review the kinds of clients you want to win on Wimbly's ideal-client page, then press Continue. This skill guides the review; it does not save profile edits. |
| `ready` | Setup is complete. The mail panel is optional on the account page. Setup completion establishes neither completed history import nor automatic ingestion of a requested LinkedIn export. |

For `setupComplete: true` with an earlier `step`, raise the specific repair only
when the partner's request needs that connection. Use the repair card or its
returned link without step numbers or restarting completed onboarding. A request
that needs no lapsed connection can continue.

## Recheck after a handoff

In text hosts, wait for the partner to return or say they finished, then call
`get_setup_status` again. Their report triggers a check; a fresh tool result
establishes completion. Start reopened conversations with that same read.
The assistant does not run a polling loop: the rendered card owns its bounded
five-second checks for up to two minutes after a person starts a connection.

Finish at `ready`. The same connection provides Wimbly's later tools; completing
setup starts no research, mailbox read or outreach on its own.
