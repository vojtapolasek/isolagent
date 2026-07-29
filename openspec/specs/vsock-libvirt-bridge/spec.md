## ADDED Requirements

### Requirement: Host-side vsock-to-libvirt relay
The session module SHALL start a socat process on the host that listens on vsock port 16509 and forwards connections to the libvirt Unix socket at `/var/run/libvirt/libvirt-sock`. Lifecycle is managed via flock on a PID file:

**Init (startup serialization):**
1. Open PID file, poll `LOCK_EX | LOCK_NB` every 0.2s up to a configurable timeout (default 10s); raise `SessionError` if the deadline expires
2. Read PID, check if process is alive
3. If dead or missing: start socat, write new PID
4. Downgrade to `LOCK_SH` (allows other sessions to proceed)
5. Hold `LOCK_SH` for session lifetime

**Teardown:**
1. Release `LOCK_SH` (close the fd)
2. Reopen PID file, attempt `LOCK_EX | LOCK_NB`
3. If acquired: kill socat, remove PID file
4. If failed: other sessions still hold shared locks, leave socat running

#### Scenario: First session starts socat
- **WHEN** a session with `runtime.access_host_libvirt: true` starts and no socat PID file exists (or the process is dead)
- **THEN** socat is started under exclusive lock, its PID is written, and the lock is downgraded to shared

#### Scenario: Subsequent session reuses socat
- **WHEN** a session with `runtime.access_host_libvirt: true` starts and socat is already running
- **THEN** the session acquires exclusive lock (serialized), confirms socat is alive, downgrades to shared

#### Scenario: Concurrent session startup
- **WHEN** two sessions with `runtime.access_host_libvirt: true` start simultaneously
- **THEN** one acquires the exclusive lock first and starts socat; the other polls until the first downgrades to shared, then sees socat is alive and takes its own shared lock

#### Scenario: Lock acquisition timeout
- **WHEN** a session cannot acquire the exclusive lock within the timeout period
- **THEN** the session raises `SessionError` with a message indicating lock acquisition timed out

#### Scenario: Last session stops socat
- **WHEN** a session tears down, releases its shared lock, and the exclusive lock attempt succeeds
- **THEN** socat is killed and the PID file is removed

#### Scenario: Other sessions still active
- **WHEN** a session tears down, releases its shared lock, and the exclusive lock attempt fails
- **THEN** socat is left running

### Requirement: Guest-side vsock-to-TCP relay
When a profile sets `runtime.access_host_libvirt: true`, the built image SHALL include a systemd unit (installed by the `libvirt-bridge` role) that forwards local TCP port 16509 to vsock CID 2 (host) port 16509. The unit is installed disabled; the session starts it on demand during setup.

#### Scenario: Session starts guest socat on demand
- **WHEN** the session calls `systemctl start vsock-libvirt-bridge` via SSH during setup
- **THEN** `socat TCP-LISTEN:16509,bind=127.0.0.1,reuseaddr,fork VSOCK-CONNECT:2:16509` is running

### Requirement: Transparent libvirt connectivity
python3-libvirt inside the guest SHALL connect to `qemu+tcp://127.0.0.1:16509/system` and reach the host's libvirtd without any special configuration.

#### Scenario: Guest connects to host libvirt
- **WHEN** the agent runs `virsh -c 'qemu+tcp://127.0.0.1:16509/system' list`
- **THEN** it returns the list of VMs managed by the host's libvirtd

#### Scenario: Guest provisions a VM on the host
- **WHEN** a workload inside the guest uses `qemu+tcp://127.0.0.1:16509/system` to define and start a VM
- **THEN** the VM is created and managed on the host's libvirtd
