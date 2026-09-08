# Contributing

Use a branch and describe the concrete problem, resulting behavior and validation in
your pull request. Run the commands in the README before submitting changes.

Keep fixtures synthetic. Do not contribute real hosts, account identifiers, private
repository names, task text, customer data, credentials or generated review artifacts.
Local configuration belongs in ignored files. Run TruffleHog as well as the public-tree
check before publishing changes; pattern checks alone cannot identify all confidential
information.

Do not weaken readiness gates to make a test pass. Add regression tests when changing
branch selection, reviewer identity, stale-evidence handling or trigger authorization.
Integration tests must use systems you control and must not perform production actions.

Contributions are made under the repository’s MIT license.
