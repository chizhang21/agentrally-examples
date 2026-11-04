# AgentRally Operator examples

Complete Agent deployments for
[AgentRally Operator](https://github.com/chizhang21/agentrally-operator).

| Project | Purpose | Requirements beyond the Operator |
| --- | --- | --- |
| [HTTP API Agent](http-api-agent/README.md) | Minimal Agent for verifying deployment, HTTP calls and suspend/resume | None in default demo mode |
| [OpenClaw](openclaw/README.md) | Resident personal assistant with persistent state | Gateway token and filesystem storage; model/channel setup for application use |

Start with HTTP API Agent to check your installation.
It uses a public image and returns a fixed response without model requests.
OpenClaw demonstrates a retained workspace and application configuration.

Basic CRs and configuration references are in the
[Operator repository](https://github.com/chizhang21/agentrally-operator/tree/main/examples).

## Prerequisites

Install AgentRally Operator and agent-sandbox Core and Extensions using the
[Operator quick start](https://github.com/chizhang21/agentrally-operator#quick-start).
For custom Helm settings, see the
[installation guide](https://github.com/chizhang21/agentrally-operator/blob/main/docs/installation.md).

The manifests use `arally.io/v1alpha1`.
Each application guide covers its storage and credential requirements.
Run its commands from this repository's root.

## Deployment order

1. Apply the AgentGroup and wait for `Ready`.
   The Operator creates its dedicated namespace.
2. Create any required Secrets and external PVCs in that namespace.
   The default HTTP API Agent skips this step.
3. Apply the AgentDefinition and AgentInstance.
4. Wait for the AgentInstance to become ready, then run the application's verification steps.

Keep credentials outside versioned files.
The optional HTTP Secret template contains placeholders only.
Use ignored `secrets/` files or your existing secret manager for real values.

## Use and verify

- [HTTP API Agent](http-api-agent/README.md#call-and-verify): forward its port, call `/healthz`
  and `/chat`, then [suspend and resume](http-api-agent/README.md#suspend-and-resume).
- [OpenClaw](openclaw/README.md#verify-and-configure): check Gateway health, configure the
  application and run the optional [lifecycle test](openclaw/README.md#run-the-openclaw-test).

## Lifecycle and GitOps

Select the manifests for one application as the GitOps source.
Exclude the optional HTTP Secret template from automatic reconciliation.
Provide Secrets through your chosen secret manager.
Keep image sources and test scripts outside the deployment scan.
Configure dependency ordering so Group namespace creation finishes before namespaced
resources are applied.

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
