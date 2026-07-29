## ADDED Requirements

### Requirement: Self-contained sections

Every documentation section under a heading SHALL be a complete thought that makes sense when read independently. Documentation SHALL NOT use phrases like "as mentioned above" or "see the previous section" to reference content in other sections. When a fact from another section is needed, it SHALL be restated directly.

#### Scenario: LLM reads a single section via grep
- **WHEN** an LLM extracts a single H2 or H3 section from a doc file
- **THEN** the section is understandable without reading any other section in the file

### Requirement: Explicit defaults and constraints

Every configurable field or option documented in `docs/` SHALL state its type, default value, and constraints inline. Documentation SHALL NOT leave defaults or types implied.

#### Scenario: Profile field documentation
- **WHEN** a reader looks up a profile field in docs/profiles.md
- **THEN** the field entry states the type (e.g., `string`, `integer`, `boolean`), the default value (e.g., `"4G"`, `null`, `true`), and any constraints (e.g., `minimum: 1`)

### Requirement: Minimal-then-full examples

Documentation covering structured configuration (profiles, playbooks) SHALL include a minimal working example followed by a full example showing all optional fields. The minimal example SHALL contain only required fields. The full example SHALL annotate each optional field with its default value. Docs that present progressive presets (e.g., litellm) satisfy this requirement through the preset progression itself.

#### Scenario: Profile documentation examples
- **WHEN** a reader looks at docs/profiles.md
- **THEN** they find a minimal YAML profile (only required fields) followed by a full YAML profile (all fields with defaults annotated), either inline or by reference to a canonical example file (e.g., `profiles/example/profile.yaml`)

### Requirement: Imperative voice

Documentation SHALL use imperative voice for instructions. Documentation SHALL NOT use passive constructions like "the image can be built by running" or hedging like "you might want to consider running."

#### Scenario: Command instructions
- **WHEN** a doc instructs the reader to run a command
- **THEN** it uses imperative form: "Run `isolagent build example`" not "You can build the image by running the build command"

### Requirement: Consistent heading hierarchy

All docs/ files SHALL use H2 (`##`) for major topics and H3 (`###`) for subtopics. No doc SHALL skip heading levels (e.g., jumping from H2 to H4). Heading text SHALL be specific and descriptive, not vague (e.g., "Configuring libvirt integration" not "Advanced options").

#### Scenario: Heading structure in a doc file
- **WHEN** a reader scans the heading structure of any file in docs/
- **THEN** all major topics are H2, all subtopics are H3, and no heading levels are skipped
