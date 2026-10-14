#!/bin/sh

# Lightweight status source for the T3 Plasma panel widget.
# Output format: CPU_PERCENT|MEMORY_PERCENT|MAX_TEMPERATURE_C

STATE_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
STATE_FILE="$STATE_DIR/t3-gemstone-panel-cpu"

read -r _ user nice system idle iowait irq softirq steal _rest < /proc/stat

user=${user:-0}
nice=${nice:-0}
system=${system:-0}
idle=${idle:-0}
iowait=${iowait:-0}
irq=${irq:-0}
softirq=${softirq:-0}
steal=${steal:-0}

total=$((user + nice + system + idle + iowait + irq + softirq + steal))
idle_total=$((idle + iowait))
previous_total=0
previous_idle=0

if [ -r "$STATE_FILE" ]; then
    read -r previous_total previous_idle < "$STATE_FILE" || true
fi

printf '%s %s\n' "$total" "$idle_total" > "$STATE_FILE"

delta_total=$((total - previous_total))
delta_idle=$((idle_total - previous_idle))

if [ "$delta_total" -gt 0 ]; then
    cpu_percent=$(((100 * (delta_total - delta_idle) + delta_total / 2) / delta_total))
else
    cpu_percent=0
fi

mem_total=$(awk '/^MemTotal:/ {print $2; exit}' /proc/meminfo)
mem_available=$(awk '/^MemAvailable:/ {print $2; exit}' /proc/meminfo)
mem_total=${mem_total:-1}
mem_available=${mem_available:-0}
memory_percent=$(((100 * (mem_total - mem_available) + mem_total / 2) / mem_total))

max_temperature=0
for temperature_file in /sys/class/thermal/thermal_zone*/temp; do
    [ -r "$temperature_file" ] || continue
    temperature=$(cat "$temperature_file" 2>/dev/null || printf '0')
    case "$temperature" in
        ''|*[!0-9]*) temperature=0 ;;
    esac
    if [ "$temperature" -gt "$max_temperature" ]; then
        max_temperature=$temperature
    fi
done

temperature_c=$(((max_temperature + 500) / 1000))

printf '%s|%s|%s\n' "$cpu_percent" "$memory_percent" "$temperature_c"
