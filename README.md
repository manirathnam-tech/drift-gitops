# drift-gitops

## Golden manifest artifacts

The `Publish golden manifests` workflow renders `apps/online-boutique` for each
push to `main` and uploads the result at `golden/<commit-sha>/` in the private
S3 bucket. The orchestrator retrieves `rendered.yaml` and `source.tar.gz` by the
Git revision in the DriftEvent. The source snapshot lets the validator check a
candidate patch without needing GitHub credentials. The workflow also publishes
SHA-256 checksums and commit metadata.

Configure these repository Actions variables after the infrastructure stack
has created the publisher role and bucket:

- `AWS_GOLDEN_PUBLISH_ROLE_ARN`
- `GOLDEN_MANIFESTS_BUCKET`

The workflow uses GitHub OIDC. It requires the account's OIDC provider and the
role trust restricted to this repository's `main` branch; it uses no long-lived
AWS keys.

## Remediation pull requests

`Validate remediation proposal` runs on pull request events with read-only
permissions. It checks out the proposed GitOps revision, renders
`apps/online-boutique`, and runs the shared DRIFT kubeconform, Conftest, and
Checkov validators. The per-check JSON report is retained as a GitHub Actions
artifact for 14 days. The workflow does not use AWS credentials or change
repository content. Generated DRIFT patches are restricted to application
manifest paths, so they cannot edit the validation workflow.

Before treating this check as a merge gate, configure the `main` branch rules
to require the `Validate rendered GitOps state` check. Use the `drift-severity-0`
through `drift-severity-3` labels as the review signal: severity 0–1 proposals
may be eligible for auto-merge after every required check passes; severity 2–3
proposals require a human review and approval. The `Severity review gate`
check passes severity 0–1 proposals without approval; for severity 2–3 it waits
for another human to approve the current PR revision and fails while a current
review requests changes. Require both `Validate rendered GitOps state` and
`Severity review gate` in the `main` branch rules. The `Severity merge policy`
workflow enables GitHub auto-merge for non-draft severity 0–1 DRIFT PRs only
after both checks succeed. It never enables auto-merge for severity 2–3. The
merge workflow is disabled until the repository Actions variable
`DRIFT_ENABLE_LOW_SEVERITY_AUTOMERGE` is set to `true`; set it only after those
branch rules are configured and verified. GitHub auto-merge waits for required
checks and reviews before merging.
