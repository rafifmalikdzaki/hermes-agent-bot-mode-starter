#!/usr/bin/env bash
# Hermes Bot Mode Ecosystem Installer
# Deploys the 7 specialized profiles, zero-token scripts, and agent skills.

set -euo pipefail

HERMES_DIR="${HOME}/.hermes"
LOCAL_BIN="${HOME}/.local/bin"
SKILLS_DIR="${HOME}/.agents/skills"

echo "🚀 Installing Hermes Bot Mode Ecosystem..."

mkdir -p "${HERMES_DIR}/profiles" "${HERMES_DIR}/scripts" "${HERMES_DIR}/skills" "${LOCAL_BIN}" "${SKILLS_DIR}"

# 1. Install Profiles
echo "📁 Deploying 9 Specialist Bot Profiles..."
for profile in orchestrator researcher builder diagnostics engineer reviewer librarian security monitor; do
  target="${HERMES_DIR}/profiles/${profile}"
  mkdir -p "${target}"
  cp -r "profiles/${profile}/"* "${target}/"
  # Create alias in ~/.local/bin
  cat <<EOF > "${LOCAL_BIN}/${profile}"
#!/bin/sh
exec hermes -p ${profile} "\$@"
EOF
  chmod +x "${LOCAL_BIN}/${profile}"
  echo "  ✓ Installed profile: ${profile} (command: ${profile})"
done

# Create observer alias for monitor
ln -sf "${LOCAL_BIN}/monitor" "${LOCAL_BIN}/observer"

# 2. Install Scripts
echo "⚙️ Installing Zero-Token CLI Tools..."
cp scripts/* "${HERMES_DIR}/scripts/"
chmod +x "${HERMES_DIR}/scripts/"*.py

ln -sf "${HERMES_DIR}/scripts/open_deep_research.py" "${LOCAL_BIN}/deep-research"
ln -sf "${HERMES_DIR}/scripts/libreoffice_tools.py" "${LOCAL_BIN}/doc-convert"
ln -sf "${HERMES_DIR}/scripts/libreoffice_tools.py" "${LOCAL_BIN}/doc-inspect"
ln -sf "${HERMES_DIR}/scripts/system_diagnose.py" "${LOCAL_BIN}/system-tune"
ln -sf "${HERMES_DIR}/scripts/agent_inspector.py" "${LOCAL_BIN}/agent-status"
ln -sf "${HERMES_DIR}/scripts/git_workspace_guard.py" "${LOCAL_BIN}/git-guard"
ln -sf "${HERMES_DIR}/scripts/project_token_usage.py" "${LOCAL_BIN}/token-projection"
ln -sf "${HERMES_DIR}/scripts/research_classifier.py" "${LOCAL_BIN}/research-classify"

# 3. Install Skills
echo "🧠 Deploying Agent Skills..."
cp -r skills/* "${SKILLS_DIR}/"
cp -r skills/* "${HERMES_DIR}/skills/"

echo ""
echo "✅ Installation Complete!"
echo "Run 'hermes profile list' to view your newly configured specialist bots."
echo "Launch Hermes Desktop with 'hermes desktop' to interact in Bot Mode."
