## ADDED Requirements

### Requirement: Default interactive Claude Code session
The agent command is now configurable via `agent.command` in the profile, not hardcoded to Claude Code. The session module SHALL run the agent command inside tmux on the guest and attach the host SSH session to it.

#### Scenario: Agent from profile
- **WHEN** `isolagent run myprofile` is invoked and the profile has `agent.command: "claude --dangerously-skip-permissions"`
- **THEN** the agent runs in a tmux session on the guest with environment variables from `agent.env`
- **THEN** the host SSH session attaches to the tmux session via a retry-attach loop

#### Scenario: SSH connection drops during agent session
- **WHEN** the SSH connection drops while the agent is running in tmux
- **THEN** the host retry-attach loop detects the tmux session is still alive and re-attaches
- **THEN** teardown does not run until the agent finishes and the tmux session disappears

#### Scenario: Custom agent
- **WHEN** the profile has `agent.command: "opencode"`
- **THEN** opencode runs in the tmux session instead of Claude Code

### Requirement: Shell escape hatch
Shell mode is accessed via `isolagent run myprofile --shell`. The user gets an interactive SSH shell at the project working directory. Shell mode bypasses tmux entirely — SSH runs directly with `-t` for PTY allocation. `--output-mode` is not required in shell mode and output extraction is skipped on teardown (the `run()` method returns immediately after the SSH session ends).

#### Scenario: Shell mode
- **WHEN** `isolagent run myprofile --shell` is invoked
- **THEN** the user gets an interactive SSH shell at `/isolagent/project/` with `agent.env` variables set via inline `env KEY=VALUE` syntax

#### Scenario: Shell mode does not require output mode
- **WHEN** `isolagent run myprofile --shell` is invoked without `--output-mode`
- **THEN** the CLI does not raise an error (unlike agent mode which requires `--output-mode`)

#### Scenario: Shell mode skips tmux and output extraction
- **WHEN** a shell session ends
- **THEN** no tmux session is created, no output extraction runs, and teardown proceeds directly to cleanup
