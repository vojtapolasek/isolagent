## ADDED Requirements

### Requirement: Preset litellm configs for common backends
The project SHALL include preset litellm configuration files for common model backends: Vertex AI and local llama-swap.

#### Scenario: Vertex AI preset
- **WHEN** the user wants to use Claude via Vertex AI
- **THEN** a preset config exists at `litellm-presets/vertex-ai.yaml` that configures litellm to proxy to Vertex AI Claude models

#### Scenario: Local llama-swap preset
- **WHEN** the user wants to use a local llama-swap instance
- **THEN** a preset config exists at `litellm-presets/local-llama-swap.yaml` that configures litellm to proxy to a local OpenAI-compatible endpoint
