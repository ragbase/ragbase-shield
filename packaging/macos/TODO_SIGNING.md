# macOS signing and notarisation: TODO

Status: **not done**. The `.pkg` built by `packaging/macos/build.sh` is unsigned. Nothing in this folder fakes a
signature. The script `packaging/macos/sign_and_notarize_TODO.sh` holds the exact commands below and exits with
code 2 ("TODO: certificate not configured") until the identities exist.

## 1. What the publisher needs to provide (one time)

| Item | Where | Notes |
|---|---|---|
| Apple Developer Program membership | developer.apple.com, 99 USD per year | Organisation account for "RAGbase" gives the Team ID |
| "Developer ID Application" certificate | Xcode > Settings > Accounts > Manage Certificates, or developer.apple.com > Certificates | Signs the Mach-O files (python, `.so`, `.dylib`) |
| "Developer ID Installer" certificate | same place | Signs the `.pkg` (productsign) |
| App-specific password for the Apple ID | appleid.apple.com > Sign-In and Security | Used once by `notarytool store-credentials` |

Then, once, on the build Mac:

```sh
xcrun notarytool store-credentials ragbase-notary \
  --apple-id <apple-id> --team-id <TEAMID> --password <app-specific-password>
security find-identity -v -p codesigning     # must list "Developer ID Application: ... (<TEAMID>)"
security find-identity -v                    # must list "Developer ID Installer: ... (<TEAMID>)"
```

## 2. Exact steps (what the script runs)

```sh
export SHIELD_APP_IDENTITY="Developer ID Application: RAGbase (TEAMID)"
export SHIELD_INSTALLER_IDENTITY="Developer ID Installer: RAGbase (TEAMID)"
export SHIELD_NOTARY_PROFILE=ragbase-notary

packaging/macos/build.sh                                  # unsigned payload + pkg
packaging/macos/sign_and_notarize_TODO.sh universal       # steps 2.1 to 2.4
```

2.1 Sign every Mach-O file of both runtimes, leaves first, with the hardened runtime and a secure timestamp:

```sh
find build/macos/payload-universal -type f \( -name '*.so' -o -name '*.dylib' \) -print0 \
 | while IFS= read -r -d '' f; do
     codesign --force --options runtime --timestamp --sign "$SHIELD_APP_IDENTITY" "$f"; done
find build/macos/payload-universal -type f -path '*/bin/python3.12' -print0 \
 | while IFS= read -r -d '' f; do
     codesign --force --options runtime --timestamp --entitlements packaging/macos/python.entitlements \
              --sign "$SHIELD_APP_IDENTITY" "$f"; done
```

`python.entitlements` holds two hardened-runtime exceptions:
`com.apple.security.cs.allow-unsigned-executable-memory` (cffi callbacks, pyobjc closures) and
`com.apple.security.cs.disable-library-validation` (NER packages installed later into `<app>/extras` by
`ragbase-shield ner install` are signed by their own teams or ad hoc).

2.2 Rewrite `MANIFEST.json` (the signatures change the bytes), run `check_payload.py`, repack with
`build.sh --reuse-payload`.

2.3 Sign the product archive:

```sh
productsign --timestamp --sign "$SHIELD_INSTALLER_IDENTITY" dist/RAGbase-Shield-<v>.pkg dist/RAGbase-Shield-<v>.pkg.signed
mv dist/RAGbase-Shield-<v>.pkg.signed dist/RAGbase-Shield-<v>.pkg
pkgutil --check-signature dist/RAGbase-Shield-<v>.pkg
```

2.4 Notarise, staple, assess:

```sh
xcrun notarytool submit dist/RAGbase-Shield-<v>.pkg --keychain-profile ragbase-notary --wait
xcrun stapler staple dist/RAGbase-Shield-<v>.pkg
xcrun stapler validate dist/RAGbase-Shield-<v>.pkg
spctl --assess --type install -vv dist/RAGbase-Shield-<v>.pkg   # expect: accepted, source=Notarized Developer ID
```

If notarisation is refused, read the log: `xcrun notarytool log <submission-id> --keychain-profile ragbase-notary`.
The usual causes are a Mach-O file left unsigned (a `.so` with an unusual name: list them with
`find build/macos/payload-universal -type f -exec file {} + | grep Mach-O`) or a missing timestamp.

## 3. Open point to settle on the first signed build

The `RAGbase Shield.app` shell is written by `ragbase-shield service install` at install time: a copy of the signed `python3.12`, an `Info.plist` and a `pyvenv.cfg` with an absolute path. The
copied binary keeps its own Developer ID signature, but the bundle around it is not signed, and that signature
was made for a standalone binary (no `Info.plist` bound to it). Expected to work (launchd runs the binary;
AMFI checks the binary's own code directory; nothing quarantines a file written by our own process), but to be
proved on the first signed build:

1. `codesign -dv --verbose=4 "<app>/RAGbase Shield.app/Contents/MacOS/RAGbase Shield"`: the Developer ID
   signature is intact.
2. Log out and in: the menu bar icon comes back (launchd started the shell).
3. With the keychain switched on (default), add a dossier: the keychain prompt names "RAGbase Shield"; choose
   "Always Allow"; restart the service; no second prompt.

If step 2 or 3 fails, the cleaner fix is a path-independent shell made AT BUILD TIME and signed as a bundle:
`Contents/lib` as a relative symlink to `../../runtime/lib` replaces `pyvenv.cfg` (Python then finds its
standard library from the executable location), so the whole `.app` can ship in the payload and be signed with
`codesign --options runtime --timestamp --entitlements python.entitlements --sign ... "RAGbase Shield.app"`.
`service_manager.app_dir()` would then also accept `sys.base_prefix` ending in `RAGbase Shield.app/Contents`.

## 4. Until then (unsigned phase): what the user sees

| macOS | What happens on double-click of the downloaded `.pkg` | What the user does |
|---|---|---|
| 15 and later | "Apple could not verify ..." with only "Done" and "Move to Trash" | System Settings > Privacy & Security > "Open Anyway" next to the RAGbase Shield message, then confirm (password or Touch ID of the Mac user, not an admin password for the install itself) |
| 13 and 14 | "cannot be opened because it is from an unidentified developer" | Right-click (or Control-click) the `.pkg` > Open > Open |

Screenshots to take for the install page (fresh account test, `packaging/TEST_PLAN_macos.md`): the refusal
dialog, the Privacy & Security "Open Anyway" button, the Installer welcome page, the "Install for me only"
destination, the conclusion page, the menu bar icon with its menu open.

Files placed by Installer carry no quarantine flag, so after the install nothing else asks for approval except
the keychain prompt (section 3) and the one-time "Background Items Added" notification of macOS 13 and later.
