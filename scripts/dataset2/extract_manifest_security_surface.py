#!/usr/bin/env python3

import sys
from pathlib import Path
from androguard.core.apk import APK

ANDROID_NS = "http://schemas.android.com/apk/res/android"


def attr(el, name):
    return el.get(f"{{{ANDROID_NS}}}{name}")


def is_exported(component):
    """
    Determine exported status according to Android rules.
    """
    exp = attr(component, "exported")

    if exp is not None:
        return exp.lower() == "true"

    # fallback rule (older Android behaviour)
    for child in component:
        if child.tag.endswith("intent-filter"):
            return True

    return False


def write_list(path, items):
    path.write_text("\n".join(sorted(set(items))) + ("\n" if items else ""), encoding="utf-8")


def main():

    if len(sys.argv) != 3:
        print("Usage: script.py <apk> <output_dir>")
        sys.exit(1)

    apk_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    apk = APK(str(apk_path))

    manifest = apk.get_android_manifest_xml()
    app = manifest.find("application")

    # ------------------------
    # permissions
    # ------------------------

    requested_permissions = set()
    declared_permissions = set()

    for el in manifest:

        tag = el.tag.split("}")[-1]

        if tag in ["uses-permission", "uses-permission-sdk-23", "uses-permission-sdk-m"]:
            name = attr(el, "name")
            if name:
                requested_permissions.add(name)

        if tag in ["permission", "permission-group", "permission-tree"]:
            name = attr(el, "name")
            if name:
                declared_permissions.add(name)

    # ------------------------
    # components
    # ------------------------

    activities_all = []
    activities_exported = []

    services_all = []
    services_exported = []

    receivers_all = []
    receivers_exported = []

    providers_all = []
    providers_exported = []

    for el in app:

        tag = el.tag.split("}")[-1]
        name = attr(el, "name")

        if not name:
            continue

        if tag == "activity":

            activities_all.append(name)

            if is_exported(el):
                activities_exported.append(name)

        elif tag == "service":

            services_all.append(name)

            if is_exported(el):
                services_exported.append(name)

        elif tag == "receiver":

            receivers_all.append(name)

            if is_exported(el):
                receivers_exported.append(name)

        elif tag == "provider":

            providers_all.append(name)

            if is_exported(el):
                providers_exported.append(name)

    # ------------------------
    # write files
    # ------------------------

    write_list(out_dir / "requested_permissions.txt", requested_permissions)
    write_list(out_dir / "declared_permissions.txt", declared_permissions)

    write_list(out_dir / "activities_all.txt", activities_all)
    write_list(out_dir / "activities_exported.txt", activities_exported)

    write_list(out_dir / "services_all.txt", services_all)
    write_list(out_dir / "services_exported.txt", services_exported)

    write_list(out_dir / "receivers_all.txt", receivers_all)
    write_list(out_dir / "receivers_exported.txt", receivers_exported)

    write_list(out_dir / "providers_all.txt", providers_all)
    write_list(out_dir / "providers_exported.txt", providers_exported)

    # ------------------------
    # summary
    # ------------------------

    summary = {
        "package": apk.get_package(),
        "versionCode": apk.get_androidversion_code(),
        "versionName": apk.get_androidversion_name(),

        "requested_permissions_count": len(requested_permissions),
        "declared_permissions_count": len(declared_permissions),

        "activities_all": len(set(activities_all)),
        "activities_exported": len(set(activities_exported)),

        "services_all": len(set(services_all)),
        "services_exported": len(set(services_exported)),

        "receivers_all": len(set(receivers_all)),
        "receivers_exported": len(set(receivers_exported)),

        "providers_all": len(set(providers_all)),
        "providers_exported": len(set(providers_exported)),
    }

    summary_text = "\n".join(f"{k}={v}" for k, v in summary.items())

    (out_dir / "manifest_security_summary.txt").write_text(summary_text + "\n", encoding="utf-8")

    print(summary_text)


if __name__ == "__main__":
    main()
