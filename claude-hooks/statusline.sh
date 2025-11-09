#!/bin/bash

# Claude Code Status Line Script
# Displays session memory context in status line
# Format: 🧠 8 (5 recent) memories | 📊 12 commits

# Path to session cache file
CACHE_FILE="$HOME/.claude/hooks/utilities/session-cache.json"

# ANSI color codes for styling
CYAN='\033[36m'
GREEN='\033[32m'
GRAY='\033[90m'
RESET='\033[0m'

# Check if cache file exists
if [ ! -f "$CACHE_FILE" ]; then
    # No cache file - session not started yet or hook failed
    echo ""
    exit 0
fi

# Read cache file and extract data
MEMORIES=$(jq -r '.memoriesLoaded // 0' "$CACHE_FILE" 2>/dev/null)
RECENT=$(jq -r '.recentCount // 0' "$CACHE_FILE" 2>/dev/null)
GIT_COMMITS=$(jq -r '.gitCommits // 0' "$CACHE_FILE" 2>/dev/null)

# Handle jq errors
if [ $? -ne 0 ]; then
    echo ""
    exit 0
fi

# Build status line output
STATUS=""

# Memory section
if [ "$MEMORIES" -gt 0 ]; then
    if [ "$RECENT" -gt 0 ]; then
        STATUS="${CYAN}🧠 ${MEMORIES}${RESET} ${GREEN}(${RECENT} recent)${RESET} memories"
    else
        STATUS="${CYAN}🧠 ${MEMORIES}${RESET} memories"
    fi
fi

# Git section
if [ "$GIT_COMMITS" -gt 0 ]; then
    if [ -n "$STATUS" ]; then
        STATUS="${STATUS} ${GRAY}|${RESET} ${CYAN}📊 ${GIT_COMMITS} commits${RESET}"
    else
        STATUS="${CYAN}📊 ${GIT_COMMITS} commits${RESET}"
    fi
fi

# Output first line becomes status line
echo -e "$STATUS"
