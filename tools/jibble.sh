#!/bin/bash
# jibble.sh — Clock in/out of Jibble Mac app via AppleScript
#
# Usage:
#   bash tools/jibble.sh clock-in
#   bash tools/jibble.sh clock-out
#   bash tools/jibble.sh status
#
# Requires: Jibble Mac app installed, Terminal in Accessibility permissions

set -euo pipefail

ACTION="${1:-status}"
LOG_DIR="$(cd "$(dirname "$0")/.." && pwd)/.tmp"
LOG_FILE="$LOG_DIR/jibble.log"
mkdir -p "$LOG_DIR"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE"
}

ensure_jibble_running() {
    # Jibble crashes on first open — open, wait, check, reopen if needed
    local max_attempts=3
    for i in $(seq 1 $max_attempts); do
        log "Opening Jibble (attempt $i/$max_attempts)..."
        open -a "Jibble - Time Tracking"
        sleep 5
        if pgrep -x "Jibble - Time Tracking" > /dev/null 2>&1; then
            log "Jibble is running"
            return 0
        fi
        log "Jibble not running after attempt $i — retrying..."
        sleep 2
    done
    log "ERROR: Jibble failed to stay open after $max_attempts attempts"
    return 1
}

get_status() {
    # Returns "in" or "out" based on UI state
    osascript -e '
    tell application "Jibble - Time Tracking" to activate
    delay 3
    tell application "System Events"
        tell process "Jibble - Time Tracking"
            set frontmost to true
            delay 2
            set allElems to entire contents of front window
            repeat with elem in allElems
                try
                    set d to description of elem
                    if d is "clock-out" then return "in"
                    if d is "clock-in" then return "out"
                end try
            end repeat
            return "unknown"
        end tell
    end tell
    ' 2>/dev/null
}

click_element() {
    # Helper: click a UI element by description in the frontmost Jibble window
    local desc="$1"
    osascript -e "
    tell application \"System Events\"
        tell process \"Jibble - Time Tracking\"
            set allElems to entire contents of front window
            repeat with elem in allElems
                try
                    set d to description of elem
                    if d is \"$desc\" then
                        set p to position of elem
                        set s to size of elem
                        set cx to (item 1 of p) + ((item 1 of s) / 2)
                        set cy to (item 2 of p) + ((item 2 of s) / 2)
                        click at {cx, cy}
                        return true
                    end if
                end try
            end repeat
            return false
        end tell
    end tell
    " 2>/dev/null
}

click_button() {
    # Helper: click a button by description
    local desc="$1"
    osascript -e "
    tell application \"System Events\"
        tell process \"Jibble - Time Tracking\"
            set allElems to entire contents of front window
            repeat with elem in allElems
                try
                    set d to description of elem
                    if d is \"$desc\" and class of elem as text is \"button\" then
                        set p to position of elem
                        set s to size of elem
                        set cx to (item 1 of p) + ((item 1 of s) / 2)
                        set cy to (item 2 of p) + ((item 2 of s) / 2)
                        click at {cx, cy}
                        return true
                    end if
                end try
            end repeat
            return false
        end tell
    end tell
    " 2>/dev/null
}

set_auto_clockout_time() {
    # Set the hour dropdown to 16 and minute to 00 (4:00 PM)
    # The sub-dialog has two dropdowns (hour, minute) and quick presets
    osascript -e '
    tell application "System Events"
        tell process "Jibble - Time Tracking"
            set allElems to entire contents of front window
            -- Find all popup buttons / combo boxes for the dropdowns
            set foundHour to false
            set foundMin to false
            repeat with elem in allElems
                try
                    set d to description of elem
                    set cls to class of elem as text
                    -- Hour dropdown: look for the first dropdown/popup with a 2-digit value
                    if cls is "pop up button" or cls is "combo box" then
                        if not foundHour then
                            -- Click to open hour dropdown, select 16
                            click elem
                            delay 1
                            -- Type 16 to select it
                            keystroke "16"
                            delay 0.5
                            key code 36 -- Enter
                            set foundHour to true
                            delay 1
                        else if not foundMin then
                            -- Click to open minute dropdown, select 00
                            click elem
                            delay 1
                            keystroke "00"
                            delay 0.5
                            key code 36 -- Enter
                            set foundMin to true
                        end if
                    end if
                end try
            end repeat
        end tell
    end tell
    ' 2>/dev/null
}

clock_in_with_auto_clockout() {
    osascript -e '
    tell application "System Events"
        tell process "Jibble - Time Tracking"
            set frontmost to true
            delay 1
        end tell
    end tell
    ' 2>/dev/null

    # Step 1: Click clock-in button
    click_element "clock-in"
    sleep 3

    # Step 2: Click "Auto clock out" to open sub-dialog
    click_element "Auto clock out"
    sleep 3

    # Step 3: Set time to 4:00 PM (16:00)
    set_auto_clockout_time
    sleep 2

    # Step 4: Save the auto clock-out sub-dialog
    click_button "Save"
    sleep 3

    # Step 5: Save the main clock-in dialog
    click_button "Save"
}

clock_in_simple() {
    osascript -e '
    tell application "System Events"
        tell process "Jibble - Time Tracking"
            set frontmost to true
            delay 1
        end tell
    end tell
    ' 2>/dev/null
    click_element "clock-in"
    sleep 3
    click_button "Save"
}

clock_out_simple() {
    osascript -e '
    tell application "System Events"
        tell process "Jibble - Time Tracking"
            set frontmost to true
            delay 1
        end tell
    end tell
    ' 2>/dev/null
    click_element "clock-out"
    sleep 3
    click_button "Save"
}

verify_status() {
    local expected="$1"
    sleep 5
    local actual
    actual=$(get_status)
    if [ "$actual" = "$expected" ]; then
        log "Verified: clocked $expected"
        return 0
    else
        log "WARNING: Expected $expected but got $actual"
        return 1
    fi
}

case "$ACTION" in
    status)
        ensure_jibble_running
        status=$(get_status)
        log "Current status: clocked $status"
        ;;
    clock-in)
        dow=$(date +%u)
        if [ "$dow" -ge 6 ]; then
            log "Weekend (dow=$dow) — skipping clock-in"
            exit 0
        fi
        ensure_jibble_running
        status=$(get_status)
        log "Current status: clocked $status"
        if [ "$status" = "in" ]; then
            log "Already clocked in — skipping"
            exit 0
        fi
        log "Clocking in (with auto clock-out at 4 PM)..."
        clock_in_with_auto_clockout
        verify_status "in"
        ;;
    clock-out)
        ensure_jibble_running
        status=$(get_status)
        log "Current status: clocked $status"
        if [ "$status" = "out" ]; then
            log "Already clocked out — skipping"
            exit 0
        fi
        log "Clocking out..."
        clock_out_simple
        verify_status "out"
        ;;
    *)
        echo "Usage: bash tools/jibble.sh {clock-in|clock-out|status}"
        exit 1
        ;;
esac
