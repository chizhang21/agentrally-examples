# Resident OpenClaw assistant

Run the commands below from the repository root.

This AgentDefinition references Alice's gateway Secret; its AgentInstance binds Alice's
retained PVC.

Application conversations stay inside OpenClaw.

Instances of one definition share its credential references.
For another user with different credentials, create a separate definition referencing
that user's Secret and an instance with its own PVC.
There is no per-instance environment override.

This example pins the official `2026.10.4` image.
Paths and the LAN listener follow its
[Compose configuration](https://github.com/openclaw/openclaw/blob/v2026.10.4/docker-compose.yml).

Startup/readiness use `/startupz`; liveness uses `/healthz`, following the
[versioned probe guidance](https://github.com/openclaw/openclaw/blob/v2026.10.4/docs/install/docker.md#health-checks).
The probes allow five seconds for a response; the default one-second timeout was
exceeded during live CLI activity.

The writable HOME also retains `.config/openclaw` credentials.
`/tmp` is ephemeral.

## Install

A default filesystem StorageClass must support the image UID/GID 1000.
Configure `workspace.yaml` if another class is needed.

Install agent-sandbox Core and Extensions before the Operator.
Then:

```sh
kubectl apply -f operator/openclaw/group.yaml && kubectl wait agentgroup/openclaw --for=condition=Ready --timeout=120s
# Supply a private token file; do not commit it.
kubectl -n agentrally-openclaw create secret generic alice-gateway --from-file=token=/path/to/token
kubectl apply -f operator/openclaw/workspace.yaml -f operator/openclaw/definition.yaml -f operator/openclaw/instance.yaml
```

On an empty workspace, the startup command writes a minimal local Gateway config with
Control UI disabled, then replaces the shell with OpenClaw.
Existing config is left intact.

Complete provider/channel onboarding using the application's CLI in the reported
`status.podName`.
Before enabling Control UI, configure its allowed origins and pairing: the
[versioned Gateway startup check](https://github.com/openclaw/openclaw/blob/v2026.10.4/src/gateway/server-runtime-config.ts)
requires explicit origins for a non-loopback UI.

This example creates no public route.
Kubernetes readiness does not establish successful channel login or model calls.

## Upgrade and retain state

Update the image and apply [definition.yaml](definition.yaml).
Wait for the Definition's current-generation `Ready` condition, then read
`status.currentRevision`.
Set `spec.revision` to that hash and change `spec.restartToken` in
[instance.yaml](instance.yaml), then apply it.
For example, use `upgrade-1` as the token.
A restart without a revision change retains the accepted configuration.

Use a unique token for each restart.
When a GitOps controller owns the deployment, change these manifests in Git
and let it reconcile them in the same readiness order.

For reproducible artifacts, pin an image digest; revision pinning captures
configuration, not mutable image tags or Secret contents.

Back up application state before upgrades that migrate its schema.

The external PVC survives replacement and instance deletion.
The Operator records its UID and rejects same-name replacement.
Delete it explicitly when its data is no longer needed.
Never attach the same user PVC to multiple independent assistants.
The example enables `workspace.exclusive` to reserve its PVC until Instance deletion.
Competing bindings report `WorkspaceInUse` before allocation.

Delete the instance and wait for execution cleanup before deleting its definition.
Retaining the PVC also requires retaining its namespace.
Group deletion waits for remaining PVCs.
See [deletion and data retention](https://github.com/chizhang21/agentrally-operator/blob/main/docs/agent-definitions.md#delete).

Existing-workspace allocations enforce zero spares even if Group policy changes; channel
consumers and application cron jobs must not run in unassigned replicas.

Suspend stops OpenClaw, including its cron jobs.
Resume restarts the process with retained files; the Operator does not buffer messages
or wake it on demand.

## Run the OpenClaw test

Use a disposable kind cluster with AgentRally Operator, agent-sandbox Core/Extensions
and a default filesystem StorageClass already installed.
See the Operator's [installation guide](https://github.com/chizhang21/agentrally-operator/blob/main/docs/installation.md).
The cluster nodes must be able to pull the image selected in this example.

From this repository root:

```sh
python3 operator/openclaw/test.py --kubeconfig /path/to/disposable-kind-kubeconfig
```

The test requires Python 3 and kubectl.
It rejects non-kind contexts and creates a uniquely named temporary Group and namespace.
It uses the manifests in this directory and generates a temporary gateway token.
It deletes its test resources afterward; the caller owns cluster setup and teardown.

The test checks HTTP probes, authenticated health RPC and a disabled scheduler job.
It verifies retained files, config, scheduler state and PVC identity after suspend/resume
and explicit execution replacement.
It also checks revision pinning, zero workspace spares and PVC retention after Instance deletion.

It does not test Kata, external channels, provider onboarding or live model inference.
