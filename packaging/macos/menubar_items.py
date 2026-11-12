"""Print the menu bar status items (window layer 25) with owner PID and bounds. No screen capture."""
import sys
import objc
from Foundation import NSBundle

CG = {}
objc.loadBundleFunctions(NSBundle.bundleWithPath_("/System/Library/Frameworks/CoreGraphics.framework"), CG,
                         [("CGWindowListCopyWindowInfo", b"@II")])
wins = CG["CGWindowListCopyWindowInfo"](1 | 16, 0)  # on screen only, exclude desktop
want = int(sys.argv[1]) if len(sys.argv) > 1 else None  # owner PID filter (optional)
for w in wins:
    layer = int(w.get("kCGWindowLayer", 0))
    pid = int(w.get("kCGWindowOwnerPID", 0))
    if layer == 25 and (want is None or pid == want):
        b = w.get("kCGWindowBounds", {})
        print(f"pid={pid} owner={w.get('kCGWindowOwnerName')} layer={layer} x={b.get('X')} y={b.get('Y')} w={b.get('Width')} h={b.get('Height')}")
