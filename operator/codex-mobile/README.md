# Codex Mobile agent

A password-protected coding agent with a retained workspace.
Build the image using the [Codex Mobile image recipe](image/README.md).
Run the commands below from the repository root.

## Deploy

Install [AgentRally and its dependencies](https://github.com/chizhang21/agentrally-operator/blob/main/docs/installation.md) first.
Build the image and replace `container.image` in [definition.yaml](definition.yaml).
Use a versioned tag or digest for a stable deployment.
For a private image, create a registry Secret in the Group namespace and add it to
`container.imagePullSecrets`.

The image runs as UID/GID 1000.
The default filesystem StorageClass must support that identity.
Set `storageClassName` in [workspace.yaml](workspace.yaml) if another class is needed.

From the repository root:

```sh
kubectl apply -f operator/codex-mobile/group.yaml && kubectl wait agentgroup/codex-mobile --for=condition=Ready --timeout=120s
# Supply a private password file; do not commit it.
kubectl -n agentrally-codex-mobile create secret generic developer-password --from-file=password=/path/to/password
kubectl apply -f operator/codex-mobile/workspace.yaml -f operator/codex-mobile/definition.yaml -f operator/codex-mobile/instance.yaml && kubectl -n agentrally-codex-mobile wait agentinstance/developer --for=condition=Ready --timeout=5m
```

The instance mounts the retained `developer-state` PVC at `/workspace`.
It reserves that PVC exclusively and uses zero unassigned spares.
The startup command creates `/workspace/projects` and starts Codex Mobile there.

For local access, read the Pod name and forward the web port:

```sh
pod=$(kubectl -n agentrally-codex-mobile get agentinstance developer -o jsonpath='{.status.podName}')
kubectl -n agentrally-codex-mobile port-forward "pod/$pod" 5900:5900
```

Open `http://127.0.0.1:5900` and use the password supplied in the Secret.
Complete model authentication through the application UI or CLI.
TCP readiness establishes that the server is listening; model access needs separate setup.

The manifests create no public route.
To add one, configure Group HTTPRoute defaults and `AgentInstance.spec.interaction` as
shown in the [Operator usage guide](https://github.com/chizhang21/agentrally-operator/blob/main/docs/usage.md#interaction-endpoint).

## Suspend, resume and upgrade

Add `spec.operatingMode: Suspended` to [instance.yaml](instance.yaml) and apply it.
Remove that field and apply again to resume.
The external PVC keeps projects and login state across both suspension and execution replacement.

To upgrade, update the image in [definition.yaml](definition.yaml) and set a new
`spec.restartToken` in [instance.yaml](instance.yaml).
Apply the definition and instance in that order.
Existing instances keep their accepted revision until explicit replacement.
Back up workspace data before application upgrades.

Keep the PVC and its Group when retaining data after deleting an instance.
See the [OpenClaw retained workspace example](../openclaw/README.md#upgrade-and-retain-state).
