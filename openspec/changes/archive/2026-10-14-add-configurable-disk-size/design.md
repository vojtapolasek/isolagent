# Design

## Context

See proposal.md — Why. Current state relevant to the approach:

- `create_overlay_volume()` (`isolagent/libvirt_helpers.py`) hardcodes a 20 GiB overlay capacity when creating the session qcow2 with a `<backingStore>` referencing the base image volume.
- `_parse_memory()` (`isolagent/libvirt_helpers.py`) parses `"4G"`/`"512M"` strings for the domain XML; memory is the only sized field today.
- Each session VM mounts a freshly generated cloud-init `cidata` ISO (`session.py`); its `instance-id` embeds the unique per-session domain name, so cloud-init config modules re-run every boot. The session user-data today carries only root-account settings.
- The base image volume is uploaded with `<capacity>` set to the downloaded file size (allocated size, e.g. ~557 MiB), which does **not** match the qcow2 header's virtual size (5 GiB for Fedora Cloud 44). Anything comparing "base size" must not trust that stale metadata.
- Fedora Cloud 44 Cloud-Base uses GPT with a Btrfs root filesystem.

## Goals / Non-Goals

**Goals:**
- One sized value (`runtime.disk`, CLI `--disk`) controls both the overlay virtual size and — via guest-side growth — the usable root filesystem.
- Misconfiguration (too small, malformed) fails fast at profile load or session init with actionable messages, never deep inside libvirt/qemu.
- Behavior is proven end-to-end by an integration test, since the growth chain (growpart → btrfs resize) is host-image dependent.

**Non-Goals:**
- Growing the base image or the build VM disk (design leaves a clean seam for it later: base-size probing is already factored out).
- Capping qcow2 *allocation* on the host (quota-style limits).
- Multi-disk or per-mount sizing.

## Decisions

### D1: Size parsing — one shared parser + schema regex
Rename `_parse_memory` to `parse_size()` returning `(value, unit)` and accept `M`, `G`, `T`. `memory` keeps working (its strings are a subset); disk uses the same function. Add a JSON-schema pattern on `runtime.disk`: `^[1-9][0-9]*[MGT]$`, so malformed values are rejected at profile validation with the field named. `runtime.memory`'s schema stays as-is (string) to avoid breaking existing profiles — its validation remains runtime-only, as today.
*Alternative considered:* integer GiB-only field — simpler, but inconsistent with `memory: "4G"` and forbids sub-GiB sizes.

### D2: Overlay capacity parameter
`create_overlay_volume(conn, name, backing_vol_name, capacity_bytes)` takes the resolved size; the 20 GiB default lives in profile defaults (`profile.py`), not in the libvirt helper. Callers: `session.py` resolves `runtime.disk` (after CLI override) → `parse_size` → bytes.
*Alternative considered:* keeping a default inside the helper — hides the source of truth and complicates testing.

### D3: Base minimum size probe
To enforce "disk ≥ base virtual size", probe the base volume's real virtual size by refreshing the storage pool (`pool.refresh(0)`) and reading `<capacity>` from the volume's `XMLDesc` — libvirt's pool refresh re-probes qcow2 headers, which is required because the uploaded volume's declared capacity is wrong (see Context). Note: the libvirt Python binding (12.x on this host) has no `virStorageVol.refresh()` and its `vol.info()` returns malformed tuples, so the volume XML is the reliable source. If probing fails or reports 0, raise `SessionError` (better a loud error than a qemu failure at boot). The check happens in the session init phase, before `create_overlay_volume`.
*Alternative considered:* shelling out to `qemu-img info` on `vol.path()` — breaks for non-local pool paths and adds a binary dependency; reading the qcow2 header in Python — needlessly low-level; storing the virtual size in OS role vars (`base_image_virtual_size`) — drifts when upstream images change.

### D4: Filesystem growth via cloud-init directives
Add to the session user-data only:
```yaml
growpart:
  mode: auto
  devices: ["/"]
resize_rootfs: true
```
`cc_growpart` grows the root partition (handles GPT layout), `cc_resizefs` resizes the filesystem in place (supports Btrfs, ext4, xfs). No cloud config in the build image changes; no runcmd scripts. Idempotent by design: both modules no-op when already grown.
*Alternative considered:* growing the partition offline at build time — cannot support per-run sizes; a growpart runcmd script — reimplements what cloud-init modules do with more failure surface.

### D5: CLI override plumbing
`--disk` on `run` flows through the existing `_apply_overrides()` in `cli.py` exactly like `--memory`: sets `profile["runtime"]["disk"]`. No validation in the CLI beyond what schema/profile-load provides (override values are re-validated: `parse_size` raises `SessionError` on malformed override input).

### D6: Integration test placement
Add to the existing integration tier (`tests/test_integration.py`, requires libvirt/KVM): run a session against the test profile with `--disk 8G`, SSH in, assert `df -B1g /` root size ≥ 7 GiB (slack for rounding/overhead). This simultaneously guards the qemu backing-store acceptance and the Fedora Btrfs growth chain.

## Risks / Trade-offs

- [Fedora 44 growpart/Btrfs chain silently no-ops] → D6 integration test asserts real `df` output; unit-test the user-data content so a regression in the payload is caught even where integration can't run.
- [libvirt probe reports stale/zero capacity for some backend] → explicit `SessionError` with remediation text; probe isolated in one helper so the strategy can be swapped (e.g., qcow2 header read) without touching callers.
- [Behavior change: existing profiles now grow root FS from ~5 GiB to 20 GiB default] → intended; documented in `docs/sessions.md`. Host qcow2 allocation grows only as written (sparse), so idle cost is nil.
- [Boot adds growpart/resizefs work on first sessions] → milliseconds-to-seconds one-time cost per session; overlay is fresh each run but growth of an already-sized FS is a no-op probe.
- [Overlay equal to base size yields no growth (qemu constraint)] → accepted; spec'd scenario makes it explicit rather than surprising.

## Migration Plan

No state migration: existing profiles keep validating (field optional, default matches current overlay size). After deploy, next session run grows the guest FS; nothing to rebuild. Rollback = revert commit; no persisted artifacts depend on the new behavior.
