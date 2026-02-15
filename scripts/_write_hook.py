import os, json, io, sys
hook_path = sys.argv[1]
template_path = sys.argv[2]
# Read template and write hook
with open(template_path) as tf:
    content = tf.read()
with open(hook_path, "w") as hf:
    hf.write(content)
os.chmod(hook_path, 0o755)
print("Created:", hook_path)
