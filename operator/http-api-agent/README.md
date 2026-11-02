# HTTP API Agent

A small [Pydantic AI](https://ai.pydantic.dev/) Agent served over HTTP.
The AgentRally example image is `ghcr.io/chizhang21/agentrally-demo-agent:v0.0.3`.
It packages the official Pydantic AI SDK on the official Python base image.
The HTTP application and container are maintained in this repository.
Run commands from this repository's root.

The default demo mode uses Pydantic AI's `TestModel` and returns a fixed response.
It makes no model requests and requires no credentials.
Real model mode accepts an OpenAI-compatible provider and requires a Bearer token.
No shell, browser or filesystem tools are registered.
The image runs as a non-root user.

## Deploy and call

Install [AgentRally Operator 0.0.3 and agent-sandbox](https://github.com/chizhang21/agentrally-operator/blob/v0.0.3/docs/installation.md) first.
The basic deployment needs no Gateway, PVC or RuntimeClass.

```sh
kubectl apply -f operator/http-api-agent/01-group.yaml && kubectl wait agentgroup/http-api-agent --for=condition=Ready --timeout=120s
kubectl apply -f operator/http-api-agent/04-agent-definition.yaml -f operator/http-api-agent/04-agent.yaml && kubectl -n agentrally-http-api-agent wait agentinstance/http-api-agent --for=condition=Ready --timeout=300s
pod=$(kubectl -n agentrally-http-api-agent get agentinstance http-api-agent -o jsonpath='{.status.podName}')
kubectl -n agentrally-http-api-agent port-forward "pod/$pod" 18080:8080
```

Keep port-forward running and call the Agent from another terminal:

```sh
curl -fsS http://127.0.0.1:18080/healthz
curl -fsS http://127.0.0.1:18080/chat -H 'Content-Type: application/json' --data '{"message":"Hello"}'
```

The chat response is:

```json
{"response":"AgentRally demo agent is ready.","mode":"demo"}
```

`/healthz` reports process health and mode.
It does not test provider credentials or model availability.
The demo keeps no conversation history or files.

## Connect a model

Copy the Secret template before supplying credentials:

```sh
mkdir -p secrets
cp operator/http-api-agent/02-agent-secret.yaml secrets/http-api-agent-credentials.yaml
```

Fill in that private copy with your model API key and a separate Agent API token.
Apply it in the Group namespace.
Uncomment `container.env` and `modelProvider` in [04-agent-definition.yaml](04-agent-definition.yaml).
Set the provider URL and model name, then apply the Definition.
Wait for its current-generation `Ready` condition and copy `status.currentRevision`.
Set the Instance's `spec.revision` to that hash and change `spec.restartToken` in the same update.
Apply the Instance and wait for `Ready`.

Model mode rejects startup without an Agent API token and model name.
Call `/chat` with `Authorization: Bearer <your-agent-api-token>`.
Requests are limited to 4096 characters, and model output is limited to 256 tokens.
Provider failures return a generic error without provider responses or credentials.
Keep provider keys and Agent tokens in Secrets, outside versioned manifests.

## Lifecycle and cleanup

Add `spec.operatingMode: Suspended` to the Instance and apply it to stop execution.
Remove the field and apply again to resume.
Read the new Pod name and restart port-forward after resuming.
For GitOps, make these changes in Git.

Delete the Instance before its Definition and Group:

```sh
kubectl delete -f operator/http-api-agent/04-agent.yaml --timeout=300s
kubectl delete -f operator/http-api-agent/04-agent-definition.yaml --timeout=120s
kubectl delete -f operator/http-api-agent/01-group.yaml --timeout=300s
```

Group deletion also removes its namespace and any supplied Secrets.

## Image source and publication

Source and hashed dependencies are in [image/](image/).
Build locally:

```sh
docker build -f operator/http-api-agent/image/Containerfile -t ghcr.io/YOUR_GITHUB_USER/agentrally-demo-agent:v0.0.3 .
```

The [demo image workflow](../../.github/workflows/demo-agent.yml) audits dependencies,
checks startup and authentication without model access, then publishes to GHCR.
Tag this repository with `v0.0.3`, or dispatch that workflow with version `0.0.3`.
The Operator's image and Chart have their own release workflow.
Set the GHCR package visibility to **Public** for anonymous access.
Use a versioned image or digest in deployments.

To refresh dependency locks:

```sh
uv pip compile --python-version 3.13 --no-header --no-annotate --generate-hashes operator/http-api-agent/image/requirements.in --output-file operator/http-api-agent/image/requirements.txt
```
