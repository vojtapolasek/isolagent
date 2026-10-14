# Spec Delta

## ADDED Requirements

### Requirement: Session cloud-init grows root filesystem
The session SHALL generate cloud-init user-data that grows the root partition into the enlarged disk and resizes the root filesystem to fill it (cloud-init `growpart` in automatic mode on the root device, plus root filesystem resize). Because each session's cloud-init meta-data uses a fresh unique instance-id, the growth modules SHALL execute on every session boot. The growth directives SHALL be idempotent: when the root filesystem already occupies the available space, boot proceeds unchanged.

#### Scenario: Root filesystem expands to configured size
- **WHEN** a session VM boots on an overlay whose virtual size exceeds the base image's root filesystem size
- **THEN** the root partition and root filesystem are grown and `df` inside the guest reports the configured size (within filesystem overhead)

#### Scenario: Growth is a no-op when disk equals base size
- **WHEN** a session VM boots on an overlay whose virtual size equals the base image's disk size
- **THEN** cloud-init growth modules complete without error and the root filesystem is unchanged

#### Scenario: Build-time user-data unaffected
- **WHEN** the builder generates its cloud-init user-data
- **THEN** the payload is unchanged by this capability (build VM disk growth is out of scope)
