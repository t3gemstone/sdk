[ -f "$HOME/kiosk.environment" ] && source "$HOME/kiosk.environment"

# If running bash manually source .bashrc for SSH logins
[ -n "$BASH_VERSION" ] && [ -f "$HOME/.bashrc" ] && source "$HOME/.bashrc"

# If user is not root and logged in on tty1 start xorg
if [ -n "${UID:-}" ] && [ "$UID" != "0" ] && [ -z "$DISPLAY" ] && [ "$XDG_VTNR" == 1 ]; then
    # Restart xorg if terminated
    while true; do
        echo "starting xorg" | logger --tag "kiosk" --priority user.info
        startx -- -nocursor
        echo "xorg terminated" | logger --tag "kiosk" --priority user.warning
        sleep 1
    done
fi
