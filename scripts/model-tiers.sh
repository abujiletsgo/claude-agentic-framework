#!/usr/bin/env bash
# Model Tier Verification & Dashboard
# Usage: just model-tiers
#
# Scans all agent .md files for model: frontmatter and displays
# a summary of tier assignments, distribution, and discrepancies.

set -euo pipefail

AGENTS_DIR="$(cd "$(dirname "$0")/../global-agents" && pwd)"
YAML_CONFIG="$(cd "$(dirname "$0")/../data" && pwd)/model_tiers.yaml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

echo ""
echo -e "${BOLD}Multi-Model Tier Dashboard${NC}"
echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Collect agents (excluding crypto-backup and README)
opus_agents=()
sonnet_agents=()
haiku_agents=()
missing_agents=()
total=0

while IFS= read -r f; do
    agent=$(basename "$f" .md)
    model=$(grep -m1 "^model:" "$f" 2>/dev/null | awk '{print $2}' || true)
    total=$((total + 1))

    case "$model" in
        opus)   opus_agents+=("$agent") ;;
        sonnet) sonnet_agents+=("$agent") ;;
        haiku)  haiku_agents+=("$agent") ;;
        *)      missing_agents+=("$agent") ;;
    esac
done < <(find "$AGENTS_DIR" -name "*.md" -not -path "*/crypto-backup*" -not -name "README.md" | sort)

# Display per-tier tables
echo -e "${RED}${BOLD}Opus (Deep Reasoning)${NC}  ${DIM}\$15/\$75 per 1M tokens${NC}"
echo -e "${DIM}  Architecture, orchestration, security, critical analysis${NC}"
for a in "${opus_agents[@]}"; do
    echo -e "  ${RED}●${NC} $a"
done
echo ""

echo -e "${BLUE}${BOLD}Sonnet (Balanced)${NC}  ${DIM}\$3/\$15 per 1M tokens${NC}"
echo -e "${DIM}  Implementation, research, analysis, agent generation${NC}"
for a in "${sonnet_agents[@]}"; do
    echo -e "  ${BLUE}●${NC} $a"
done
echo ""

echo -e "${GREEN}${BOLD}Haiku (Fast Tasks)${NC}  ${DIM}\$0.25/\$1.25 per 1M tokens${NC}"
echo -e "${DIM}  Validation, data processing, docs, mechanical ops${NC}"
for a in "${haiku_agents[@]}"; do
    echo -e "  ${GREEN}●${NC} $a"
done
echo ""

# Missing model field
if [ ${#missing_agents[@]} -gt 0 ]; then
    echo -e "${YELLOW}${BOLD}WARNING: Missing model field${NC}"
    for a in "${missing_agents[@]}"; do
        echo -e "  ${YELLOW}!${NC} $a"
    done
    echo ""
fi

# Distribution summary
echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}Distribution Summary${NC}"
echo ""

opus_count=${#opus_agents[@]}
sonnet_count=${#sonnet_agents[@]}
haiku_count=${#haiku_agents[@]}
missing_count=${#missing_agents[@]}

opus_pct=$((opus_count * 100 / total))
sonnet_pct=$((sonnet_count * 100 / total))
haiku_pct=$((haiku_count * 100 / total))

# Visual bar chart
opus_bar=$(printf '█%.0s' $(seq 1 $((opus_count * 2))))
sonnet_bar=$(printf '█%.0s' $(seq 1 $((sonnet_count * 2))))
haiku_bar=$(printf '█%.0s' $(seq 1 $((haiku_count * 2))))

printf "  ${RED}Opus  ${NC} %2d (%2d%%) ${RED}%s${NC}\n" "$opus_count" "$opus_pct" "$opus_bar"
printf "  ${BLUE}Sonnet${NC} %2d (%2d%%) ${BLUE}%s${NC}\n" "$sonnet_count" "$sonnet_pct" "$sonnet_bar"
printf "  ${GREEN}Haiku ${NC} %2d (%2d%%) ${GREEN}%s${NC}\n" "$haiku_count" "$haiku_pct" "$haiku_bar"
echo -e "  ${DIM}Total: $total agents${NC}"
echo ""

# Target validation
echo -e "${BOLD}Target Validation${NC}"
target_opus=12
target_sonnet=48
target_haiku=39

check() {
    local label=$1 actual=$2 target=$3
    local diff=$((actual - target))
    if [ "$diff" -eq 0 ]; then
        echo -e "  ${GREEN}PASS${NC} $label: ${actual}% (target: ${target}%)"
    elif [ "$diff" -gt -3 ] && [ "$diff" -lt 3 ]; then
        echo -e "  ${GREEN}PASS${NC} $label: ${actual}% (target: ${target}%, within tolerance)"
    else
        echo -e "  ${YELLOW}WARN${NC} $label: ${actual}% (target: ${target}%, off by ${diff}%)"
    fi
}

check "Opus " "$opus_pct" "$target_opus"
check "Sonnet" "$sonnet_pct" "$target_sonnet"
check "Haiku " "$haiku_pct" "$target_haiku"
echo ""

# Config file check
echo -e "${BOLD}Config Files${NC}"
if [ -f "$YAML_CONFIG" ]; then
    echo -e "  ${GREEN}PASS${NC} data/model_tiers.yaml exists"
else
    echo -e "  ${RED}FAIL${NC} data/model_tiers.yaml missing"
fi

skill_file="$(cd "$(dirname "$0")/../global-skills/multi-model-tiers" && pwd)/SKILL.md"
if [ -f "$skill_file" ]; then
    echo -e "  ${GREEN}PASS${NC} global-skills/multi-model-tiers/SKILL.md exists"
else
    echo -e "  ${RED}FAIL${NC} global-skills/multi-model-tiers/SKILL.md missing"
fi
echo ""

# Cross-check YAML vs frontmatter
echo -e "${BOLD}YAML Config Cross-Check${NC}"
# Count all agent entries (lines starting with "    - ") in agent_tiers section
yaml_total=$(sed -n '/^agent_tiers:/,/^[a-z]/p' "$YAML_CONFIG" | grep -c '^\s*- ' || true)

if [ "$yaml_total" -eq "$total" ]; then
    echo -e "  ${GREEN}PASS${NC} YAML lists $yaml_total agents (matches $total frontmatter agents)"
else
    echo -e "  ${YELLOW}WARN${NC} YAML lists $yaml_total agents vs $total in frontmatter"
fi

# Overall status
echo ""
if [ "$missing_count" -eq 0 ]; then
    echo -e "${GREEN}${BOLD}All $total agents have model tier assignments.${NC}"
else
    echo -e "${RED}${BOLD}$missing_count agent(s) missing model field!${NC}"
fi
echo ""
