# Proposal

## Why

The disk the sandbox agent actually writes to is a qcow2 overlay with a hardcoded 20 GiB virtual size (`libvirt_helpers.create_overlay_volume`), and nothing grows the guest's root partition/filesystem into it — so inside the sandbox `df -h /` always reports roughly the base image size (~5 GiB for Fedora Cloud) regardless of the workload. Users cannot size the sandbox for their project (e.g., a large repo or a toolchain-heavy agent run that needs tens of gigabytes of scratch space), and profiles offer no knob for it.

## What Changes

- Add `runtime.disk` profile field (string with unit suffix, e.g. `"20G"`; default `"20G"`), parsed by a generalized size parser accepting `M`/`G`/`T`.
- The session overlay volume's virtual size is taken from `runtime.disk` instead of the hardcoded 20 GiB.
- Fail fast at session init when the configured size is smaller than the base image volume's virtual size (qcow2 overlays cannot be smaller than their backing image), with an error naming the minimum.
- The session cloud-init user-data gains partition/filesystem growth (`growpart` + `resize_rootfs`) so the root filesystem expands into the configured disk size on each session boot; the configured size equals the usable root filesystem (`df -h /`) inside the sandbox.
- `isolagent run` gains a `--disk` override flag alongside `--memory`/`--cpus`.
- Reference profile and docs (`docs/profiles.md`, `docs/sessions.md`) updated; the build-time disk ceiling (base image virtual size) is documented as out of scope.

## Capabilities

### New Capabilities

(None — this extends existing capabilities.)

### Modified Capabilities

- `profile-schema`: `runtime` section gains a `disk` field (string, default `"20G"`); invalid size strings fail validation.
- `cli-entrypoint`: `run` subcommand accepts `--disk` as a runtime override.
- `qemu-vm`: "Ephemeral overlay disk" requirement — overlay virtual size comes from `runtime.disk`; session init rejects sizes smaller than the base image volume's virtual size.
- `session-lifecycle`: "Init phase creates ephemeral resources" honors the configured disk size and performs the minimum-size check; "Simplified cloud-init user-data" scenario broadened to include filesystem-growth directives.
- `cloud-init-data-generation`: session user-data SHALL include root-partition growth and root-filesystem resize directives.

## Impact

- Code: `isolagent/profile_schema.json`, `isolagent/profile.py` (defaults + size validation), `isolagent/libvirt_helpers.py` (generalized size parser, overlay capacity parameter, base-size minimum check), `isolagent/session.py` (overlay capacity from profile, cloud-init user-data growth directives), `isolagent/cli.py` (`--disk` flag).
- Profiles: `profiles/reference/profile.yaml` (AGENTS.md requirement), possibly `profiles/example/profile.yaml` if present.
- Tests: unit tests for parser/schema/CLI/validation/cloud-config; one integration test asserting the guest's root filesystem reflects the configured size (also proves the Btrfs growpart/resizefs path on Fedora 44 Cloud).
- Docs: `docs/profiles.md`, `docs/sessions.md`; note on build-time capacity limitation.
- Compatibility: existing profiles without `runtime.disk` keep today's 20 GiB overlay capacity, but their root filesystem will now actually grow into it (intended behavior change, previously 5 GiB).
- Out of scope: build VM disk sizing / base image growth; host-side qcow2 allocation capping.
