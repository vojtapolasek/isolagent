# litellm Proxy (Optional)

litellm is an optional component that proxies model API traffic so the sandbox never sees real API keys. It is not required — agents like opencode can manage their own provider credentials directly (via `/connect`). Use litellm when you need API key isolation (keys never enter the sandbox) or model routing (multiple backends without guest changes).

## Why litellm

The sandbox runs AI agents with full permissions. If API keys are inside the guest, a compromised or misbehaving agent could exfiltrate them. litellm eliminates this risk: the guest only knows `ANTHROPIC_API_KEY=unused` and routes all traffic through the host proxy. The host injects real credentials (e.g., Google Cloud ADC for Vertex AI) at the proxy layer.

litellm also enables model routing. Different profiles can target different backends — Vertex AI, a local model server, or any OpenAI-compatible endpoint — without changing anything inside the guest.

If you are using the `opencode-quickstart` profile or another profile where the agent handles provider auth directly, you can skip litellm setup entirely.

## Prerequisites

Install litellm:

```shell
pip install litellm
```

## Setup

### Presets

Two presets are provided in `litellm-presets/`:

**vertex-ai.yaml** —

Routes Claude models through Google Vertex AI. Requires a GCP project with the Anthropic models enabled and Application Default Credentials configured on the host.

```yaml
model_list:
  - model_name: claude-opus-4-8
    litellm_params:
      model: vertex_ai/claude-opus-4-8
      vertex_project: YOUR_GCP_PROJECT
      vertex_location: global

  - model_name: claude-sonnet-5
    litellm_params:
      model: vertex_ai/claude-sonnet-5
      vertex_project: YOUR_GCP_PROJECT
      vertex_location: global

  - model_name: claude-haiku-4-5
    litellm_params:
      model: vertex_ai/claude-haiku-4-5
      vertex_project: YOUR_GCP_PROJECT
      vertex_location: global

general_settings:
  drop_params: true
```

**local-llama-swap.yaml** —

Routes to a local model server (llama-swap or any OpenAI-compatible server) running on port 8080. No cloud credentials needed.

```yaml
model_list:
  - model_name: local-model
    litellm_params:
      model: openai/your-model-name
      api_base: http://127.0.0.1:8080

general_settings:
  drop_params: true
```

### Create your config

Copy a preset and customize it:

```shell
cp litellm-presets/vertex-ai.yaml litellm_config.yaml
# Edit litellm_config.yaml — replace YOUR_GCP_PROJECT with your GCP project ID
```

Here is a full example `litellm_config.yaml` with all supported models:

```yaml
model_list:
  - model_name: claude-opus-4-6
    litellm_params:
      model: vertex_ai/claude-opus-4-6
      vertex_project: YOUR_PROJECT_ID
      vertex_location: global

  - model_name: claude-opus-4-8
    litellm_params:
      model: vertex_ai/claude-opus-4-8
      vertex_project: YOUR_PROJECT_ID
      vertex_location: global

  - model_name: claude-sonnet-4-6
    litellm_params:
      model: vertex_ai/claude-sonnet-4-6
      vertex_project: YOUR_PROJECT_ID
      vertex_location: global

  - model_name: claude-sonnet-5
    litellm_params:
      model: vertex_ai/claude-sonnet-5
      vertex_project: YOUR_PROJECT_ID
      vertex_location: global

  - model_name: claude-haiku-4-5
    litellm_params:
      model: vertex_ai/claude-haiku-4-5
      vertex_project: YOUR_PROJECT_ID
      vertex_location: global

  # Uncomment to add local inference via llama-swap or any OpenAI-compatible server:
  # - model_name: local-model
  #   litellm_params:
  #     model: openai/your-model-name
  #     api_base: http://127.0.0.1:8080

general_settings:
  drop_params: true
```

### Create the environment file

Create `litellm.env` with paths to your litellm binary and config:

| Variable | Required | Description |
|----------|----------|-------------|
| `LITELLM_BIN` | yes | Absolute path to the litellm binary |
| `LITELLM_CONFIG` | yes | Absolute path to `litellm_config.yaml` |
| `GOOGLE_APPLICATION_CREDENTIALS` | for Vertex AI | Absolute path to Google Cloud ADC credentials JSON |

```shell
LITELLM_BIN=/path/to/litellm
LITELLM_CONFIG=/path/to/litellm_config.yaml
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

### Install the systemd user service

```shell
cp litellm.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now litellm
```

The service file references `litellm.env` via `EnvironmentFile=`. Edit the `EnvironmentFile=` path in `~/.config/systemd/user/litellm.service` if your project is cloned to a different location than the default.

### Open the firewall for VM traffic

libvirt's default firewalld zone rejects connections from VMs to host services. Allow port 4000 so the sandbox can reach litellm.

libvirt recreates the `libvirt` zone each time libvirtd or the default network restarts, so a plain `firewall-cmd --add-port` won't persist. Use a libvirt network hook instead:

```shell
sudo tee /etc/libvirt/hooks/network <<'EOF'
#!/bin/bash
if [ "$1" = "default" ] && [ "$2" = "started" ]; then
    firewall-cmd --zone=libvirt --add-port=4000/tcp
fi
EOF
sudo chmod +x /etc/libvirt/hooks/network
```

Apply immediately without restarting libvirtd:

```shell
sudo firewall-cmd --zone=libvirt --add-port=4000/tcp
```

### Verify

```shell
curl http://localhost:4000/health
```

A successful response confirms litellm is running and accepting requests.

## Profile Configuration

Set `agent.env.ANTHROPIC_BASE_URL` in your profile to point at the libvirt default network gateway:

```yaml
agent:
  env:
    ANTHROPIC_BASE_URL: "http://192.168.122.1:4000"
    ANTHROPIC_API_KEY: "unused"
```

The `reference` profile (`profiles/reference/profile.yaml`) demonstrates this configuration.
