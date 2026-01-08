# Email Triage Task Context

## Objective
Process the user's inbox starting with the first batch of 20 unread emails. Apply the defined Golden Rules to categorize, flag, archive, or draft replies.

## Agents & Roles
- **@email-manager**: Orchestrates the process. Scans inbox, applies logic.
- **@email-drafter**: Writes DRAFT replies for relevant emails.
- **@email-curator**: Moves low-priority/newsletter items to archive.

## Constraints
- **Safety**: NEVER send emails. Only create drafts.
- **Safety**: Prefer archiving over deleting.
- **State**: Keep important emails UNSEEN (or mark back to unread).
- **Batch Size**: 20 emails.

## Golden Rules
1. **Critical**: External sender + Direct To: user -> Flag + Leave Unread.
2. **High**: Internal (@netskope.com) + Direct To: user -> Flag + Create Task.
3. **Low**: Internal + User in CC/BCC -> Delegate to Curator (Archive/Read later).
4. **Newsletters**: Archive.

## Tools
- `search_emails(criteria="unseen", limit=20)`
- `flag_email(uid, flag=True)`
- `create_task(description)`
- `draft_reply_tool(uid, reply_body)`
- `move_email(uid, target_folder="Archive")`
- `mark_as_unread(uid)`
