## ADDED Requirements

### Requirement: Validate domain XML against real libvirt
The test suite SHALL include an integration test that validates the output of `generate_domain_xml` against real libvirt by defining a persistent domain (via `conn.defineXMLFlags`) and immediately undefining it. This SHALL catch QEMU-driver-level errors (bus incompatibilities, unsupported device combinations) that ElementTree-based unit tests cannot detect.

#### Scenario: Valid domain XML accepted by libvirt
- **WHEN** `generate_domain_xml` produces XML with valid device configurations using a unique domain name from `generate_domain_name("xmltest")`
- **AND** the XML is passed to `conn.defineXMLFlags(xml, 0)`
- **THEN** libvirt accepts the XML without error
- **AND** the defined domain is immediately undefined via `domain.undefine()` in a try/finally block

### Requirement: Unit test asserts cdrom bus type
The existing `TestDomainXMLGeneration.test_cloud_init_iso_in_cdrom` unit test SHALL assert that the cdrom target uses `bus='sata'`, not `bus='virtio'`.

#### Scenario: Cdrom bus assertion
- **WHEN** `generate_domain_xml` is called and the output is parsed
- **THEN** the cdrom disk's `<target>` element has `bus='sata'`
- **AND** the cdrom disk's `<target>` element has `dev='sda'`

### Requirement: Storage pool operations tested against real libvirt
The `TestStoragePoolVolumeManagement` tests SHALL use real libvirt storage pool operations instead of mocks. Tests SHALL create volumes with distinctive names via `generate_domain_name` and clean up in try/finally.

#### Scenario: volume_exists with real pool
- **WHEN** a test volume is created in the default pool
- **THEN** `volume_exists` returns True for that volume name
- **AND** returns False after the volume is deleted

#### Scenario: delete_volume with real pool
- **WHEN** a test volume exists in the default pool
- **AND** `delete_volume` is called
- **THEN** the volume no longer exists in the pool

#### Scenario: create_overlay_volume with real pool
- **WHEN** a base volume exists in the default pool
- **AND** `create_overlay_volume` is called with a test overlay name
- **THEN** the overlay volume is created with a backingStore referencing the base volume
- **AND** the overlay volume is cleaned up after the test

### Requirement: Init phase tested against real libvirt
A `TestInitPhaseIntegration` class SHALL test overlay volume creation and cloud-init ISO creation against real libvirt. The existing `TestInitPhase` class retains mocked unit tests for fast feedback. Socat-related init behavior MAY remain mocked.

#### Scenario: Init creates real overlay volume
- **WHEN** `runner.init()` is called with a real libvirt connection and a base image volume present
- **THEN** an overlay volume is created in the default pool
- **AND** the overlay volume has a backingStore referencing the base image

#### Scenario: Init creates cloud-init ISO
- **WHEN** `runner.init()` is called
- **THEN** a cloud-init ISO file is created on disk
- **AND** the ISO contains user-data and meta-data files

### Requirement: Teardown volume cleanup tested against real libvirt
A `TestTeardownIntegration` class SHALL test overlay volume deletion against real libvirt resources. The existing `TestTeardown` class retains mocked unit tests for fast feedback. Tests SHALL create a real overlay volume (with a dummy base), then verify teardown actually removes it. Domain destruction SHALL remain mocked — transient domains (created via `createXML`) require real disk images to start, and the destroy lifecycle is already covered by end-to-end tests.

#### Scenario: Teardown deletes real overlay volume
- **WHEN** an overlay volume exists in the default pool
- **AND** `runner.teardown()` is called with a real libvirt connection
- **THEN** the overlay volume no longer exists in the pool
