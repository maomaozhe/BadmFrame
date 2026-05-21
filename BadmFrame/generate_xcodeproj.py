#!/usr/bin/env python3
"""Generate BadmFrame.xcodeproj with proper UUIDs for all source files."""

import os
import hashlib
from pathlib import Path
from collections import defaultdict

PROJECT_DIR = Path(__file__).parent.absolute()
XCODEPROJ_DIR = PROJECT_DIR / "BadmFrame.xcodeproj"
PROJECT_NAME = "BadmFrame"
BUNDLE_ID = "com.badmframe.app"
SRC_ROOT = PROJECT_NAME  # "BadmFrame" - source code root relative to project dir

def gen_id(seed: str) -> str:
    """Generate a deterministic 24-char hex ID from a seed string."""
    h = hashlib.md5(seed.encode()).hexdigest()[:24].upper()
    if h[0].isdigit():
        h = 'A' + h[1:]
    return h

def pbx_quote(value: str) -> str:
    """Quote values that are not safe bare OpenStep plist strings."""
    safe_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.$/")
    if value and all(ch in safe_chars for ch in value):
        return value
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

def find_source_files():
    """Find all .swift files relative to source root."""
    sources = []
    src_dir = PROJECT_DIR / SRC_ROOT
    for root, dirs, files in os.walk(src_dir):
        for f in sorted(files):
            if f.endswith('.swift'):
                full = Path(root) / f
                rel = full.relative_to(src_dir)
                sources.append(str(rel))
    return sources

def find_resources():
    """Find resource files relative to source root."""
    resources = []
    assets = PROJECT_DIR / SRC_ROOT / "Assets.xcassets"
    if not assets.exists():
        assets.mkdir(parents=True, exist_ok=True)
        (assets / "Contents.json").write_text('{"info":{"author":"xcode","version":1}}')
    resources.append("Assets.xcassets")
    return resources

def build_group_tree(sources, resources):
    """Build a nested group tree from source and resource paths."""
    tree = {"name": SRC_ROOT, "path": SRC_ROOT, "files": [], "subgroups": {}}

    def ensure_path(node, parts):
        if not parts:
            return node
        name = parts[0]
        if name not in node["subgroups"]:
            node["subgroups"][name] = {
                "name": name,
                "path": name,
                "files": [],
                "subgroups": {}
            }
        return ensure_path(node["subgroups"][name], parts[1:])

    for src in sources:
        parent = str(Path(src).parent)
        if parent == ".":
            tree["files"].append(src)
        else:
            parts = parent.split("/")
            node = ensure_path(tree, parts)
            node["files"].append(src)

    for res in resources:
        tree["files"].append(res)

    return tree

def emit_groups(tree, file_ref_ids, sub_groups, output, indent=2):
    """Recursively emit PBXGroup entries and populate sub_groups dict.
    Returns list of (group_id, group) for children that need parent references."""
    group_id = gen_id(f"group-{tree['path']}")
    child_refs = []

    # Process subgroups first (depth-first)
    for name, subgroup in sorted(tree["subgroups"].items()):
        child_id = emit_groups(subgroup, file_ref_ids, sub_groups, output, indent)[0]
        child_refs.append((child_id, name))

    # Add file references
    for f in sorted(tree["files"]):
        child_refs.append((file_ref_ids[f], Path(f).name))

    # Emit this group
    tab = "\t" * indent
    output.append(f'{tab}{group_id} /* {tree["name"]} */ = {{')
    output.append(f'{tab}\tisa = PBXGroup;')
    output.append(f'{tab}\tchildren = (')
    for cid, cname in child_refs:
        output.append(f'{tab}\t\t{cid} /* {cname} */,')
    output.append(f'{tab}\t);')
    output.append(f'{tab}\tpath = {tree["name"]};')
    output.append(f'{tab}\tsourceTree = "<group>";')
    output.append(f'{tab}}};')

    return (group_id, tree["name"])

def generate_pbxproj():
    sources = find_source_files()
    resources = find_resources()
    group_tree = build_group_tree(sources, resources)

    lines = []
    def p(line=""):
        lines.append(line)

    p("// !$*UTF8*$!")
    p("{")
    p("\tarchiveVersion = 1;")
    p("\tclasses = {};")
    p("\tobjectVersion = 77;")
    p("\tobjects = {")

    # ---- IDs ----
    product_group_id = gen_id("product-group")
    project_id = gen_id("project")
    native_target_id = gen_id("native-target")
    sources_bp_id = gen_id("sources-build-phase")
    resources_bp_id = gen_id("resources-build-phase")
    frameworks_bp_id = gen_id("frameworks-build-phase")
    product_ref_id = gen_id("product-ref")
    debug_config_id = gen_id("debug-config-project")
    release_config_id = gen_id("release-config-project")
    debug_target_config_id = gen_id("debug-config-target")
    release_target_config_id = gen_id("release-config-target")
    proj_config_list_id = gen_id("proj-config-list")
    target_config_list_id = gen_id("target-config-list")

    file_ref_ids = {}
    build_file_ids = {}

    all_files = sources + resources
    for f in all_files:
        fid = gen_id(f"file-ref-{f}")
        file_ref_ids[f] = fid
        bfid = gen_id(f"build-file-{f}")
        build_file_ids[f] = bfid

    # ---- PBXBuildFile ----
    for key, bfid in build_file_ids.items():
        name = Path(key).name
        if key in sources:
            fid = file_ref_ids[key]
            p(f"\t\t{bfid} /* {name} in Sources */ = {{isa = PBXBuildFile; fileRef = {fid} /* {name} */; }};")
        elif key in resources:
            fid = file_ref_ids[key]
            p(f"\t\t{bfid} /* {name} in Resources */ = {{isa = PBXBuildFile; fileRef = {fid} /* {name} */; }};")

    # ---- PBXFileReference ----
    for key, fid in file_ref_ids.items():
        name = Path(key).name
        if key.endswith('.swift'):
            p(f'\t\t{fid} /* {name} */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = {pbx_quote(name)}; sourceTree = "<group>"; }};')
        elif key.endswith('.plist'):
            p(f'\t\t{fid} /* {name} */ = {{isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = {pbx_quote(name)}; sourceTree = "<group>"; }};')
        elif key.endswith('.xcassets'):
            p(f'\t\t{fid} /* {name} */ = {{isa = PBXFileReference; lastKnownFileType = folder.assetcatalog; path = {pbx_quote(name)}; sourceTree = "<group>"; }};')

    # Product reference
    p(f'\t\t{product_ref_id} /* {PROJECT_NAME}.app */ = {{isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = {PROJECT_NAME}.app; sourceTree = BUILT_PRODUCTS_DIR; }};')

    # ---- PBXFrameworksBuildPhase ----
    p(f"\t\t{frameworks_bp_id} /* Frameworks */ = {{")
    p("\t\t\tisa = PBXFrameworksBuildPhase;")
    p("\t\t\tbuildActionMask = 2147483647;")
    p("\t\t\tfiles = (")
    p("\t\t\t);")
    p("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    p("\t\t};")

    # ---- PBXGroup: emit all groups recursively ----
    # We need to emit groups in the right order and also track the main group's ID.
    # The emit_groups function emits PBXGroup entries and returns (id, name).
    # We need to also add the Products group as a child of the main group.

    # First, collect all group IDs separately so we can modify the tree
    # Actually, let's emit groups while building, and track the main group ID.

    # Build main group with Products child added
    main_group_children = []
    # Emit subgroups
    for name, subgroup in sorted(group_tree["subgroups"].items()):
        child_id = emit_groups(subgroup, file_ref_ids, {}, lines, indent=2)[0]
        main_group_children.append((child_id, name))
    # Root-level files
    for f in sorted(group_tree["files"]):
        main_group_children.append((file_ref_ids[f], Path(f).name))
    # Products group
    main_group_children.append((product_group_id, "Products"))

    main_group_id = gen_id(f"group-{group_tree['path']}")
    p(f'\t\t{main_group_id} /* {group_tree["name"]} */ = {{')
    p("\t\t\tisa = PBXGroup;")
    p("\t\t\tchildren = (")
    for cid, cname in main_group_children:
        p(f"\t\t\t\t{cid} /* {cname} */,")
    p("\t\t\t);")
    p(f"\t\t\tpath = {SRC_ROOT};")
    p('\t\t\tsourceTree = "<group>";')
    p("\t\t};")

    # ---- PBXGroup: products ----
    p(f"\t\t{product_group_id} /* Products */ = {{")
    p("\t\t\tisa = PBXGroup;")
    p("\t\t\tchildren = (")
    p(f"\t\t\t\t{product_ref_id} /* {PROJECT_NAME}.app */,")
    p("\t\t\t);")
    p("\t\t\tname = Products;")
    p('\t\t\tsourceTree = "<group>";')
    p("\t\t};")

    # ---- PBXNativeTarget ----
    p(f'\t\t{native_target_id} /* {PROJECT_NAME} */ = {{')
    p(f'\t\t\tisa = PBXNativeTarget;')
    p(f'\t\t\tbuildConfigurationList = {target_config_list_id} /* Build configuration list for PBXNativeTarget "{PROJECT_NAME}" */;')
    p("\t\t\tbuildPhases = (")
    p(f"\t\t\t\t{sources_bp_id} /* Sources */,")
    p(f"\t\t\t\t{frameworks_bp_id} /* Frameworks */,")
    p(f"\t\t\t\t{resources_bp_id} /* Resources */,")
    p("\t\t\t);")
    p("\t\t\tbuildRules = (")
    p("\t\t\t);")
    p("\t\t\tdependencies = (")
    p("\t\t\t);")
    p(f"\t\t\tname = {PROJECT_NAME};")
    p(f"\t\t\tproductName = {PROJECT_NAME};")
    p(f"\t\t\tproductReference = {product_ref_id} /* {PROJECT_NAME}.app */;")
    p('\t\t\tproductType = "com.apple.product-type.application";')
    p("\t\t};")

    # ---- PBXProject ----
    p(f'\t\t{project_id} /* Project object */ = {{')
    p(f'\t\t\tisa = PBXProject;')
    p("\t\t\tattributes = {")
    p("\t\t\t\tBuildIndependentTargetsInParallel = 1;")
    p("\t\t\t\tLastSwiftUpdateCheck = 2650;")
    p("\t\t\t\tLastUpgradeCheck = 2650;")
    p("\t\t\t\tTargetAttributes = {")
    p(f'\t\t\t\t\t{native_target_id} = {{')
    p("\t\t\t\t\t\tCreatedOnToolsVersion = 2650;")
    p("\t\t\t\t\t};")
    p("\t\t\t\t};")
    p("\t\t\t};")
    p(f'\t\t\tbuildConfigurationList = {proj_config_list_id} /* Build configuration list for PBXProject "{PROJECT_NAME}" */;')
    p('\t\t\tcompatibilityVersion = "Xcode 16.0";')
    p("\t\t\tdevelopmentRegion = en;")
    p("\t\t\thasScannedForEncodings = 0;")
    p("\t\t\tknownRegions = (")
    p("\t\t\t\ten,")
    p("\t\t\t\tBase,")
    p('\t\t\t\t"zh-Hans",')
    p("\t\t\t);")
    p(f"\t\t\tmainGroup = {main_group_id};")
    p(f"\t\t\tproductRefGroup = {product_group_id} /* Products */;")
    p('\t\t\tprojectDirPath = "";')
    p('\t\t\tprojectRoot = "";')
    p("\t\t\ttargets = (")
    p(f"\t\t\t\t{native_target_id} /* {PROJECT_NAME} */,")
    p("\t\t\t);")
    p("\t\t};")

    # ---- PBXResourcesBuildPhase ----
    res_list = ",\n".join([f'\t\t\t\t{build_file_ids[r]} /* {Path(r).name} in Resources */' for r in resources])
    p(f"\t\t{resources_bp_id} /* Resources */ = {{")
    p("\t\t\tisa = PBXResourcesBuildPhase;")
    p("\t\t\tbuildActionMask = 2147483647;")
    p("\t\t\tfiles = (")
    if res_list:
        p(res_list + ",")
    p("\t\t\t);")
    p("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    p("\t\t};")

    # ---- PBXSourcesBuildPhase ----
    src_list = ",\n".join([f'\t\t\t\t{build_file_ids[s]} /* {Path(s).name} in Sources */' for s in sources])
    p(f"\t\t{sources_bp_id} /* Sources */ = {{")
    p("\t\t\tisa = PBXSourcesBuildPhase;")
    p("\t\t\tbuildActionMask = 2147483647;")
    p("\t\t\tfiles = (")
    if src_list:
        p(src_list + ",")
    p("\t\t\t);")
    p("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    p("\t\t};")

    # ---- XCBuildConfiguration (Debug, project) ----
    p(f"\t\t{debug_config_id} /* Debug */ = {{")
    p("\t\t\tisa = XCBuildConfiguration;")
    p("\t\t\tbuildSettings = {")
    p("\t\t\t\tALWAYS_SEARCH_USER_PATHS = NO;")
    p("\t\t\t\tASSETCATALOG_COMPILER_GENERATE_SWIFT_ASSET_SYMBOL_EXTENSIONS = YES;")
    p("\t\t\t\tCLANG_ANALYZER_NONNULL = YES;")
    p('\t\t\t\tCLANG_CXX_LANGUAGE_STANDARD = "gnu++20";')
    p("\t\t\t\tCLANG_ENABLE_MODULES = YES;")
    p("\t\t\t\tCLANG_ENABLE_OBJC_ARC = YES;")
    p("\t\t\t\tCOPY_PHASE_STRIP = NO;")
    p("\t\t\t\tDEBUG_INFORMATION_FORMAT = dwarf;")
    p("\t\t\t\tENABLE_STRICT_OBJC_MSGSEND = YES;")
    p("\t\t\t\tENABLE_TESTABILITY = YES;")
    p("\t\t\t\tENABLE_USER_SCRIPT_SANDBOXING = YES;")
    p("\t\t\t\tGCC_DYNAMIC_NO_PIC = NO;")
    p("\t\t\t\tGCC_OPTIMIZATION_LEVEL = 0;")
    p('\t\t\t\tGCC_PREPROCESSOR_DEFINITIONS = ("DEBUG=1", "$(inherited)");')
    p("\t\t\t\tIPHONEOS_DEPLOYMENT_TARGET = 17.0;")
    p("\t\t\t\tLOCALIZATION_PREFERS_STRING_CATALOGS = YES;")
    p("\t\t\t\tMTL_ENABLE_DEBUG_INFO = INCLUDE_SOURCE;")
    p("\t\t\t\tONLY_ACTIVE_ARCH = YES;")
    p("\t\t\t\tSDKROOT = iphoneos;")
    p('\t\t\t\tSWIFT_ACTIVE_COMPILATION_CONDITIONS = "DEBUG $(inherited)";')
    p('\t\t\t\tSWIFT_OPTIMIZATION_LEVEL = "-Onone";')
    p("\t\t\t};")
    p("\t\t\tname = Debug;")
    p("\t\t};")

    # ---- XCBuildConfiguration (Release, project) ----
    p(f"\t\t{release_config_id} /* Release */ = {{")
    p("\t\t\tisa = XCBuildConfiguration;")
    p("\t\t\tbuildSettings = {")
    p("\t\t\t\tALWAYS_SEARCH_USER_PATHS = NO;")
    p("\t\t\t\tASSETCATALOG_COMPILER_GENERATE_SWIFT_ASSET_SYMBOL_EXTENSIONS = YES;")
    p("\t\t\t\tCLANG_ANALYZER_NONNULL = YES;")
    p('\t\t\t\tCLANG_CXX_LANGUAGE_STANDARD = "gnu++20";')
    p("\t\t\t\tCLANG_ENABLE_MODULES = YES;")
    p("\t\t\t\tCLANG_ENABLE_OBJC_ARC = YES;")
    p("\t\t\t\tCOPY_PHASE_STRIP = NO;")
    p('\t\t\t\tDEBUG_INFORMATION_FORMAT = "dwarf-with-dsym";')
    p("\t\t\t\tENABLE_NS_ASSERTIONS = NO;")
    p("\t\t\t\tENABLE_STRICT_OBJC_MSGSEND = YES;")
    p("\t\t\t\tENABLE_USER_SCRIPT_SANDBOXING = YES;")
    p("\t\t\t\tGCC_OPTIMIZATION_LEVEL = s;")
    p("\t\t\t\tIPHONEOS_DEPLOYMENT_TARGET = 17.0;")
    p("\t\t\t\tLOCALIZATION_PREFERS_STRING_CATALOGS = YES;")
    p("\t\t\t\tMTL_ENABLE_DEBUG_INFO = NO;")
    p("\t\t\t\tSDKROOT = iphoneos;")
    p("\t\t\t\tSWIFT_COMPILATION_MODE = wholemodule;")
    p("\t\t\t\tVALIDATE_PRODUCT = YES;")
    p("\t\t\t};")
    p("\t\t\tname = Release;")
    p("\t\t};")

    # ---- XCBuildConfiguration (Debug, target) ----
    p(f"\t\t{debug_target_config_id} /* Debug */ = {{")
    p("\t\t\tisa = XCBuildConfiguration;")
    p("\t\t\tbuildSettings = {")
    p("\t\t\t\tCODE_SIGN_STYLE = Automatic;")
    p("\t\t\t\tCURRENT_PROJECT_VERSION = 1;")
    p("\t\t\t\tENABLE_PREVIEWS = YES;")
    p("\t\t\t\tGENERATE_INFOPLIST_FILE = YES;")
    p(f"\t\t\t\tINFOPLIST_FILE = {SRC_ROOT}/Info.plist;")
    p("\t\t\t\tINFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES;")
    p("\t\t\t\tINFOPLIST_KEY_UIApplicationSupportsIndirectInputEvents = YES;")
    p("\t\t\t\tINFOPLIST_KEY_UILaunchScreen_Generation = YES;")
    p("\t\t\t\tINFOPLIST_KEY_UISupportedInterfaceOrientations = UIInterfaceOrientationPortrait;")
    p('\t\t\t\tLD_RUNPATH_SEARCH_PATHS = ("$(inherited)", "@executable_path/Frameworks");')
    p("\t\t\t\tMARKETING_VERSION = 1.0;")
    p(f"\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = {BUNDLE_ID};")
    p('\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";')
    p('\t\t\t\tSUPPORTED_PLATFORMS = "iphoneos iphonesimulator";')
    p("\t\t\t\tSUPPORTS_MACCATALYST = NO;")
    p("\t\t\t\tSWIFT_EMIT_LOC_STRINGS = YES;")
    p("\t\t\t\tSWIFT_VERSION = 5.0;")
    p("\t\t\t\tTARGETED_DEVICE_FAMILY = 1;")
    p("\t\t\t};")
    p("\t\t\tname = Debug;")
    p("\t\t};")

    # ---- XCBuildConfiguration (Release, target) ----
    p(f"\t\t{release_target_config_id} /* Release */ = {{")
    p("\t\t\tisa = XCBuildConfiguration;")
    p("\t\t\tbuildSettings = {")
    p("\t\t\t\tCODE_SIGN_STYLE = Automatic;")
    p("\t\t\t\tCURRENT_PROJECT_VERSION = 1;")
    p("\t\t\t\tENABLE_PREVIEWS = YES;")
    p("\t\t\t\tGENERATE_INFOPLIST_FILE = YES;")
    p(f"\t\t\t\tINFOPLIST_FILE = {SRC_ROOT}/Info.plist;")
    p("\t\t\t\tINFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES;")
    p("\t\t\t\tINFOPLIST_KEY_UIApplicationSupportsIndirectInputEvents = YES;")
    p("\t\t\t\tINFOPLIST_KEY_UILaunchScreen_Generation = YES;")
    p("\t\t\t\tINFOPLIST_KEY_UISupportedInterfaceOrientations = UIInterfaceOrientationPortrait;")
    p('\t\t\t\tLD_RUNPATH_SEARCH_PATHS = ("$(inherited)", "@executable_path/Frameworks");')
    p("\t\t\t\tMARKETING_VERSION = 1.0;")
    p(f"\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = {BUNDLE_ID};")
    p('\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";')
    p('\t\t\t\tSUPPORTED_PLATFORMS = "iphoneos iphonesimulator";')
    p("\t\t\t\tSUPPORTS_MACCATALYST = NO;")
    p("\t\t\t\tSWIFT_EMIT_LOC_STRINGS = YES;")
    p("\t\t\t\tSWIFT_VERSION = 5.0;")
    p("\t\t\t\tTARGETED_DEVICE_FAMILY = 1;")
    p("\t\t\t};")
    p("\t\t\tname = Release;")
    p("\t\t};")

    # ---- XCConfigurationList (project) ----
    p(f'\t\t{proj_config_list_id} /* Build configuration list for PBXProject "{PROJECT_NAME}" */ = {{')
    p("\t\t\tisa = XCConfigurationList;")
    p("\t\t\tbuildConfigurations = (")
    p(f"\t\t\t\t{debug_config_id} /* Debug */,")
    p(f"\t\t\t\t{release_config_id} /* Release */,")
    p("\t\t\t);")
    p("\t\t\tdefaultConfigurationIsVisible = 0;")
    p("\t\t\tdefaultConfigurationName = Release;")
    p("\t\t};")

    # ---- XCConfigurationList (target) ----
    p(f'\t\t{target_config_list_id} /* Build configuration list for PBXNativeTarget "{PROJECT_NAME}" */ = {{')
    p("\t\t\tisa = XCConfigurationList;")
    p("\t\t\tbuildConfigurations = (")
    p(f"\t\t\t\t{debug_target_config_id} /* Debug */,")
    p(f"\t\t\t\t{release_target_config_id} /* Release */,")
    p("\t\t\t);")
    p("\t\t\tdefaultConfigurationIsVisible = 0;")
    p("\t\t\tdefaultConfigurationName = Release;")
    p("\t\t};")

    p("\t};")
    p(f"\trootObject = {project_id} /* Project object */;")
    p("}")

    return "\n".join(lines)

if __name__ == "__main__":
    XCODEPROJ_DIR.mkdir(parents=True, exist_ok=True)
    pbxproj = XCODEPROJ_DIR / "project.pbxproj"
    content = generate_pbxproj()
    pbxproj.write_text(content)
    print(f"Generated {pbxproj}")
    print(f"  {len(find_source_files())} source files")
    print(f"  {len(find_resources())} resource files")
