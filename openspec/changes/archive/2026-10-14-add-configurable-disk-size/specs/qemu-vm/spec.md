# Spec Delta

## MODIFIED Requirements

### Requirement: Ephemeral overlay disk
The overlay SHALL be created as a storage pool volume backed by the profile's base image volume. The overlay's virtual size SHALL be the resolved `runtime.disk` size (profile value or CLI override, default "20G"). If the resolved disk size is smaller than the base image volume's virtual size, session init SHALL fail with a `SessionError` stating the minimum allowed size, before the VM is started. The overlay volume SHALL be deleted via `vol.delete()` during teardown.

#### Scenario: Clean slate per run
- **WHEN** `isolagent run myprofile` launches a session
- **THEN** a new overlay pool volume is created backed by `isolagent-myprofile`
- **WHEN** the session ends
- **THEN** the overlay volume is deleted from the pool

#### Scenario: Overlay sized from profile
- **WHEN** a session starts for a profile with `runtime.disk: "40G"`
- **THEN** the overlay volume is created with a virtual size of 40 GiB

#### Scenario: Disk size smaller than base image
- **WHEN** a session starts with a resolved disk size smaller than the base image volume's virtual size
- **THEN** session init fails with a `SessionError` naming the minimum size and no domain is created

#### Scenario: Disk size equal to base image
- **WHEN** a session starts with a resolved disk size equal to the base image volume's virtual size
- **THEN** the overlay is created successfully and the guest's root filesystem remains at the base size
