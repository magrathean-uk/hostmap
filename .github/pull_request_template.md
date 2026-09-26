## Change

Describe the problem and the resulting behavior.

## Validation

List checks run and their results. State skipped checks and the reason. For collector changes, include the Linux paranoid smoke result. Do not attach private host bundles.

## Review checklist

- [ ] Collection remains read-only apart from output, with local container sockets and no remote API queries.
- [ ] Fixtures and examples contain no real credentials or private host details.
- [ ] Relevant tests cover changed behavior.
- [ ] README, prompts, skill, and schema agree if the bundle contract changed.
- [ ] Existing licence and attribution notices are preserved.
