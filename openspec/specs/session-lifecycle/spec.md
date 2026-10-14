## Requirements

### Requirement: Session lifecycle phases
The `isolagent run` command SHALL execute four phases in order: init, setup, run, teardown. The teardown phase SHALL always execute regardless of errors in prior phases. The CLI SHALL install a SIGTERM handler that converts the signal to `SystemExit`, ensuring Python's `finally` blocks (and thus teardown) execute on process termination.

#### Scenario: Successful session
- **WHEN** `isolagent run myprofile` is invoked and all phases succeed
- **THEN** init creates the overlay and resources, setup boots the VM and provisions it, run executes the agent, and teardown extracts output and cleans up

#### Scenario: Error during setup
- **WHEN** QEMU fails to start or SSH never becomes available
- **THEN** teardown still runs, cleaning up the overlay and any started processes

#### Scenario: Error during run
- **WHEN** the agent command exits with a non-zero code
- **THEN** teardown still runs and output extraction is attempted

### Requirement: Init phase creates ephemeral resources
The init phase SHALL create an overlay as a storage pool volume (with `<backingStore>` referencing the base image volume) with virtual size equal to the resolved `runtime.disk` size, generate a unique domain name, create the cloud-init ISO with DHCP network configuration, and manage the shared socat process for libvirt bridging if `runtime.access_host_libvirt` is true (starting socat only if not already running). Before creating the overlay, the init phase SHALL verify the resolved disk size is not smaller than the base image volume's virtual size and fail with a `SessionError` naming the minimum size if it is. Slot allocation is no longer performed — libvirt handles IP assignment (DHCP) and VSOCK CID assignment (auto).

#### Scenario: Overlay creation
- **WHEN** init runs for profile `myprofile` with suffix `a1b2c3` and `runtime.disk` resolving to "20G"
- **THEN** a pool volume `isolagent-myprofile-a1b2c3-overlay` with virtual size 20 GiB is created backed by the `isolagent-myprofile` base volume

#### Scenario: Disk size below base image minimum
- **WHEN** init runs with a resolved disk size smaller than the base image volume's virtual size
- **THEN** init fails with a `SessionError` naming the minimum size before any overlay volume or domain is created

#### Scenario: Domain name generation
- **WHEN** init runs for profile `myprofile`
- **THEN** a unique domain name like `isolagent-myprofile-<suffix>` is generated

#### Scenario: Libvirt bridge start (first session)
- **WHEN** `runtime.access_host_libvirt` is true and no socat is running
- **THEN** init starts a host socat process and writes its PID to a PID file

#### Scenario: Libvirt bridge reuse (subsequent session)
- **WHEN** `runtime.access_host_libvirt` is true and socat is already running
- **THEN** init skips starting socat

#### Scenario: No libvirt
- **WHEN** `runtime.access_host_libvirt` is false
- **THEN** init does not interact with socat

### Requirement: Setup phase boots VM and provisions runtime
The setup phase SHALL create a transient libvirt domain via `conn.createXML()`, discover the guest IP via DHCP lease polling, wait for SSH, rsync the project into the guest, deploy guest files from the profile's `guest-files/` directory, and enable runtime services. SSH connections SHALL use "none" authentication without any key file or password. The SSH command SHALL include `-o IdentitiesOnly=yes` to prevent SSH from using agent-offered identity keys (ensuring "none" authentication is used). The session cloud-init user-data SHALL preserve root account state (`disable_root: false`, `lock_passwd: false`) and request root partition/filesystem growth, without any SSH key injection or sshd configuration.

#### Scenario: Domain creation
- **WHEN** setup runs
- **THEN** a transient domain is created with KVM, virtio networking on the `default` network, vsock with auto CID, and the overlay disk

#### Scenario: Guest IP discovery
- **WHEN** the domain boots and obtains a DHCP lease
- **THEN** setup discovers the guest IP by polling `domain.interfaceAddresses(VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE)`, falling back to `network.DHCPLeases(mac)` if needed

#### Scenario: SSH readiness
- **WHEN** the guest IP is discovered
- **THEN** setup polls SSH every second for up to 60 seconds before failing

#### Scenario: SSH without credentials
- **WHEN** setup polls or connects via SSH
- **THEN** the SSH command uses no `-i` key file flag and includes `-o IdentitiesOnly=yes`

#### Scenario: Project sync
- **WHEN** SSH is ready
- **THEN** `project.workdir` is rsynced to `/isolagent/project/` on the guest using SSH without key auth

#### Scenario: Guest file deployment
- **WHEN** the profile has a `guest-files/` subdirectory with files
- **THEN** each file is SCP'd to the guest at its mirrored path using SCP without key auth

#### Scenario: No guest files
- **WHEN** the profile has no `guest-files/` subdirectory
- **THEN** setup skips guest file deployment without error

#### Scenario: Libvirt guest service
- **WHEN** `runtime.access_host_libvirt` is true
- **THEN** the vsock-libvirt-bridge service is started on the guest

#### Scenario: Cloud-init user-data content
- **WHEN** the session generates cloud-init user-data
- **THEN** the user-data contains `disable_root: false` and `lock_passwd: false` for root and filesystem-growth directives, with no SSH keys or sshd runcmds

#### Scenario: Domain start failure
- **WHEN** `conn.createXML()` raises a libvirt error
- **THEN** the session raises `SessionError` with the libvirt error message

### Requirement: Run phase executes the agent
The run phase SHALL execute the agent command from `agent.command` with environment variables from `agent.env` passed inline using `env KEY=VALUE` syntax, inside tmux on the guest. After launching the tmux session, the run phase SHALL enter a reconnect loop that polls `tmux has-session` via SSH. The loop SHALL distinguish between SSH transport failures and clean tmux session exits by inspecting the SSH exit code: exit code 255 indicates an SSH transport failure and SHALL be retried up to 10 times with 2-second intervals; any other nonzero exit code indicates the remote `tmux has-session` command returned nonzero (session no longer exists) and SHALL cause the loop to break immediately without retrying or printing a warning.

#### Scenario: Agent in tmux with env vars
- **WHEN** `isolagent run myprofile` is invoked and `agent.env` has entries
- **THEN** the agent command runs as `env KEY1=val1 KEY2=val2 <agent.command>` in a tmux session on the guest

#### Scenario: Agent in tmux without env vars
- **WHEN** `isolagent run myprofile` is invoked and `agent.env` is empty
- **THEN** the agent command runs directly without an `env` prefix

#### Scenario: Shell mode
- **WHEN** `isolagent run myprofile --shell` is invoked
- **THEN** the user gets an interactive SSH shell at `/isolagent/project/` instead of the agent

#### Scenario: Clean agent exit
- **WHEN** the agent exits normally (e.g., via `/exit`) and the tmux session ends
- **THEN** `tmux has-session` returns nonzero via SSH with an exit code other than 255, and the reconnect loop breaks immediately without retrying or printing a warning

#### Scenario: SSH transport failure during reconnect
- **WHEN** the SSH connection fails during the reconnect loop (exit code 255)
- **THEN** the loop retries up to 10 times with 2-second intervals, printing "Warning: Lost connection to VM after 10 attempts" only if all retries are exhausted

#### Scenario: SSH transport recovers
- **WHEN** SSH fails transiently but recovers within the retry window
- **THEN** the loop reattaches to the tmux session and resets the failure counter

### Requirement: Teardown phase cleans up
The teardown phase SHALL extract output, destroy the libvirt domain (direct destroy, no graceful shutdown), delete the overlay pool volume via `vol.delete()`, release the socat shared lock (killing socat only if this is the last active session, checked via flock — release shared lock, attempt exclusive lock), and then remove ephemeral files (cloud-init directory, cloud-init ISO, console log).

#### Scenario: Clean teardown
- **WHEN** teardown runs after a successful session
- **THEN** output is extracted, the domain is destroyed, the overlay pool volume is deleted, and temp files are removed

#### Scenario: Partial teardown
- **WHEN** teardown runs after a domain crash (VM unreachable)
- **THEN** output extraction is skipped with a warning, but domain cleanup and file removal still proceed

#### Scenario: Teardown with other sessions holding shared locks
- **WHEN** teardown releases its shared lock and the exclusive lock attempt fails
- **THEN** socat is left running

#### Scenario: Teardown of last session
- **WHEN** teardown releases its shared lock and the exclusive lock attempt succeeds
- **THEN** socat is killed and the PID file is removed

### Requirement: Preflight checks
The session SHALL verify prerequisites before starting: libvirtd is reachable via `libvirt.open()` (using the configured URI), the `default` libvirt network is active, the `default` storage pool exists and is active, the base image volume `isolagent-<profile>` exists in the storage pool, and an ISO creation tool is available. Error messages SHALL provide clear remediation instructions.

#### Scenario: Missing image
- **WHEN** no volume named `isolagent-<profile>` exists in the storage pool
- **THEN** the session prints an error with instructions to run `isolagent build` first and exits

#### Scenario: libvirtd not reachable
- **WHEN** `libvirt.open()` fails
- **THEN** the session prints an error with instructions to start libvirtd and ensure the user has appropriate access

#### Scenario: Default network not active
- **WHEN** the `default` libvirt network is not active
- **THEN** the session prints an error with instructions to run `virsh net-start default`

#### Scenario: Default storage pool not found
- **WHEN** the `default` storage pool does not exist or is not active
- **THEN** the session prints an error with instructions to create and start the pool

#### Scenario: All prerequisites met
- **WHEN** libvirtd is reachable, the default network is active, the default pool is active, and the image volume exists
- **THEN** preflight passes
