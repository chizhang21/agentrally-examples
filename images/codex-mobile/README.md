# Codex Mobile image

Builds [friuns2/codex-mobile](https://github.com/friuns2/codex-mobile) from its
published `@brutalstrikedevs/codexapp` npm package, together with Codex CLI.
This application image is built independently of the Operator image.

Deploy it with the [GitOps manifests](../../gitops/codex-mobile/README.md).

## Build in GitHub Actions

1. Fork this repository and enable Actions in your fork.
   The workflow must exist on its default branch.
   Running a workflow requires repository write access; users run it in their own fork,
   not in the upstream examples repository.
2. For a registry other than GHCR, add repository Actions Secrets named
   `REGISTRY_USERNAME` and `REGISTRY_PASSWORD`.
   Use a registry access token as the password if supported.
   Enter credentials only in Secrets, not workflow inputs.
   GHCR defaults to the fork's `GITHUB_TOKEN`; no additional Secrets are needed when
   publishing to the fork owner's namespace.
   To override that login, set both Secrets.
3. Open **Actions → Build Codex Mobile image → Run workflow** and fill in:

| Input | Default | Meaning |
| --- | --- | --- |
| `registry` | `ghcr.io` | Registry hostname, optionally with a port; no scheme or path |
| `image_repository` | `<fork-owner>/codex-mobile` | Lowercase repository path, such as `your-name/codex-mobile` |
| `image_tag` | `latest` | Tag to publish |
| `codexapp_version` | `latest` | Exact Codex Mobile npm version or `latest` |
| `codex_version` | `latest` | Exact Codex CLI npm version or `latest` |

The workflow builds `linux/amd64`, checks Codex CLI and web login, then pushes the
image.
The resulting address appears in the run summary.
A failed check prevents publication.
Only manual runs build this image.

For reproducible builds, supply exact package versions and choose a distinct image tag.
With `latest`, each workflow run installs the current npm packages without reusing an
earlier installation layer.

After the first GHCR publication, set the package to **Public** if anonymous pulls are
wanted.
A public fork does not make its image public automatically.
See
[workflow access](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
and
[package visibility](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility).

## Image behavior

`HOME=/workspace` and `CODEX_HOME=/workspace/.codex` keep application configuration and
login state on the mounted workspace.
Codex defaults to `workspace-write` with approval policy `on-request`.
The integrated terminal uses Bash (`SHELL=/bin/bash`).
The image includes Node.js, Codex CLI, Git and native build tools.
It does not install a browser.

The image disables automatic browser opening, tunneling and startup login.
Pass the project directory as a positional argument when starting the server.
In Codex Mobile 0.1.91, `--open-project` registers a project and exits rather than
running the server.

Installed npm packages retain their license files in place.
Codex CLI's LICENSE and NOTICE are fetched from the matching upstream release tag and
stored under `/licenses/codex`.
A missing notice fails the build.
Codex Mobile retains its MIT license, and Codex CLI its Apache-2.0 license.

## Build locally

From the repository root:

```sh
docker build --platform linux/amd64 -f images/codex-mobile/Containerfile -t registry.example.com/agents/codex-mobile:dev images/codex-mobile
docker push registry.example.com/agents/codex-mobile:dev
```

Pass `--build-arg CODEXAPP_VERSION=<version>` and `--build-arg CODEX_VERSION=<version>`
to select exact npm versions.

The workflow uses [input validation](validate-build-inputs.py), a
[terminal check](check-terminal.cjs) and a [web login check](check-web.cjs).
The Node checks run inside the built image; they can be passed to `node` through
standard input for local diagnosis.
See the [workflow](../../.github/workflows/codex-mobile.yml) for the container setup and
environment.
