## ADDED Requirements

### Requirement: litellm systemd user service
A systemd user service SHALL run litellm on `0.0.0.0:4000`, proxying requests to Vertex AI with credential injection. The service is enabled via `systemctl --user enable --now litellm`.

#### Scenario: Service running after enable
- **WHEN** the user enables and starts the service
- **THEN** `systemctl --user is-active litellm.service` returns `active`
- **THEN** `curl http://127.0.0.1:4000/health` returns a healthy status

### Requirement: Credential injection
litellm SHALL inject provider credentials (e.g., Google ADC for Vertex AI) into API requests. When litellm is used, the sandbox SHALL only know `ANTHROPIC_API_KEY=unused` and `ANTHROPIC_BASE_URL=http://192.168.122.1:4000`. litellm is optional — profiles that do not use litellm (e.g., opencode-quickstart) SHALL manage provider credentials directly within the agent.

#### Scenario: Sandbox makes API call via litellm
- **WHEN** an agent in the sandbox sends a request to `http://192.168.122.1:4000/v1/messages` with `ANTHROPIC_API_KEY=unused`
- **THEN** litellm replaces the credentials with the host's provider credentials and forwards to the configured backend

#### Scenario: API key not exposed when using litellm
- **WHEN** the sandbox inspects its environment variables in a litellm-backed profile
- **THEN** `ANTHROPIC_API_KEY` is `unused` and no real credentials are present

#### Scenario: Agent manages credentials directly
- **WHEN** a profile does not use litellm (no `ANTHROPIC_BASE_URL` pointing at the proxy)
- **THEN** the agent handles provider authentication itself (e.g., via opencode's `/connect` command)

### Requirement: Provider backend configuration
litellm SHALL be configured with one or more model backends (e.g., Vertex AI, OpenAI-compatible servers) using the appropriate credentials for each provider. Preset files in `litellm-presets/` provide starting-point configurations for common providers.

#### Scenario: Model routing
- **WHEN** a request arrives for a model name listed in `litellm_config.yaml`
- **THEN** litellm routes it to the configured provider backend

### Requirement: Drop unsupported parameters
The litellm config SHALL include `general_settings: drop_params: true` so that unsupported parameters from client requests are silently dropped rather than causing errors.

### Requirement: Extensible model configuration
The litellm config file SHALL support adding additional model backends (e.g., local llama-swap/OpenAI-compatible servers) without modifying the sandbox or the CLI.

#### Scenario: Adding local inference
- **WHEN** the user adds a local model entry to `litellm_config.yaml`
- **THEN** the sandbox can use the new model by changing `ANTHROPIC_BASE_URL` or model name without any other changes
