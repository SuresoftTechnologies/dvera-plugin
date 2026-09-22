# Releasing the MCP bundle

The MCP server in `scripts/` is distributed as an MCP Bundle (`.mcpb`) attached to
a GitHub release, and listed in the MCP registry through `server.json`.

`mcpb pack` is **not** reproducible - packing the same tree twice produces
different bytes, and so a different hash. The `fileSha256` in `server.json`
must therefore be taken from the exact file that is uploaded, never from an
earlier local build. A stale hash does not fail at publish time: the registry
does not check it, but MCP clients do, and they refuse the download.

## Why the `uv` server type

`manifest.json` declares `server.type: "uv"`, the one type where the MCPB spec
says the host provides Python ("Host application manages Python and
dependencies automatically", MCPB README). `python` expects an interpreter the
user already has, `node` would mean rewriting the server, and `binary` needs a
per-platform build.

Verified once: unpacking the bundle and running it made uv fetch its own
CPython into its managed directory rather than use an interpreter installed on
the machine.

`mcp_config` passes `--project`, not `--directory`. `--directory` makes the
child's working directory the bundle, and CT tools that default a source path
to the working directory would then scan the bundle instead of the user's
project.

## Steps

1. Bump `version` in `manifest.json`, `pyproject.toml`, `server.json`,
   `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and
   `SERVER_INFO` in `scripts/dvera-mcp.py` so all six agree. Below, `X.Y.Z` is
   that version.

   `SERVER_INFO` is the one clients read back over the wire, in the
   `initialize` response. It was missed in 0.1.1, which shipped announcing
   itself as `0.1.0`. Check it with:

   ```
   grep -rn 'X\.Y\.Z' manifest.json pyproject.toml server.json        .claude-plugin/plugin.json .claude-plugin/marketplace.json        scripts/dvera-mcp.py
   ```

2. Build the bundle. The output name must contain `mcp`, because the registry
   requires the package URL to contain that string:

   ```
   npx @anthropic-ai/mcpb pack . dvera-mcp.mcpb
   ```

   Pack from a clean tree. A local `uv run` leaves a `.venv/` behind, and while
   `.mcpbignore` excludes it, anything new that appears in the working tree
   ends up in the bundle unless it is listed there.

3. Create the release **as a draft** and upload the bundle. It has to stay a
   draft until step 7: publishing it is what triggers the registry workflow,
   and `server.json` does not hold the right hash yet.

   ```
   gh release create vX.Y.Z dvera-mcp.mcpb --draft --title vX.Y.Z --notes "..."
   ```

   Do not create the tag yourself. `vX.Y.Z` does not exist yet, and the draft
   targets the default branch; GitHub cuts the tag when the release is
   published in step 7, at whatever `main` points to then. Step 6 commits
   `server.json` before that, so the tag lands on it.

   Notes are read by people outside the company, so write them in English.

4. Download the asset back and hash **that** file, not the local build - the
   uploaded copy is the one clients fetch and check:

   ```
   gh release download vX.Y.Z --pattern dvera-mcp.mcpb --dir verify
   openssl dgst -sha256 verify/dvera-mcp.mcpb
   ```

   Put the digest in `server.json` as `packages[0].fileSha256`, and set
   `packages[0].identifier` to the asset's download URL for `vX.Y.Z`.

5. Check the manifest and the registry metadata:

   ```
   npx @anthropic-ai/mcpb validate manifest.json
   uvx check-jsonschema --schemafile https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json server.json
   mcp-publisher validate server.json
   ```

6. Commit and push the updated `server.json`. Nothing else: the tag does not
   exist yet, so there is no tag to move, and step 7 creates it on this commit.

   ```
   git add server.json && git commit -m "..." && git push origin main
   ```

   Confirm after step 7 that the tag really is on that commit:

   ```
   git ls-remote --tags origin vX.Y.Z
   ```

   The one case that needs more care is re-cutting a version whose tag already
   exists. Then the draft keeps the old tag, and the commit has to be moved
   deliberately rather than as a routine step - prefer a new version number.

7. Publish the release. That is the whole of it - publishing the draft fires
   `.github/workflows/publish-mcp-registry.yml`, which validates `server.json`
   and pushes it to the official registry.

   ```
   gh release edit vX.Y.Z --draft=false
   gh run watch $(gh run list --workflow publish-mcp-registry.yml --limit 1 --json databaseId --jq '.[0].databaseId')
   ```

   Confirm the entry landed:

   ```
   curl -s "https://registry.modelcontextprotocol.io/v0/servers?search=io.github.SuresoftTechnologies"
   ```

8. Check that Glama picked the release up, and do not assume it did.
   **Auto-Release** is switched on for the listing, so publishing the GitHub
   release in step 7 is supposed to build and publish there as well.

   It stopped doing that after 0.1.1 and nobody noticed for two releases: on
   2026-09-22 Glama still held `latestRelease 0.1.1`, having missed 0.1.2 and
   0.1.3. **Confirm the reflection on every release rather than trusting the
   setting.** The server page shows no version anywhere, so read
   `latestRelease.version` out of the page's embedded data, or check that the
   Schema tab lists the tools you expect.

   **Sync Glama's copy of the repository before building.** Glama builds from
   its own clone, not from the release you just cut, and a stale clone produces
   a build that carries the new version number over old code. That is what
   happened to 0.1.3: Glama published a `0.1.3` built from a 2026-09-18 commit,
   which reported zero tools, and the version could not be rebuilt afterwards -
   the admin page offers no way to delete or overwrite a published release. The
   only way out was to burn a version and cut 0.1.4. Sync first, build second.

   Open the [Dockerfile admin page][glama-dockerfile] and confirm the build
   succeeded and the new version is listed. The saved build spec only needs
   revisiting if the entry point moves:

   ```
   baseImage     debian:trixie-slim
   pythonVersion 3.14
   buildSteps    []
   cmdArguments  ["python", "scripts/dvera-mcp.py"]
   ```

   `buildSteps` is empty because the server has no third-party dependencies.
   Glama wraps the command with `mcp-proxy` itself.

   The sandbox has no CT, so the run reports one tool -
   `dvera_check_environment`, the built-in check that needs no product behind
   it. That is a pass: the server completes the handshake, and its
   `instructions` string says why the verification tools are missing. Where
   Auto-Release has not run, the same page has **Build & Release**, which does
   both by hand - after the sync above, never before it.

[glama-dockerfile]: https://glama.ai/mcp/servers/SuresoftTechnologies/dvera-plugin/admin/dockerfile

## Why the registry publish runs in CI

The workflow authenticates with GitHub Actions OIDC, and the registry grants
`io.github.<repository_owner>/*` straight from the token's `repository_owner`
claim. Because the repo is owned by `SuresoftTechnologies`, that is the
namespace it gets.

Do not replace this with `mcp-publisher login github` from a laptop. That path
was tried and does not work here: the device-code flow only ever returned
`io.github.<user>/*`, even for an org Owner with a public membership, because
the organisation restricts third-party OAuth apps. OIDC sidesteps the org's
app policy entirely and needs no Owner on hand at release time.

## Checking the bundle before release

`uv` resolves its own Python, so this runs without a system interpreter:

```
npx @anthropic-ai/mcpb unpack dvera-mcp.mcpb out
uv run --directory out scripts/dvera-mcp.py
```

Send it an `initialize` request on stdin. With CT installed it reports the
tools the installed CT declares; without CT it reports only
`dvera_check_environment` and stays connected rather than failing.
