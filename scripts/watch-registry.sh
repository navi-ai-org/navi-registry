#!/usr/bin/env bash
#
# watch-registry.sh — watches the navi-registry repo for issues labeled
# "registry-needs-review" and dispatches NAVI (headless) to resolve them.
#
# Configuration via environment variables:
#
#   NAVI_REGISTRY_DIR     — path to the local navi-registry clone (required)
#   NAVI_BIN              — path to the navi binary (default: "navi")
#   NAVI_PROVIDER         — provider id for NAVI (default: "opencode")
#   NAVI_MODEL            — model name for NAVI (default: "deepseek-v4-flash-free")
#   NAVI_PROVIDER_KEY_ENV — env var name for the API key (default: "OPENCODE_API_KEY")
#   NAVI_API_KEY          — the API key value (default: $OPENCODE_API_KEY)
#   WATCH_INTERVAL        — seconds between checks when run in --daemon mode (default: 1800)
#
# Usage:
#   watch-registry.sh              # one-shot check
#   watch-registry.sh --daemon     # loop forever, checking every WATCH_INTERVAL seconds
#   watch-registry.sh --install    # install systemd timer + service
#   watch-registry.sh --uninstall  # remove systemd timer + service
#
set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────

NAVI_BIN="${NAVI_BIN:-navi}"
NAVI_PROVIDER="${NAVI_PROVIDER:-opencode}"
NAVI_MODEL="${NAVI_MODEL:-deepseek-v4-flash-free}"
NAVI_PROVIDER_KEY_ENV="${NAVI_PROVIDER_KEY_ENV:-OPENCODE_API_KEY}"
NAVI_API_KEY="${NAVI_API_KEY:-${OPENCODE_API_KEY:-}}"
WATCH_INTERVAL="${WATCH_INTERVAL:-1800}"
ISSUE_LABEL="registry-needs-review"
REPO="navi-ai-org/navi-registry"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Helpers ───────────────────────────────────────────────────────────────

log() {
    printf '[watch-registry] %s\n' "$*" >&2
}

die() {
    log "ERROR: $*"
    exit 1
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "command not found: $1"
}

# ── Core logic ────────────────────────────────────────────────────────────

# Fetches open issues with the registry-needs-review label.
# Outputs JSON array of {number, title, body} objects.
fetch_open_issues() {
    gh issue list \
        --repo "$REPO" \
        --label "$ISSUE_LABEL" \
        --state open \
        --json number,title,body 2>/dev/null || echo "[]"
}

# Creates a temporary .navi/config.toml for NAVI so it uses the configured
# provider/model without touching the user's global config.
create_temp_config() {
    local tmpdir="$1"
    cat > "$tmpdir/.navi/config.toml" <<EOF
[model]
provider = "${NAVI_PROVIDER}"
name = "${NAVI_MODEL}"
EOF
}

# Dispatches NAVI to resolve a single issue.
# Sets up a temp project dir with .navi/config.toml, runs NAVI headless
# with the issue body as the task, then commits and pushes changes.
resolve_issue() {
    local issue_number="$1"
    local issue_title="$2"
    local issue_body="$3"

    log "resolving issue #${issue_number}: ${issue_title}"

    # Use the registry repo as the working directory for NAVI.
    local work_dir="${NAVI_REGISTRY_DIR:?NAVI_REGISTRY_DIR is required}"

    # Create temp config if it doesn't already have one.
    if [ ! -f "$work_dir/.navi/config.toml" ]; then
        mkdir -p "$work_dir/.navi"
        create_temp_config "$work_dir"
        local created_config=1
    fi

    # Export the API key for the provider.
    if [ -n "${NAVI_API_KEY}" ]; then
        export "${NAVI_PROVIDER_KEY_ENV}=${NAVI_API_KEY}"
    fi

    # Build the task prompt for NAVI.
    local task
    task="You are working in the navi-registry repository at ${work_dir}.

A GitHub issue (#${issue_number}) was created because the daily registry probe
detected models that need manual attachment capability review.

## Issue: ${issue_title}

${issue_body}

## Your task

1. Read the issue body to identify which models need attachment review.
2. For each model, check the provider's documentation or API to determine
   which attachment types it supports (images, audio, video, documents).
3. Update the corresponding providers/*.json file with the appropriate
   supports_images, supports_audio, supports_video, supports_documents fields.
4. Add matching rules to scripts/model_rules.json so future detections of
   the same model pattern are auto-filled.
5. Run: python scripts/validate.py
6. Git commit all changes with a clear message.
7. Git push.
8. Close the GitHub issue with: gh issue close ${issue_number} --repo ${REPO}

Do not skip any model. If you cannot determine the capabilities of a model,
leave it unchanged and note it in your response."

    # Run NAVI headless.
    log "starting NAVI headless with provider=${NAVI_PROVIDER} model=${NAVI_MODEL}"
    cd "$work_dir"
    "$NAVI_BIN" --no-tui "$task" || {
        log "NAVI failed for issue #${issue_number}"
        if [ "${created_config:-0}" = "1" ]; then
            rm -f "$work_dir/.navi/config.toml"
            rmdir "$work_dir/.navi" 2>/dev/null || true
        fi
        return 1
    }

    # Clean up temp config if we created it.
    if [ "${created_config:-0}" = "1" ]; then
        rm -f "$work_dir/.navi/config.toml"
        rmdir "$work_dir/.navi" 2>/dev/null || true
    fi

    log "issue #${issue_number} resolved"
    return 0
}

# Main check: fetch issues and dispatch NAVI for each one.
run_check() {
    require_cmd gh
    require_cmd "$NAVI_BIN"

    if [ -z "${NAVI_REGISTRY_DIR:-}" ]; then
        die "NAVI_REGISTRY_DIR is required (path to local navi-registry clone)"
    fi

    if [ ! -d "$NAVI_REGISTRY_DIR" ]; then
        die "NAVI_REGISTRY_DIR does not exist: $NAVI_REGISTRY_DIR"
    fi

    log "checking for open issues labeled '${ISSUE_LABEL}' in ${REPO}..."

    local issues
    issues=$(fetch_open_issues)

    local count
    count=$(echo "$issues" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")

    if [ "$count" = "0" ]; then
        log "no issues need review"
        return 0
    fi

    log "found ${count} issue(s) needing review"

    echo "$issues" | python3 -c "
import json, sys
issues = json.load(sys.stdin)
for issue in issues:
    print(f\"{issue['number']}|{issue['title']}|{issue['body']}\")
" | while IFS='|' read -r number title body; do
        resolve_issue "$number" "$title" "$body" || true
    done
}

# ── Daemon mode ───────────────────────────────────────────────────────────

run_daemon() {
    log "daemon mode: checking every ${WATCH_INTERVAL}s"
    while true; do
        run_check || true
        sleep "$WATCH_INTERVAL"
    done
}

# ── Systemd install ───────────────────────────────────────────────────────

install_systemd() {
    local unit_dir="${HOME}/.config/systemd/user"
    local service_name="navi-registry-watch.service"
    local timer_name="navi-registry-watch.timer"

    mkdir -p "$unit_dir"

    # Resolve navi binary path.
    local navi_path
    navi_path=$(command -v "$NAVI_BIN" 2>/dev/null || echo "$NAVI_BIN")

    # Resolve registry dir.
    local registry_dir
    registry_dir="${NAVI_REGISTRY_DIR:?NAVI_REGISTRY_DIR is required}"

    # Build service unit, conditionally including the API key line.
    local api_key_line=""
    if [ -n "${NAVI_API_KEY}" ]; then
        api_key_line="Environment=${NAVI_PROVIDER_KEY_ENV}=${NAVI_API_KEY}"
    fi

    cat > "$unit_dir/$service_name" <<EOF
[Unit]
Description=NAVI Registry Watch — resolves probe issues automatically

[Service]
Type=oneshot
ExecStart=${SCRIPT_DIR}/watch-registry.sh
Environment=NAVI_REGISTRY_DIR=${registry_dir}
Environment=NAVI_BIN=${navi_path}
Environment=NAVI_PROVIDER=${NAVI_PROVIDER}
Environment=NAVI_MODEL=${NAVI_MODEL}
Environment=NAVI_PROVIDER_KEY_ENV=${NAVI_PROVIDER_KEY_ENV}
${api_key_line}
WorkingDirectory=${registry_dir}
EOF

    # Write timer unit.
    cat > "$unit_dir/$timer_name" <<EOF
[Unit]
Description=Run NAVI Registry Watch periodically

[Timer]
OnBootSec=5min
OnUnitActiveSec=${WATCH_INTERVAL}sec
Unit=${service_name}

[Install]
WantedBy=timers.target
EOF

    log "installed systemd units:"
    log "  $unit_dir/$service_name"
    log "  $unit_dir/$timer_name"

    systemctl --user daemon-reload
    systemctl --user enable --now "$timer_name"
    log "timer enabled and started. Check: systemctl --user status $timer_name"
}

uninstall_systemd() {
    local unit_dir="${HOME}/.config/systemd/user"
    local service_name="navi-registry-watch.service"
    local timer_name="navi-registry-watch.timer"

    systemctl --user disable --now "$timer_name" 2>/dev/null || true
    rm -f "$unit_dir/$service_name" "$unit_dir/$timer_name"
    systemctl --user daemon-reload
    log "uninstalled systemd units"
}

# ── CLI ───────────────────────────────────────────────────────────────────

main() {
    case "${1:-}" in
        --daemon)
            run_daemon
            ;;
        --install)
            install_systemd
            ;;
        --uninstall)
            uninstall_systemd
            ;;
        --help|-h)
            cat <<EOF
watch-registry.sh — watch navi-registry for probe issues and dispatch NAVI

Usage:
  watch-registry.sh              one-shot check
  watch-registry.sh --daemon     loop forever
  watch-registry.sh --install    install systemd timer
  watch-registry.sh --uninstall  remove systemd timer

Environment:
  NAVI_REGISTRY_DIR      path to local navi-registry clone (required)
  NAVI_BIN               path to navi binary (default: navi)
  NAVI_PROVIDER          provider id (default: opencode)
  NAVI_MODEL             model name (default: deepseek-v4-flash-free)
  NAVI_PROVIDER_KEY_ENV  env var name for API key (default: OPENCODE_API_KEY)
  NAVI_API_KEY           API key value (default: \$OPENCODE_API_KEY)
  WATCH_INTERVAL         seconds between checks in daemon mode (default: 1800)
EOF
            ;;
        *)
            run_check
            ;;
    esac
}

main "$@"
