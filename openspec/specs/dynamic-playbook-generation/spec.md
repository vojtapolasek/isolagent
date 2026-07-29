## Requirements

### Requirement: Builder generates playbooks dynamically
The builder SHALL generate a temporary Ansible playbook at build time from the assembled role list. No static playbook files SHALL be maintained.

#### Scenario: Generated playbook content
- **WHEN** the assembled role list is `[base, fedora, libvirt-bridge, agent-claude, example]`
- **THEN** the generated playbook targets `all` hosts, uses `become: true`, and lists those roles in that order

#### Scenario: Playbook is temporary
- **WHEN** the builder generates a playbook
- **THEN** the playbook file is written to a temporary directory and cleaned up after the build completes

### Requirement: Builder sets roles_path for role resolution
The builder SHALL pass the Ansible `roles_path` setting to include both the profile's local `roles/` directory (first) and the global `roles/` directory (second).

#### Scenario: Roles path includes profile-local and global
- **WHEN** building profile `example`
- **THEN** the Ansible provisioner is configured with `roles_path` containing `profiles/example/roles` and `roles/` (in that order)

#### Scenario: Profile with no local roles directory
- **WHEN** a profile has no `roles/` subdirectory
- **THEN** the `roles_path` contains only the global `roles/` directory

