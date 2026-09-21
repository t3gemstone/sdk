[ -f "$HOME/kiosk.environment" ] && source "$HOME/kiosk.environment"

# If running bash manually source .bashrc for SSH logins
[ -n "$BASH_VERSION" ] && [ -f "$HOME/.bashrc" ] && source "$HOME/.bashrc"

# If user is not root and logged in on tty1 start the kiosk session
if [ -n "${UID:-}" ] && [ "$UID" != "0" ] && [ -z "$DISPLAY" ] && [ "$XDG_VTNR" == 1 ]; then
    # Restart the session if terminated
    while true; do
        if [ "${KIOSK_BACKEND:-x11}" = "eglfs" ]; then
            # No display server; kiosk-session runs the app straight on DRM/KMS
            echo "starting eglfs session" | logger --tag "kiosk" --priority user.info
            kiosk-session
            echo "eglfs session terminated" | logger --tag "kiosk" --priority user.warning
        else
            echo "starting xorg" | logger --tag "kiosk" --priority user.info
            startx -- -nocursor
            echo "xorg terminated" | logger --tag "kiosk" --priority user.warning
        fi
        sleep 1
    done
fi
