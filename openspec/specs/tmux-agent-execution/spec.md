## ADDED Requirements

### Requirement: Agent launched inside guest tmux session
In unattended mode, the session runner SHALL start the agent command inside a tmux session named `isolagent` in the guest VM via `tmux new-session -d -s isolagent '<command>'`. This allows the host to detach and re-attach to the agent's terminal.

#### Scenario: Agent started in tmux
- **WHEN** `runner.run()` is called in unattended mode
- **THEN** a detached tmux session named `isolagent` is created in the guest running the agent command

#### Scenario: Interactive mode bypasses tmux
- **WHEN** `runner.run()` is called with `--shell`
- **THEN** an interactive SSH session is opened directly without tmux

### Requirement: Host monitors agent via tmux has-session polling
After launching the tmux session, the host SHALL poll `tmux has-session -t isolagent` over SSH in a loop. Between polls, the host attaches to the tmux session so the user can observe the agent's output.

#### Scenario: Agent finishes normally
- **WHEN** the agent exits and the tmux session ends
- **THEN** `tmux has-session` returns a non-255 exit code and the polling loop exits

#### Scenario: Host attaches between polls
- **WHEN** `tmux has-session` confirms the session is alive
- **THEN** the host attaches to the tmux session via `tmux attach-session -t isolagent`

### Requirement: SSH transport failure triggers retry with backoff
When an SSH connection fails (exit code 255), the polling loop SHALL retry up to 10 consecutive times with a 2-second delay between attempts. A successful reconnect resets the failure counter. If 10 consecutive failures occur, the loop exits with a warning.

#### Scenario: Transient SSH failure recovered
- **WHEN** `tmux has-session` returns exit code 255 (SSH transport error)
- **THEN** the runner waits 2 seconds and retries
- **AND** on successful reconnect, the consecutive failure counter resets to zero

#### Scenario: Persistent SSH failure
- **WHEN** 10 consecutive SSH transport failures occur
- **THEN** the runner prints a warning and exits the polling loop

#### Scenario: Non-SSH failure exits immediately
- **WHEN** `tmux has-session` returns a non-zero, non-255 exit code
- **THEN** the polling loop exits immediately (the tmux session has ended)
