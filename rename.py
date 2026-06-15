import os
import shutil

replacements = {
    "vscode-aria": "vscode-nitpick",
    "aria-mcp": "nitpick-mcp",
    "aria-safety": "nitpick-safety",
    "aria-test": "nitpick-test",
    "aria-tools": "nitpick-tools",
    "aria-docs": "nitpick-docs",
    "aria_mcp": "nitpick_mcp",
    "aria_safety": "nitpick_safety",
    "aria_test": "nitpick_test",
    "aria_compile": "nitpick_compile",
    "aria_check": "nitpick_check",
    "aria_docs": "nitpick_docs",
    "aria_format": "nitpick_format",
    "aria_ask": "nitpick_ask",
    "aria_specialist": "nitpick_specialist",
    "aria_ref": "nitpick_ref",
    "ariac": "nitpickc",
    "ARIAC": "NITPICKC",
    "ARIA_SAFETY": "NITPICK_SAFETY",
    "ARIA_LS_LOG": "NITPICK_LS_LOG",
    "ARIA_REF_MD": "NITPICK_REF_MD",
    "ARIA_ASK_DISABLED": "NITPICK_ASK_DISABLED",
    "ARIA_ROOT": "NITPICK_ROOT",
    "Aria Language Server": "Nitpick Language Server",
    "Aria Developer Tools": "Nitpick Developer Tools",
    "Aria toolchain": "Nitpick toolchain",
    "Aria ": "Nitpick ",
    "Aria's": "Nitpick's",
    "Aria.": "Nitpick.",
    "aria.": "nitpick.",
    ".aria": ".npk",
    "aria_": "nitpick_",
    "aria/build": "nitpick/build",
}

target_dirs = [
    "/home/randy/Workspace/REPOS/nitpick-tools/nitpick-mcp",
    "/home/randy/Workspace/REPOS/nitpick-tools/nitpick-safety",
    "/home/randy/Workspace/REPOS/nitpick-tools/nitpick-test",
    "/home/randy/Workspace/REPOS/nitpick-tools/vscode-aria",
    "/home/randy/Workspace/REPOS/nitpick-tools/vscode-nitpick",
    "/home/randy/Workspace/REPOS/nitpick-tools/.github",
    "/home/randy/Workspace/REPOS/nitpick-tools",
]

for d in target_dirs:
    if not os.path.exists(d): continue
    for root, dirs, files in os.walk(d):
        if ".git" in root.split(os.sep): continue
        if "node_modules" in root.split(os.sep): continue
        if "target" in root.split(os.sep): continue
        for f in files:
            if f in ("rename.py", "package-lock.json", ".gitignore"): continue
            if f.endswith(".png") or f.endswith(".jpg") or f.endswith(".zip") or f.endswith(".wasm"): continue
            path = os.path.join(root, f)
            if not os.path.exists(path) or not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as file:
                    content = file.read()
            except UnicodeDecodeError:
                continue
            
            new_content = content
            for old, new in replacements.items():
                new_content = new_content.replace(old, new)
                
            if new_content != content:
                with open(path, "w", encoding="utf-8") as file:
                    file.write(new_content)

# Rename directories
if os.path.exists("/home/randy/Workspace/REPOS/nitpick-tools/vscode-aria"):
    os.rename("/home/randy/Workspace/REPOS/nitpick-tools/vscode-aria", "/home/randy/Workspace/REPOS/nitpick-tools/vscode-nitpick")
    
# Rename files ending in .aria or with aria in name
for root, dirs, files in os.walk("/home/randy/Workspace/REPOS/nitpick-tools"):
    if ".git" in root.split(os.sep): continue
    if "node_modules" in root.split(os.sep): continue
    if "target" in root.split(os.sep): continue
    for f in files:
        if f.endswith(".aria"):
            os.rename(os.path.join(root, f), os.path.join(root, f.replace(".aria", ".npk")))
        elif "aria" in f and "variable" not in f and "rename.py" not in f:
            os.rename(os.path.join(root, f), os.path.join(root, f.replace("aria", "nitpick")))

print("Renames completed.")
