## ADDED Requirements

### Requirement: OS role vars carry base image SHA-256 hash
Each OS role's `vars/main.yaml` MAY include a `base_image_sha256` field containing a 64-character lowercase hex string. The builder reads this value alongside `base_image_url` to verify image integrity.

#### Scenario: OS role with sha256
- **WHEN** the OS role's `vars/main.yaml` includes `base_image_sha256`
- **THEN** the builder passes the hash to `download_base_image()` for verification

#### Scenario: OS role without sha256
- **WHEN** the OS role's `vars/main.yaml` omits `base_image_sha256`
- **THEN** the builder downloads the image without hash verification

### Requirement: download_base_image verifies SHA-256 when hash is provided
`download_base_image()` SHALL accept an optional `sha256` parameter. When provided, the function SHALL verify the SHA-256 hash of both cached and freshly downloaded images.

#### Scenario: Fresh download with matching hash
- **WHEN** `download_base_image(url, sha256=hash)` downloads a new image and the computed SHA-256 matches `hash`
- **THEN** the function SHALL return the cached path

#### Scenario: Fresh download with mismatched hash
- **WHEN** `download_base_image(url, sha256=hash)` downloads a new image and the computed SHA-256 does not match `hash`
- **THEN** the function SHALL delete the downloaded file and raise an error

#### Scenario: Cached image with matching hash
- **WHEN** `download_base_image(url, sha256=hash)` finds a cached image and its SHA-256 matches `hash`
- **THEN** the function SHALL return the cached path without re-downloading

#### Scenario: Cached image with mismatched hash
- **WHEN** `download_base_image(url, sha256=hash)` finds a cached image and its SHA-256 does not match `hash`
- **THEN** the function SHALL delete the cached file, re-download the image, and verify the new download

#### Scenario: No hash provided
- **WHEN** `download_base_image(url)` is called without a `sha256` parameter
- **THEN** the function SHALL behave as before (cache by filename, no verification)

### Requirement: Base image download with XDG-based caching
`download_base_image()` SHALL download cloud images from a URL and cache them in `$XDG_CACHE_HOME/isolagent/` (defaulting to `~/.cache/isolagent/`). The cached filename SHALL be derived from the URL's last path segment. If the image is already cached (and hash verification passes, if applicable), the download SHALL be skipped.

#### Scenario: First download
- **WHEN** `download_base_image(url)` is called and no cached file exists
- **THEN** the image is downloaded to `~/.cache/isolagent/<filename>` and the path is returned

#### Scenario: Image already cached
- **WHEN** `download_base_image(url)` is called and a cached file exists with a matching filename
- **THEN** the download is skipped and the cached path is returned

#### Scenario: Cache directory created on demand
- **WHEN** `download_base_image(url)` is called and `~/.cache/isolagent/` does not exist
- **THEN** the directory is created before downloading

#### Scenario: Download failure raises DownloadError
- **WHEN** hash verification fails after a fresh download
- **THEN** the downloaded file is deleted and a `DownloadError` is raised with the expected and actual hashes

### Requirement: download_base_image accepts optional downloads directory
`download_base_image()` SHALL accept an optional `downloads_dir` parameter that overrides the default XDG-based cache directory. This allows callers (such as test fixtures) to specify an absolute path.

#### Scenario: Custom downloads directory
- **WHEN** `download_base_image(url, downloads_dir=path)` is called
- **THEN** the image SHALL be downloaded to and cached in `path` instead of the default `$XDG_CACHE_HOME/isolagent/`

### Requirement: run_build passes sha256 from OS role to download
`run_build()` SHALL read `base_image_sha256` from the OS role's vars and pass it to `download_base_image()` for automatic integrity verification during builds.

#### Scenario: Build with OS role providing sha256
- **WHEN** `run_build()` loads the OS role vars and `base_image_sha256` is present
- **THEN** it SHALL pass the hash to `download_base_image()` for verification
