# Spec Delta

## MODIFIED Requirements

### Requirement: Runtime section defines session parameters
The `runtime` section SHALL contain: `access_host_libvirt` (boolean, default false), `libvirt_uri` (string, optional), `memory` (string, default "4G"), `cpus` (integer, default 4), `disk` (string, default "20G"). Output mode and output directory are CLI-only arguments on `isolagent run`, not part of the profile.

The `access_host_libvirt` field replaces the former `libvirt` field. When true, the session starts a host-side socat relay so the guest can reach the host's libvirtd via VSOCK.

The `libvirt_uri` field specifies which libvirt connection URI to use for VM management (e.g., `qemu:///session`). If omitted, defaults to `qemu:///system`. The `ISOLAGENT_LIBVIRT_URI` environment variable takes precedence over this field.

The `disk` field specifies the usable disk size for the session VM (overlay disk virtual size and grown root filesystem). It SHALL be a positive integer followed by the unit suffix `M`, `G`, or `T` (e.g., `"20G"`, `"512M"`, `"1T"`).

#### Scenario: Minimal runtime section
- **WHEN** the runtime section is empty or omitted
- **THEN** validation passes with `access_host_libvirt` defaulted to false, `libvirt_uri` unset, `memory` to "4G", `cpus` to 4, and `disk` to "20G"

#### Scenario: Valid disk value
- **WHEN** the runtime section contains `disk: "40G"`
- **THEN** validation passes with `disk` set to "40G"

#### Scenario: Invalid disk value
- **WHEN** the runtime section contains `disk: "big"` or `disk: "40"` (no unit suffix)
- **THEN** profile validation fails with an error identifying the invalid disk size format

#### Scenario: Host libvirt access enabled
- **WHEN** the runtime section contains `access_host_libvirt: true`
- **THEN** the session enables the VSOCK socat relay for host libvirtd access

#### Scenario: Custom libvirt URI
- **WHEN** the runtime section contains `libvirt_uri: "qemu:///session"`
- **THEN** the session connects to `qemu:///session` instead of `qemu:///system`

#### Scenario: Environment variable overrides profile URI
- **WHEN** the profile sets `libvirt_uri: "qemu:///session"` and `ISOLAGENT_LIBVIRT_URI=qemu+ssh://remote/system` is set
- **THEN** the session connects to `qemu+ssh://remote/system`
