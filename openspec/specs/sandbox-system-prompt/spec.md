## ADDED Requirements

### Requirement: System prompt delivered via profile guest-files
Each profile MAY include a system prompt at `profiles/<name>/guest-files/root/.claude/CLAUDE.md`. The `guest-files/` directory mirrors the guest filesystem — files are deployed to matching absolute paths on the guest at session start.

#### Scenario: Profile includes system prompt
- **WHEN** a profile has `guest-files/root/.claude/CLAUDE.md`
- **THEN** the file is deployed to `/root/.claude/CLAUDE.md` on the guest before the agent starts

### Requirement: Prompt describes sandbox identity
The system prompt SHALL state that the agent is running as root inside an ephemeral QEMU virtual machine that is destroyed after the session.

#### Scenario: Agent reads environment identity
- **WHEN** Claude Code starts inside the sandbox VM
- **THEN** the CLAUDE.md tells it the VM is ephemeral and it is root

### Requirement: Prompt pushes autonomous posture
The system prompt SHALL instruct the agent to act decisively — prefer action over deliberation, do not ask for permission to run commands or modify files, do not hedge. It SHALL instruct the agent to ask the human only when genuinely unsure about intent or requirements.

#### Scenario: Agent encounters a destructive action
- **WHEN** the agent needs to delete files, install packages, or modify system configuration
- **THEN** it proceeds without asking for confirmation

#### Scenario: Agent is unsure about user intent
- **WHEN** the agent does not understand what the user wants
- **THEN** it asks for clarification

### Requirement: Prompt describes available resources
The system prompt SHALL state that the agent has unrestricted internet access, can install any packages, and has a libvirt connection available at `qemu+tcp://127.0.0.1:16509/system` bridged to the host's hypervisor.

#### Scenario: Agent needs to install a package
- **WHEN** the agent needs a tool not already installed
- **THEN** the CLAUDE.md has told it to install freely without hesitation

#### Scenario: Agent needs VM management
- **WHEN** the agent needs to interact with libvirt VMs
- **THEN** the CLAUDE.md provides the connection URI

### Requirement: Prompt specifies git checkpoint workflow
The system prompt SHALL instruct the agent to commit incrementally — small, meaningful commits as it works — and SHALL state that changes are synced back to the host on successful exit.

#### Scenario: Agent completes a coherent step
- **WHEN** the agent finishes a logical unit of work
- **THEN** it creates a git commit with a clear message explaining why

#### Scenario: Agent exits successfully
- **WHEN** the agent session ends with exit code 0
- **THEN** incremental commits are present in the working tree for sync-back

### Requirement: Prompt includes minimal guardrails
The system prompt SHALL prohibit the agent from rebooting or halting the VM, stopping or disabling sshd, and modifying the vsock-libvirt-bridge service.

#### Scenario: Agent considers rebooting
- **WHEN** the agent considers rebooting the VM
- **THEN** the CLAUDE.md tells it not to, because it would end the session

#### Scenario: Agent considers stopping sshd
- **WHEN** the agent considers stopping the SSH daemon
- **THEN** the CLAUDE.md tells it not to, because it would sever the connection

### Requirement: Prompt is project-agnostic
The system prompt SHALL NOT contain instructions specific to any particular project. Project-specific instructions SHALL be provided by each project's own CLAUDE.md.

#### Scenario: Different project rsynced into sandbox
- **WHEN** a different project is synced into the sandbox
- **THEN** the global CLAUDE.md is still applicable and contains no irrelevant instructions

