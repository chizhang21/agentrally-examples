# AgentRally Examples

Configuration and deployment examples for
[AgentRally Operator](https://github.com/chizhang21/agentrally-operator).

The top-level `operator/` directory covers the Operator API and Kubernetes resource references.
Start with [Operator examples](operator/README.md) for minimal CRs, workspace storage,
group policy, HTTPRoute, custom templates and deployer RBAC.

Application manifests and deployment instructions live under `gitops/`.
Image recipes and build checks live under `images/`.
Codex Mobile includes a [separate image recipe](images/codex-mobile/README.md)
and a manual image build workflow.

```text
operator/
  base/
  rbac/
gitops/
  codex-mobile/
  openclaw/
  http-api-agent/
images/
  codex-mobile/
```

| Project | Environment | State |
| --- | --- | --- |
| [Codex Mobile](gitops/codex-mobile/README.md) | Coding agent with a web UI and terminal | External PVC for projects and login state |
| [OpenClaw](gitops/openclaw/README.md) | Resident personal assistant | External PVC for configuration, credentials and workspace |
| [HTTP API Agent](gitops/http-api-agent/README.md) | Your HTTP agent image | Ephemeral by default; optional Sandbox-owned PVC |

## Prerequisites

Install AgentRally Operator and agent-sandbox Core and Extensions first.
See the [Operator installation guide](https://github.com/chizhang21/agentrally-operator/blob/main/docs/installation.md).

The manifests use the `arally.io/v1alpha1` API provided by Operator `v0.0.2`.
Adjust image addresses, storage and ingress settings for your cluster.
Application setup and model authentication remain part of each project.

Run commands in project READMEs from this directory.
Apply one project at a time.

## Deployment order

1. Apply the AgentGroup and wait for `Ready`.
   The Operator creates its dedicated namespace.
2. Prepare Secrets and any external PVC in that namespace.
3. Apply the AgentDefinition and wait for `Ready`.
4. Apply the AgentInstance and wait for `Ready`.

Keep actual credentials outside versioned files.
The Secret manifests in the HTTP project contain placeholders only.
Use ignored `secrets/` files or your existing secret manager for real values.

## Lifecycle and GitOps

The YAML manifests under `gitops/` declare the desired Agent deployments.
Select the configured manifests for one application as the GitOps source.
Exclude the HTTP Secret templates from automatic reconciliation.
Provide those Secrets through your chosen secret manager.
Keep image sources and build checks outside the deployment scan.
Configure dependency ordering and readiness checks so Group namespace creation finishes
before namespaced resources are applied.
The directory layout alone does not provide that ordering.

Declare `spec.operatingMode: Running` or `Suspended` on an AgentInstance.
Change the desired mode in Git when a GitOps controller owns the resource.

Changing a definition publishes a new revision.
Existing instances retain their accepted revision, including through suspend/resume.
After the updated definition is Ready, change the instance's `spec.restartToken` to
adopt that revision.
Pin images by digest when reproducible execution matters.

Delete an instance and wait for execution cleanup before deleting its definition.
Retain external PVCs and their Groups when keeping workspace data.
Configure GitOps pruning accordingly.

## Validate manifests

The Operator repository contains the CRD admission and reference checks.
From a checkout of its matching source, run:

```sh
AGENTRALLY_EXAMPLES_DIR=/path/to/agentrally-examples \
go test ./tests/packaging -run 'AdmissionAndPruning|ReferencesResolveWithinTheSameGroup'
```

The opt-in OpenClaw lifecycle test is documented in [the OpenClaw project](gitops/openclaw/README.md#run-the-openclaw-test).
The selected directory includes both `operator/` and the complete application examples.
These are alternative configurations; select one example at a time when deploying.

## License

Project manifests and supporting code use the [Apache License 2.0](LICENSE).
Built applications and installed packages retain their own licenses.
