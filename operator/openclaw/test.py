#!/usr/bin/env python3
"""Test OpenClaw in an existing disposable kind cluster running AgentRally."""
import argparse
import json
from pathlib import Path
import secrets
import subprocess
import time
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kubeconfig", type=Path, required=True)
    args = parser.parse_args()
    command = ["kubectl", "--kubeconfig", str(args.kubeconfig.resolve()), "--request-timeout=15s"]

    def kubectl(*arguments, body=None):
        result = subprocess.run(command + list(arguments), input=body, text=True, capture_output=True, timeout=420)
        if result.returncode:
            # Submitted credentials and application output stay out of errors.
            raise RuntimeError("kubectl failed: " + " ".join(arguments[:3]))
        return result.stdout.strip()

    context = kubectl("config", "current-context")
    if not context.startswith("kind-"):
        parser.error("use a disposable kind cluster; other contexts are rejected")

    group_name = "openclaw-test-" + uuid.uuid4().hex[:12]
    namespace = "agentrally-" + group_name
    directory = Path(__file__).resolve().parent

    def load(filename):
        obj = json.loads(kubectl("create", "--dry-run=client", "-f", str(directory / filename), "-o", "json"))
        if obj["kind"] == "AgentGroup":
            obj["metadata"]["name"] = group_name
            obj["spec"]["namespace"] = namespace
        else:
            obj["metadata"]["namespace"] = namespace
            if "agentGroupRef" in obj.get("spec", {}):
                obj["spec"]["agentGroupRef"]["name"] = group_name
        return obj

    def create(obj):
        kubectl("create", "-f", "-", body=json.dumps(obj))

    def get(resource, name, namespaced=True):
        flags = ["-n", namespace] if namespaced else []
        output = kubectl("get", resource, name, *flags, "--ignore-not-found", "-o", "json")
        return json.loads(output) if output else None

    def patch(resource, name, spec, namespaced=True):
        flags = ["-n", namespace] if namespaced else []
        kubectl("patch", resource, name, *flags, "--type=merge", "-p", json.dumps({"spec": spec}))

    def wait(label, check):
        deadline = time.monotonic() + 360
        while time.monotonic() < deadline:
            value = check()
            if value:
                return value
            time.sleep(2)
        raise RuntimeError("timed out: " + label)

    def ready(obj, condition="Ready"):
        return obj is not None and any(
            item["type"] == condition and item["status"] == "True"
            and item.get("observedGeneration") == obj["metadata"]["generation"]
            for item in obj.get("status", {}).get("conditions", [])
        )

    def ready_instance(revision=None, previous_pod=None):
        obj = get("agentinstance", "alice")
        if not ready(obj):
            return None
        status = obj["status"]
        return obj if (revision is None or status["definition"]["revision"] == revision) and (
            previous_pod is None or status["podUID"] != previous_pod) else None

    def execute(*arguments):
        instance = get("agentinstance", "alice")
        return kubectl("exec", "-n", namespace, instance["status"]["podName"], "--", "node", *arguments)

    def health():
        execute("-e", "(async()=>{for(const path of ['/healthz','/startupz']){"
                "const r=await fetch('http://127.0.0.1:18789'+path);if(r.status!==200)throw Error(path)}})()"
                ".catch(()=>process.exit(1))")
        assert json.loads(execute("/app/dist/index.js", "health", "--json", "--timeout", "10000"))["ok"]

    def retained():
        execute("-e", "const fs=require('node:fs');for(const dir of ['/workspace/.openclaw/workspace',"
                "'/workspace/.config/openclaw']){if(fs.readFileSync(dir+'/operator-canary','utf8')"
                "!=='retained-openclaw-state\\n')throw Error('state changed')}"
                "const cfg=JSON.parse(fs.readFileSync(process.env.OPENCLAW_CONFIG_PATH,'utf8'));"
                "if(cfg.gateway.mode!=='local'||cfg.gateway.controlUi.enabled!==false)throw Error('config changed')")
        pvc = get("pvc", "alice-state")
        instance = get("agentinstance", "alice")
        assert pvc["metadata"]["uid"] == pvc_uid == instance["status"]["workspace"]["uid"]
        assert not pvc["metadata"].get("ownerReferences")
        jobs = json.loads(execute("/app/dist/index.js", "cron", "list", "--all", "--json"))["jobs"]
        assert any(item["id"] == job_id and not item["enabled"] for item in jobs)

    create(load("group.yaml"))
    print("Testing in temporary Group:", group_name, flush=True)
    try:
        wait("Group readiness", lambda: ready(get("agentgroup", group_name, False)))
        create(load("workspace.yaml"))
        create({"apiVersion": "v1", "kind": "Secret", "metadata": {"name": "alice-gateway", "namespace": namespace},
                "stringData": {"token": secrets.token_hex(32)}})
        create(load("definition.yaml"))
        create(load("instance.yaml"))
        instance = wait("OpenClaw readiness", ready_instance)
        health()
        job = json.loads(execute("/app/dist/index.js", "cron", "add", "--name", "operator-retention",
                                "--every", "1h", "--command", "printf operator-retention", "--disabled", "--no-deliver", "--json"))
        assert job["id"] and not job["enabled"]
        job_id = job["id"]
        execute("-e", "const fs=require('node:fs');for(const dir of ['/workspace/.openclaw/workspace',"
                "'/workspace/.config/openclaw']){fs.mkdirSync(dir,{recursive:true});"
                "fs.writeFileSync(dir+'/operator-canary','retained-openclaw-state\\n')}")
        pvc_uid = get("pvc", "alice-state")["metadata"]["uid"]
        first = instance["status"]
        patch("agentinstance", "alice", {"operatingMode": "Suspended"})
        wait("suspension", lambda: ready(get("agentinstance", "alice"), "Suspended"))
        assert get("pod", first["podName"]) is None
        patch("agentinstance", "alice", {"operatingMode": None})
        instance = wait("resume", lambda: ready_instance(previous_pod=first["podUID"]))
        assert instance["status"]["sandboxName"] == first["sandboxName"]
        health()
        retained()
        print("Suspend/resume retained application state and scheduler job", flush=True)

        previous_revision = instance["status"]["definition"]["revision"]
        previous_pod = instance["status"]["podUID"]
        definition = get("agentdefinition", "openclaw")
        definition["spec"]["container"].setdefault("env", []).append({"name": "AGENTRALLY_OPENCLAW_TEST_REVISION", "value": "updated"})
        patch("agentdefinition", "openclaw", {"container": definition["spec"]["container"]})

        def published():
            obj = get("agentdefinition", "openclaw")
            return obj["status"]["currentRevision"] if ready(obj) and obj["status"]["currentRevision"] != previous_revision else None

        revision = wait("Definition publication", published)
        instance = get("agentinstance", "alice")
        assert instance["status"]["definition"]["revision"] == previous_revision
        assert instance["status"]["podUID"] == previous_pod
        assert execute("-e", "console.log(process.env.AGENTRALLY_OPENCLAW_TEST_REVISION||'original')") == "original"
        patch("agentinstance", "alice", {"revision": revision, "restartToken": "openclaw-test-updated"})
        instance = wait("replacement", lambda: ready_instance(revision, previous_pod))
        assert execute("-e", "console.log(process.env.AGENTRALLY_OPENCLAW_TEST_REVISION)") == "updated"
        health()
        retained()
        patch("agentgroup", group_name, {"prewarming": {"replicas": 2}}, False)
        wait("Group policy update", lambda: ready(get("agentgroup", group_name, False)))
        pool = get("sandboxwarmpools.extensions.agents.x-k8s.io", instance["status"]["provisioning"]["poolName"])
        assert pool["spec"]["replicas"] == 0
        kubectl("delete", "agentinstance", "alice", "-n", namespace, "--wait=true", "--timeout=360s")
        pvc = get("pvc", "alice-state")
        assert pvc["metadata"]["uid"] == pvc_uid and not pvc["metadata"].get("ownerReferences")
        print("Replacement and Instance deletion retained the external PVC", flush=True)
    finally:
        # Execution must finish cleanup before its external PVC can be removed.
        kubectl("delete", "agentinstance", "alice", "-n", namespace, "--ignore-not-found", "--wait=true", "--timeout=360s")
        kubectl("delete", "agentdefinition", "openclaw", "-n", namespace, "--ignore-not-found", "--wait=true", "--timeout=360s")
        kubectl("delete", "pvc", "alice-state", "-n", namespace, "--ignore-not-found", "--wait=true", "--timeout=360s")
        kubectl("delete", "agentgroup", group_name, "--wait=true", "--timeout=360s")
    print("OpenClaw lifecycle passed")


if __name__ == "__main__":
    main()
