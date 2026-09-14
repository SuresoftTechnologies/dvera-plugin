# Privacy Policy

This policy covers the DVERA plugin and the DVERA MCP server in this repository. It does
not cover CT itself, which is a separate Suresoft Technologies product with its own terms.

Last updated: 2026-09-10

## What is collected

**Nothing is collected by this software.**

The MCP server (`scripts/dvera-mcp.py`) runs on your machine. It makes no network requests
of its own: no telemetry, no analytics, no crash reporting, no update checks. Suresoft
Technologies receives no data as a result of you installing or running it.

The Skills are Markdown documents. They contain no executable code.

## How data is used and stored

The server does three things with data:

1. Reads the tool catalog file that ships inside your local CT installation, to build the
   list of available tools.
2. Passes the arguments of a tool call to CT's command-line entry point on the same
   machine.
3. Returns CT's response to the MCP client that asked for it.

It writes no files of its own and keeps no database, cache, or log. It stores no
credentials, tokens, or licence keys. Beyond the CT installation directory, the server
itself reads only the paths a tool call explicitly names.

CT is a separate matter. Each call starts a CT process, and that process reads and writes
what the requested operation needs: the active CT workspace, the project registered for
it, your source files, and the analysis, test, and report output CT keeps in its own
workspace. That work is CT's, under CT's own data handling, and it happens whether the
request came from DVERA or from the CT IDE.

## What leaves your machine

The server sends nothing. **Your MCP client does.**

When you use these tools, the client sends CT's responses to the AI model behind it so the
model can act on them. Depending on the tools you invoke, those responses may include
source file paths, function names, source code excerpts, test results, and coverage data.

That transfer is between you and your AI provider and is governed by their privacy policy —
for Claude, Anthropic's. Suresoft Technologies is not a party to it and does not receive
that data. Review your provider's terms before running these tools on code you may not
disclose.

## Third parties

Suresoft Technologies shares no data collected by this software, because none is collected.

Running the MCP server through an MCP Bundle may cause the host application to download a
Python runtime from that host's own distribution channel. That download is performed by the
host, not by this software.

## Retention

No data is retained by this software.

Data that CT records during analysis — workspaces, analysis output, test results, reports —
stays in CT's workspace on your machine under CT's own data handling. Removing it is done
through CT.

## Changes to this policy

Changes are made in this repository and are visible in its commit history.

## Contact

Questions about this policy, or about data handling in the CT product:
[bizcenter@suresofttech.com](mailto:bizcenter@suresofttech.com)

Suresoft Technologies, Inc. — <https://www.suresofttech.com>
