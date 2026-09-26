# Hostmap support

For usage questions and reproducible bugs, use [GitHub issues](https://github.com/magrathean-uk/hostmap/issues). Start with the [README](README.md) and [review prompts](docs/prompts.md).

Include the Hostmap version (`python3 -m hostmap --version`), Python version, Linux distribution where relevant, collection mode, command used, expected result, and a minimal sanitized example. For offline diff problems, describe both bundles' schema versions and whether all files listed in their manifests are present.

Do not attach full bundles or archives to a public issue. They can contain hostnames, usernames, paths, software inventories, and topology. Use synthetic examples or small excerpts that you have reviewed yourself. Report suspected secret exposure or security defects through [SECURITY.md](SECURITY.md).

## Common gaps

- Collection requires Linux. Help, version output, and offline diff can run on other platforms.
- Missing tools, inaccessible local container sockets, permission errors, and bounded directory walks leave incomplete evidence. A missing entry does not prove a service is absent.
- `paranoid` skips copied configs and repository/CI collection; some files found in `safe` bundles are therefore absent.
- Existing bundle, ZIP, and diff report paths are protected from replacement. Choose a new output location when a path conflicts.
- An oversized ZIP fails collection's archive step. Inspect the retained directory before retrying with `--no-zip` or an appropriate positive `--max-zip-mb` limit.

Hostmap is an alpha project. This repository does not publish a response-time commitment or a supported-release schedule.
