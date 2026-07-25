# Security

DocuCommit is an educational prototype and has not completed a production
security review. Do not deploy it with confidential documents without adding
production session settings, database migrations, managed file storage,
transport security, and an independent security assessment.

## Access control

Profile images and project, document, branch, revision, diff, export, and merge
data are scoped to the authenticated owner. Regression tests cover both
unauthenticated requests and attempts by a second user to access another user's
resources.

## Legacy local databases

Older revisions automatically created a shared development account. New
installations no longer create any account; use the registration flow instead.

An existing SQLite database may still contain that legacy account. This update
does not delete or reassign it automatically because doing so could destroy or
orphan local documents. If the database contains no data you need, remove the
local development database and restart the app. If its data must be preserved,
reset or remove the legacy account and deliberately reassign its documents
before deploying the database anywhere.
