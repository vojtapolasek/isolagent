## MODIFIED Requirements

### Requirement: Environment variables for unattended mode
Profile-defined `agent.env` variables SHALL be passed to the agent command's process environment via `env`. The `env` utility SHALL wrap the agent command, not the `cd` that precedes it, so that variables propagate to the agent process.

#### Scenario: Sandbox environment
- **WHEN** a profile defines `agent.env` with `IS_SANDBOX=1` and the agent command is launched via tmux
- **THEN** `IS_SANDBOX=1` is set in the agent process's environment

#### Scenario: Command structure
- **WHEN** a profile defines `agent.env` variables and `agent.command`
- **THEN** `_agent_tmux_cmd()` produces a command of the form `cd <workdir> && env VAR=val <command>`
