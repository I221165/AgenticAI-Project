import sys
import os

# Insert the project root at the front of sys.path so that the local `mcp/`
# package takes precedence over the installed `mcp` SDK package.
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Evict any already-cached `mcp` module so the next import picks up the local one.
for _key in list(sys.modules.keys()):
    if _key == "mcp" or _key.startswith("mcp."):
        del sys.modules[_key]
