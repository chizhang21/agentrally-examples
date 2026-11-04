# AgentRally Examples

Deployable application examples for AgentRally components.
Each top-level directory contains examples for one component.

| Component | Examples |
| --- | --- |
| [Operator](operator/README.md) | HTTP API Agent and OpenClaw |

Start with [HTTP API Agent](operator/http-api-agent/README.md), a minimal runnable Agent
for verifying deployment, HTTP access and suspend/resume.
Its default mode returns a fixed response without model credentials.

Install [AgentRally Operator and its dependencies](https://github.com/chizhang21/agentrally-operator#quick-start)
first, then follow the [deployment order](operator/README.md#deployment-order).
Each application guide includes its configuration and verification steps.

```text
operator/
  README.md
  http-api-agent/
    image/
  openclaw/
```

## License

Project manifests and supporting code use the [Apache License 2.0](LICENSE).
Built applications and installed packages retain their own licenses.
