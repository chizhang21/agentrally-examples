# AgentRally Operator examples

Complete Agent deployments for
[AgentRally Operator](https://github.com/chizhang21/agentrally-operator).

Each application directory contains its deployment manifests and instructions.
Application-specific image recipes live alongside those manifests.
Run the commands below from the repository root.

Basic CRs and configuration references are in the
[Operator repository](https://github.com/chizhang21/agentrally-operator/tree/v0.0.3/examples).

## Prerequisites

Install AgentRally Operator and agent-sandbox Core and Extensions first.
See the [Operator installation guide](https://github.com/chizhang21/agentrally-operator/blob/main/docs/installation.md).

The manifests use the `arally.io/v1alpha1` API provided by Operator `v0.0.3`.
Adjust image addresses, storage and ingress settings for your cluster.
Application setup and model authentication remain part of each project.

Apply one project at a time.

## Deployment order

1. Apply the AgentGroup and wait for `Ready`.
   The Operator creates its dedicated namespace.
2. Prepare Secrets and any external PVC in that namespace.
3. Apply the AgentDefinition and AgentInstance.

Keep actual credentials outside versioned files.
The optional Secret template in the HTTP project contains placeholders only.
Use ignored `secrets/` files or your existing secret manager for real values.

## Application examples

| Project | Environment | State |
| --- | --- | --- |
| [Codex Mobile](codex-mobile/README.md) | Coding agent with a web UI and terminal | External PVC for projects and login state |
| [OpenClaw](openclaw/README.md) | Resident personal assistant | External PVC for configuration, credentials and workspace |
| [HTTP API Agent](http-api-agent/README.md) | Minimal Pydantic AI Agent with a public image | Stateless by default |

The Codex Mobile [image recipe and build checks](codex-mobile/image/README.md) live with
its deployment example.
A manual GitHub Actions workflow can build and publish that image.

## Lifecycle and GitOps

The YAML manifests in each application directory declare its desired deployment.
Select the configured manifests for one application as the GitOps source.
Exclude the optional HTTP Secret template from automatic reconciliation.
Provide those Secrets through your chosen secret manager.
Keep image sources and build checks outside the deployment scan.
Configure dependency ordering and readiness checks so Group namespace creation finishes
before namespaced resources are applied.
The directory layout alone does not provide that ordering.

AgentInstances run by default.
Add `spec.operatingMode: Suspended` to pause one; remove that field to resume.
Change the manifest in Git when a GitOps controller owns the resource.

Changing a definition publishes a new revision.
Existing instances retain their accepted revision, including through suspend/resume.
Apply the updated definition and wait for its current-generation `Ready` condition.
Read its `status.currentRevision`.
Set the instance's `spec.revision` to that hash and change `spec.restartToken` in the same update.
A restart without a revision change retains the instance's accepted configuration.
Pin images by digest when reproducible execution matters.

Delete an instance and wait for execution cleanup before deleting its definition.
Retain external PVCs and their Groups when keeping workspace data.
Configure GitOps pruning accordingly.

## Validate manifests

After creating the Group and preparing its dependencies, validate the selected application
against the installed CRDs and admission policies before applying it.
For Codex Mobile:

```sh
kubectl apply --dry-run=server -f operator/codex-mobile/definition.yaml -f operator/codex-mobile/instance.yaml
```

This checks API admission.
Image startup, credentials, Gateways and storage still need runtime verification.
The opt-in OpenClaw lifecycle test is documented in the
[OpenClaw example](openclaw/README.md#run-the-openclaw-test).
