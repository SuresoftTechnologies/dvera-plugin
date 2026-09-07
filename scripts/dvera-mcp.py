#!/usr/bin/env python3
"""DVERA MCP server - exposes CT's verification tools over stdio MCP.

Design constraint: this script must not import or vendor CT product code.
It touches the installed product in exactly two supported ways:

  1. reads ``resources/mcp-tools.json`` - a declarative tool catalog shipped
     with the CT MCP bundle (data, not code)
  2. runs ``scripts/ct_tool.py call <tool> --json @-`` as a subprocess - the
     product's own command-line entry point

(It also prefers the interpreter CT ships, which is a third, path-level
dependency on the install layout - see ``find_python``.)

This script keeps nothing of its own running: each tool call is a short-lived
subprocess. CT does keep a helper of its own alive between calls and retires it
when idle - that lifetime belongs to the product, not to this server.

Without a CT install this process does NOT fail. It answers the handshake and
reports zero tools, so machines without CT see the DVERA Skills only, with no
connection error.

Env overrides:
  CT_HOME  CT install dir (default: platform standard path)
"""
import glob
import json
import os
import queue
import re
import subprocess
import sys
import threading

# Versions this server implements. The newest is offered when a client asks
# for something outside the list.
SUPPORTED_PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
SERVER_INFO = {"name": "dvera-mcp", "version": "0.1.0"}
CALL_TIMEOUT_SEC = 900  # ct_tool.py's own default for the tool itself is 600

NO_CT_MESSAGE = (
    "CT is not available on this machine, so DVERA exposes no MCP tools. "
    "The DVERA Skills still work for guidance. To enable the tools, install "
    "CT 2026.06 or later and set CT_HOME if it is not in the default location."
)


def ensure_utf8_stdio():
    """Pin stdio to UTF-8, whatever the console code page is.

    MCP stdio messages are UTF-8, but on a Korean Windows the pipes come up as
    cp949 unless python was started with -X utf8. Decoding a tool argument
    such as a Korean project name under cp949 turns it into lone surrogates,
    which then blow up inside CT with a UnicodeEncodeError. The host decides
    how this process is launched, so it cannot be left to the launch flags.
    """
    for name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        if (getattr(stream, "encoding", "") or "").lower().replace("_", "-") == "utf-8":
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError, AttributeError):
            continue


# --------------------------------------------------------------------------
# locating the product
# --------------------------------------------------------------------------

def find_ct_home():
    """Return the CT install directory, or None when CT is not installed."""
    override = os.environ.get("CT_HOME")
    if override:
        return override if os.path.isdir(override) else None
    cands = ([r"C:\Program Files\Suresoft\CT 2026"] if sys.platform == "win32"
             else [os.path.expanduser("~/Suresoft/CT 2026")])
    for c in cands:
        if os.path.isdir(c):
            return c
    return None


def _version_key(path):
    """Sort key over the numeric parts of a bundle directory name.

    Plain string ordering would rank ``_1.10`` below ``_1.9``.
    """
    return [int(n) for n in re.findall(r"\d+", os.path.basename(path))]


def find_bundle(home):
    """Return the newest CT MCP bundle dir, or None when the bundle is absent.

    Found by the command-line tool it has to contain, not by the bundle's own
    identifier: the identifier is an internal detail, while the tool's path is
    the documented way in.
    """
    hits = glob.glob(os.path.join(home, "plugins", "*", "scripts", "ct_tool.py"))
    bundles = [os.path.dirname(os.path.dirname(h)) for h in hits]
    return max(bundles, key=_version_key) if bundles else None


def find_python(home):
    """Prefer the interpreter CT ships, so ct_tool.py runs on a known version."""
    bundled = os.path.join(home, "python",
                           "python.exe" if sys.platform == "win32" else "python3")
    return bundled if os.path.isfile(bundled) else sys.executable


# --------------------------------------------------------------------------
# tool catalog
# --------------------------------------------------------------------------

def _to_json_schema(spec):
    """Convert a catalog entry's ``params`` block into a JSON Schema object.

    The catalog abbreviates array element types as ``"items": "string"``;
    JSON Schema wants ``{"type": "string"}``. ``required`` is left out when
    empty rather than emitted as ``[]``, which is what CT's own server does.
    """
    props = {}
    for pname, pspec in (spec.get("params") or {}).items():
        prop = dict(pspec)
        if isinstance(prop.get("items"), str):
            prop["items"] = {"type": prop["items"]}
        props[pname] = prop
    schema = {"type": "object", "properties": props}
    required = list(spec.get("required") or [])
    if required:
        schema["required"] = required
    return schema


def _validate_catalog(catalog):
    """Reject a catalog we would otherwise turn into malformed tools.

    Unknown extra fields are allowed on purpose - the product may add some -
    but every field this code reads has to be the shape it expects, so that a
    format change degrades to zero tools with a stated reason instead of
    exposing an invalid tool list or crashing before the handshake.
    """
    if not isinstance(catalog, dict) or not catalog:
        raise ValueError("expected a non-empty object keyed by tool name")
    for name, spec in catalog.items():
        where = "entry %r" % name
        if not isinstance(spec, dict):
            raise ValueError("%s is not an object" % where)
        if not isinstance(spec.get("description", ""), str):
            raise ValueError("%s has a non-string 'description'" % where)
        params = spec.get("params", {})
        if not isinstance(params, dict):
            raise ValueError("%s has a non-object 'params'" % where)
        for pname, pspec in params.items():
            if not isinstance(pspec, dict):
                raise ValueError("%s parameter %r is not an object" % (where, pname))
        required = spec.get("required", [])
        if not isinstance(required, list):
            raise ValueError("%s has a non-list 'required'" % where)
        for entry in required:
            if not isinstance(entry, str):
                raise ValueError("%s lists a non-string in 'required'" % where)
            if entry not in params:
                raise ValueError("%s requires %r, which it does not declare"
                                 % (where, entry))


_JSON_TYPES = {
    "string": str, "number": (int, float), "integer": int,
    "boolean": bool, "array": list, "object": dict,
}


def validate_arguments(schema, arguments):
    """Return an error string when ``arguments`` do not fit ``schema``.

    Only presence and primitive type are checked - enough to keep a bad call
    from reaching CT, which reports a type mismatch as a raw Java exception
    rather than as a validation error.
    """
    if not isinstance(arguments, dict):
        return "arguments must be an object"
    for name in schema.get("required", []):
        if arguments.get(name) is None:
            return "missing required argument: %s" % name
    props = schema.get("properties", {})
    for name, value in arguments.items():
        expected = props.get(name, {}).get("type")
        py_type = _JSON_TYPES.get(expected)
        if py_type is None or value is None:
            continue
        # bool is an int subclass; a flag is not a number
        if isinstance(value, bool) != (expected == "boolean"):
            return "argument %s must be of type %s" % (name, expected)
        if not isinstance(value, py_type):
            return "argument %s must be of type %s" % (name, expected)
    return None


def load_tools(bundle):
    """Build the MCP tool list from the bundle's catalog resource."""
    path = os.path.join(bundle, "resources", "mcp-tools.json")
    with open(path, encoding="utf-8") as fh:
        catalog = json.load(fh)
    _validate_catalog(catalog)
    return [{"name": name,
             "description": spec.get("description", ""),
             "inputSchema": _to_json_schema(spec)}
            for name, spec in catalog.items()]


# --------------------------------------------------------------------------
# tool invocation
# --------------------------------------------------------------------------

def _extract_json(text):
    """Return the last top-level JSON object printed on ct_tool.py's stdout.

    The last one, not the first: anything the CLI prints ahead of its payload
    would otherwise be mistaken for the result.
    """
    decoder = json.JSONDecoder()
    found = None
    idx = text.find("{")
    while idx >= 0:
        try:
            obj, end = decoder.raw_decode(text[idx:])
        except ValueError:
            idx = text.find("{", idx + 1)
            continue
        if isinstance(obj, dict):
            found = obj
        idx = text.find("{", idx + end)
    return found


def call_tool(runtime, name, arguments):
    """Run one tool through ct_tool.py and return (payload_text, is_error)."""
    cmd = [runtime["python"], runtime["ct_tool"], "call", name, "--json", "@-"]
    try:
        proc = subprocess.run(
            cmd,
            input=json.dumps(arguments or {}),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=CALL_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        return ("ct_tool.py timed out after %ds calling %s."
                % (CALL_TIMEOUT_SEC, name), True)
    except OSError as exc:
        return ("could not run ct_tool.py (%s)." % exc, True)

    payload = _extract_json(proc.stdout or "")
    if payload is None:
        detail = (proc.stderr or proc.stdout or "").strip()[-2000:]
        return ("ct_tool.py returned no JSON (exit %d).\n%s"
                % (proc.returncode, detail), True)
    # ct_tool.py exits 0 exactly when the payload reports success, so a
    # mismatch means something went wrong outside the payload.
    is_error = not payload.get("success", False) or proc.returncode != 0
    return json.dumps(payload, ensure_ascii=False, indent=2), is_error


# --------------------------------------------------------------------------
# stdio MCP loop
# --------------------------------------------------------------------------

def negotiate_protocol(requested):
    """Answer with the client's version when we speak it, else our newest."""
    if requested in SUPPORTED_PROTOCOLS:
        return requested
    return SUPPORTED_PROTOCOLS[0]


def serve(tools, runtime, note=None):
    if note:
        print("dvera-mcp: %s" % note, file=sys.stderr, flush=True)

    write_lock = threading.Lock()

    def send(payload):
        line = json.dumps(payload) + "\n"
        with write_lock:  # the worker thread writes here too
            try:
                sys.stdout.write(line)
                sys.stdout.flush()
            except (OSError, ValueError):
                pass  # client already gone; the reply has nowhere to go

    def result(rid, value):
        send({"jsonrpc": "2.0", "id": rid, "result": value})

    def error(rid, code, message):
        send({"jsonrpc": "2.0", "id": rid,
              "error": {"code": code, "message": message}})

    # One worker, never more. CT serialises tool calls itself and assumes a
    # session works in a single workspace, so issuing calls concurrently here
    # would only stack up ct_tool.py processes waiting their turn. The queue
    # keeps the read loop free instead, which is what long calls need.
    pending = queue.Queue()
    closing = threading.Event()
    in_flight = {"rid": None}

    def worker():
        while True:
            item = pending.get()
            if item is None:  # sentinel: client is gone
                return
            rid, name, params = item
            in_flight["rid"] = rid
            try:
                text, is_error = call_tool(runtime, name, params.get("arguments"))
            except Exception as exc:  # noqa: BLE001 - the worker must not die
                text, is_error = ("calling %s failed: %s" % (name, exc), True)
            in_flight["rid"] = None
            result(rid, {"content": [{"type": "text", "text": text}],
                         "isError": is_error})
            if closing.is_set():
                # The client left while this call was running. It has been seen
                # through so CT was not abandoned mid-operation, but anything
                # still queued is work nobody is waiting for.
                return

    # Not a daemon: if the client disconnects mid-call, let CT finish rather
    # than orphaning a ct_tool.py subprocess partway through an operation.
    worker_thread = threading.Thread(target=worker)
    worker_thread.start()

    def cancel(rid):
        """Ask CT to abandon the call the client just gave up on."""
        if rid is None or rid != in_flight["rid"]:
            return
        try:
            subprocess.run([runtime["python"], runtime["ct_tool"], "cancel"],
                           capture_output=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            pass  # best effort; the call will still finish on its own

    try:
        _read_loop(sys.stdin, tools, pending, result, error, cancel)
    finally:
        closing.set()
        # However the loop ends - EOF, a decoding error, an unexpected raise -
        # the worker has to be released or this process never exits. The
        # worker stops itself after the call it is on, so queued work is not
        # started; draining here instead raced with the worker picking an item
        # up and silently dropped a reply the client had asked for.
        pending.put(None)
    return 0


def _read_loop(stream, tools, pending, result, error, cancel=None):
    for line in stream:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except ValueError:
            error(None, -32700, "Parse error: line is not valid JSON")
            continue
        if not isinstance(req, dict):
            error(None, -32600, "Invalid Request: expected a JSON object")
            continue

        method = req.get("method")
        if "id" not in req:  # notification - never answered
            if method == "notifications/cancelled" and cancel is not None:
                cancel((req.get("params") or {}).get("requestId"))
            continue
        rid = req.get("id")
        if not isinstance(method, str):
            error(rid, -32600, "Invalid Request: 'method' must be a string")
            continue
        params = req.get("params")
        if not isinstance(params, dict):
            params = {}

        if method == "initialize":
            payload = {
                "protocolVersion": negotiate_protocol(params.get("protocolVersion")),
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            }
            if not tools:
                payload["instructions"] = NO_CT_MESSAGE
            result(rid, payload)
        elif method == "tools/list":
            result(rid, {"tools": tools})
        elif method == "ping":
            result(rid, {})
        elif method == "tools/call":
            if not tools:
                error(rid, -32602, NO_CT_MESSAGE)
                continue
            name = params.get("name")
            tool = next((t for t in tools if t["name"] == name), None)
            if tool is None:
                error(rid, -32602, "Unknown tool: %s" % name)
                continue
            bad = validate_arguments(tool["inputSchema"], params.get("arguments") or {})
            if bad is not None:
                error(rid, -32602, "%s: %s" % (name, bad))
                continue
            # CT operations such as analysis or test execution run for minutes,
            # so hand the call to the worker and keep reading. Otherwise the
            # server answers nothing meanwhile and the client drops it.
            pending.put((rid, name, params))
        else:
            error(rid, -32601, "Method not found: %s" % method)


def main():
    ensure_utf8_stdio()
    home = find_ct_home()
    if home is None:
        return serve([], None, "no CT install found. Serving zero tools.")
    bundle = find_bundle(home)
    if bundle is None:
        return serve([], None, "CT at %s has no MCP bundle (needs 2026.06+). "
                               "Serving zero tools." % home)
    ct_tool = os.path.join(bundle, "scripts", "ct_tool.py")
    try:
        tools = load_tools(bundle)
    except Exception as exc:  # noqa: BLE001 - never fail before the handshake
        return serve([], None, "could not read the CT tool catalog (%s). "
                               "Serving zero tools." % exc)
    runtime = {"python": find_python(home), "ct_tool": ct_tool}
    return serve(tools, runtime, "CT found at %s; %d tools." % (home, len(tools)))


if __name__ == "__main__":
    sys.exit(main())
