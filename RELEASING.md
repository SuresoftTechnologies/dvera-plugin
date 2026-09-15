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
   `.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json` so all
   five agree. Below, `X.Y.Z` is that version.

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

6. Commit the updated `server.json`, then move the tag onto that commit so the
   release points at the metadata it describes:

   ```
   git tag -f vX.Y.Z && git push --force origin vX.Y.Z
   ```

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

8. Check that Glama picked the release up. **Auto-Release** is switched on for
   the listing, so publishing the GitHub release in step 7 also builds and
   publishes there - the same event drives both, and by then `server.json` and
   the tag are already settled.

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

   The sandbox has no CT, so the run reports zero tools. That is a pass, not a
   failure - the server completes the handshake and its `instructions` string
   says why the list is empty. If Auto-Release is ever turned off, the same page
   has **Build & Release**, which does both by hand.

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
tools the installed CT declares; without CT it reports zero and stays
connected rather than failing.
