## Requirements

### Requirement: Shared socat process for VSOCK-to-libvirt forwarding
When `runtime.access_host_libvirt` is `true`, the session SHALL start a socat process on the host that listens on `VSOCK-LISTEN:16509` and forwards to `UNIX-CONNECT:/var/run/libvirt/libvirt-sock`. Multiple concurrent sessions SHALL share a single socat process.

#### Scenario: First session starts socat
- **WHEN** a session with `runtime.access_host_libvirt: true` starts and no socat process is running
- **THEN** a new socat process is spawned and its PID is recorded

#### Scenario: Second session reuses existing socat
- **WHEN** a session starts and a socat process from a prior session is already running
- **THEN** the existing socat process is reused (no new process spawned)

### Requirement: Flock-based coordination via PID file
The socat lifecycle SHALL be coordinated using file locking on a PID file at `$XDG_RUNTIME_DIR/isolagent/socat.pid`. Starting acquires an exclusive lock (with timeout), writes the PID, then downgrades to a shared lock. Each active session holds a shared lock for the session's lifetime.

#### Scenario: Exclusive lock acquired for startup
- **WHEN** a session needs to start or check the socat process
- **THEN** it acquires an exclusive lock on the PID file (with a configurable timeout, default 10s)
- **THEN** after starting or confirming socat, it downgrades to a shared lock

#### Scenario: Lock acquisition timeout
- **WHEN** the exclusive lock cannot be acquired within the timeout
- **THEN** a `SessionError` is raised identifying the lock file and timeout duration

### Requirement: Cleanup on last session teardown
On teardown, the session releases its shared lock. If no other sessions hold a shared lock (i.e., the exclusive lock can be acquired without blocking), the socat process SHALL be terminated via SIGTERM and the PID file removed.

#### Scenario: Last session cleans up socat
- **WHEN** the last session with `access_host_libvirt: true` tears down
- **THEN** the exclusive lock succeeds, socat is killed via SIGTERM, and the PID file is removed

#### Scenario: Other sessions still active
- **WHEN** a session tears down but other sessions still hold shared locks
- **THEN** the exclusive lock attempt fails (non-blocking) and socat is left running
