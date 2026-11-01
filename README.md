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
