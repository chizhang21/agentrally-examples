# HTTP API Agent

A minimal runnable [Pydantic AI](https://ai.pydantic.dev/) Agent for verifying an
AgentRally installation: deploy it, call its HTTP API, then suspend and resume it.

The [AgentDefinition](04-agent-definition.yaml) uses a public image maintained in this
repository, built from the official Pydantic AI SDK and Python base image.
The default demo mode uses `TestModel` to return a fixed response without model credentials.
It keeps no conversation history or files.

The image runs as a non-root user and registers no shell, browser or filesystem tools.
Optional real model mode supports an OpenAI-compatible provider and requires a Bearer token.

## Prerequisites

Install [AgentRally Operator and agent-sandbox](https://github.com/chizhang21/agentrally-operator#quick-start).
The default example needs no model credentials, Gateway, PVC or additional RuntimeClass.

Get the manifests and run the remaining commands from this repository's root:

```sh
git clone https://github.com/chizhang21/agentrally-examples.git
cd agentrally-examples
```

## Deploy

Create the AgentGroup first so its namespace exists.
Then create the AgentDefinition and AgentInstance:

```sh
kubectl apply -f operator/http-api-agent/01-group.yaml && kubectl wait agentgroup/http-api-agent --for=condition=Ready --timeout=120s
kubectl apply -f operator/http-api-agent/04-agent-definition.yaml -f operator/http-api-agent/04-agent.yaml && kubectl -n agentrally-http-api-agent wait agentinstance/http-api-agent --for=condition=Ready --timeout=300s
```

## Call and verify

Forward the running Agent's port:

```sh
pod=$(kubectl -n agentrally-http-api-agent get agentinstance http-api-agent -o jsonpath='{.status.podName}')
kubectl -n agentrally-http-api-agent port-forward "pod/$pod" 18080:8080
```

Keep port-forward running and use another terminal:

```sh
curl -fsS http://127.0.0.1:18080/healthz
curl -fsS http://127.0.0.1:18080/chat -H 'Content-Type: application/json' --data '{"message":"Hello"}'
```

The health response is:

```json
{"status":"ok","mode":"demo"}
```

The chat response is:

```json
{"response":"AgentRally demo agent is ready.","mode":"demo"}
```

These responses verify the application and HTTP path.
They do not test a model provider.
If the AgentInstance does not become ready, inspect its Conditions and Events:

```sh
kubectl -n agentrally-http-api-agent describe agentinstance http-api-agent
```

## Suspend and resume

Check the Pod UID before suspending and again after resuming:

```sh
kubectl -n agentrally-http-api-agent get agentinstance http-api-agent -o jsonpath='{.status.podUID}{"\n"}'
```

The recreated Pod may have the same name, but its UID changes.
The current-generation `Suspended=True` condition confirms that the old Pod is gone.

Suspend:

```sh
kubectl -n agentrally-http-api-agent patch agentinstance http-api-agent --type=merge -p '{"spec":{"operatingMode":"Suspended"}}' && kubectl -n agentrally-http-api-agent wait agentinstance/http-api-agent --for=condition=Suspended --timeout=120s
```

Resume:

```sh
kubectl -n agentrally-http-api-agent patch agentinstance http-api-agent --type=merge -p '{"spec":{"operatingMode":null}}' && kubectl -n agentrally-http-api-agent wait agentinstance/http-api-agent --for=condition=Ready --timeout=300s
```

Repeat [Call and verify](#call-and-verify) with the new Pod to confirm the Agent responds again.
For GitOps, add or remove `spec.operatingMode: Suspended` in the manifest instead.

## Connect a model

Copy the Secret template before supplying credentials:

```sh
mkdir -p secrets
cp operator/http-api-agent/02-agent-secret.yaml secrets/http-api-agent-credentials.yaml
```

Fill in that private copy with your model API key and a separate Agent API token.
Apply it in the Group namespace:

```sh
kubectl apply -f secrets/http-api-agent-credentials.yaml
```

Uncomment `container.env` and `modelProvider` in [04-agent-definition.yaml](04-agent-definition.yaml).
Set the provider URL and model name, then apply the AgentDefinition.
Wait for its current-generation `Ready` condition and copy `status.currentRevision`.
Set the AgentInstance's `spec.revision` to that hash and change `spec.restartToken` in the same update.
Apply the AgentInstance and wait for `Ready`.

Model mode rejects startup without an Agent API token and model name.
Call `/chat` with `Authorization: Bearer <your-agent-api-token>`.
Requests are limited to 4096 characters, and model output is limited to 256 tokens.
Provider failures return a generic error without provider responses or credentials.
`/healthz` reports process health and mode.
It does not test provider credentials or model availability.

## Clean up

Delete the AgentInstance before its AgentDefinition and AgentGroup:

```sh
kubectl delete -f operator/http-api-agent/04-agent.yaml --timeout=300s
kubectl delete -f operator/http-api-agent/04-agent-definition.yaml --timeout=120s
kubectl delete -f operator/http-api-agent/01-group.yaml --timeout=300s
```

Group deletion also removes its namespace and any supplied Secrets.

## Image source and publication

Source and hashed dependencies are in [image/](image/).
To build locally:

```sh
docker build -f operator/http-api-agent/image/Containerfile -t ghcr.io/YOUR_GITHUB_USER/agentrally-demo-agent:v0.0.3 .
```

The [image workflow](../../.github/workflows/demo-agent.yml) audits dependencies,
checks startup and authentication without model access, then publishes to GHCR.
Push a version tag or dispatch the workflow with an image version.
The Agent image and the Operator are released independently.
Set the GHCR package visibility to **Public** for anonymous access.
The workflow summary provides a `tag@sha256:…` reference.
Copy it into the AgentDefinition when updating the example.
The digest fixes the image contents even if the tag changes.

To refresh dependency locks:

```sh
uv pip compile --python-version 3.13 --no-header --no-annotate --generate-hashes operator/http-api-agent/image/requirements.in --output-file operator/http-api-agent/image/requirements.txt
```
