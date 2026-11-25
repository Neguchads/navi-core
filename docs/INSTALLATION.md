# Offline installation and update

Bootstrap with an already reviewed Python environment: install the NAVI wheel
using normal pip in an isolated environment, then use the installed NAVI
commands to provision subsequent independent environments. The installer
requires a local wheel bundle including one NAVI wheel and all compatible
reviewed dependency wheels. It does not download or install an agent, alter
global PATH, resolve dependencies online or change existing environments.

Prepare a wheel-only SHA-256 manifest in the bundle (on Bash, for example
sha256sum ./*.whl > WHEELS.sha256). Obtain and review the expected manifest
digest separately. For the NAVI release wheel, verify GitHub provenance
with gh attestation verify WHEEL --repo Neguchads/navi-core before creating
the bundle. A digest of untrusted downloads does not prove authenticity;
independently review third-party dependencies and licenses.

    navi install --manifest /private/bundle/WHEELS.sha256 --manifest-sha256 EXPECTED --destination /private/envs/navi-0.6
    navi install --manifest /private/bundle/WHEELS.sha256 --manifest-sha256 EXPECTED --destination /private/envs/navi-0.6 --apply

The parent must already exist and be outside Git. Apply creates a new venv,
installs only exact wheel paths with --no-index --no-deps, checks installed
dependencies and checks the version. No shell or global config change.
Use the new environment's Python or activate it manually. Trust wheel code
as executable software. No sandbox is implied.

Update is the same offline operation under a new destination:

    navi update --manifest /private/new-bundle/WHEELS.sha256 --manifest-sha256 EXPECTED --destination /private/envs/navi-next --apply

Rollback by activating the old environment; it is not modified. A partial
installation remains for manual inspection if a command fails. No
automatic destructive cleanup or background update.

    navi uninstall --destination /private/envs/navi-0.6
    navi uninstall --destination /private/envs/navi-0.6 --apply

Removal requires the exact managed receipt and unchanged full file inventory.
Ordinary use may generate bytecode or other files; any drift requires
manual review, not forced removal. Run from a separate active environment
and ensure no concurrent process edits or uses the target. Project data and
private stores should never be inside the managed venv.

The CI smoke downloads reviewed-version fixture wheels in a separate
preparation step, then verifies actual offline installation, version,
dependency consistency and removal. The fixture manifest does not claim
independent third-party provenance or full production supply-chain review.
