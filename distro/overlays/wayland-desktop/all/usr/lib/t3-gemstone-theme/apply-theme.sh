#!/bin/bash
set -eu

WALLPAPER=/usr/share/wallpapers/T3GemstoneLaunchEclipse/contents/images/1920x1080.png
STATE_DIR="${HOME}/.local/share/t3-gemstone-theme"
DEFAULT_APPLETSRC=/usr/share/t3-gemstone-theme/default-plasma-org.kde.plasma.desktop-appletsrc

# The package may be applied from SSH or dpkg's post-install hook. In both
# cases, point Qt and KDE tools at the already-running Plasma Wayland session.
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=${XDG_RUNTIME_DIR}/bus}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export DISPLAY="${DISPLAY:-:0}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-wayland}"
export QT_OPENGL="${QT_OPENGL:-software}"
export QT_QUICK_BACKEND="${QT_QUICK_BACKEND:-software}"
export QT_WAYLAND_CLIENT_BUFFER_INTEGRATION="${QT_WAYLAND_CLIENT_BUFFER_INTEGRATION:-shm}"

if [ "${1:-}" = "--backup" ]; then
    BACKUP_DIR="${STATE_DIR}/backups/$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${BACKUP_DIR}"
    for file in \
        kdeglobals \
        plasmarc \
        plasma-org.kde.plasma.desktop-appletsrc
    do
        if [ -f "${HOME}/.config/${file}" ]; then
            cp -a "${HOME}/.config/${file}" "${BACKUP_DIR}/${file}"
        fi
    done
fi

mkdir -p "${STATE_DIR}" "${HOME}/.config/gtk-3.0"

# Seed the default T3 panel/dock/launcher layout on first boot only, so a
# user's own later customization of the panel is never overwritten by a
# subsequent service run.
if [ -f "${DEFAULT_APPLETSRC}" ] &&
    [ ! -f "${HOME}/.config/plasma-org.kde.plasma.desktop-appletsrc" ]; then
    cp "${DEFAULT_APPLETSRC}" \
        "${HOME}/.config/plasma-org.kde.plasma.desktop-appletsrc"
fi

# Seed the T3 Browser desktop shortcut on first boot only, and only
# when the (optional) t3-content-shell package is actually installed.
CONTENT_SHELL_DESKTOP_FILE=/usr/local/share/applications/t3-content-shell.desktop
if [ -f "${CONTENT_SHELL_DESKTOP_FILE}" ] &&
    [ ! -f "${HOME}/Desktop/T3 Browser.desktop" ]; then
    mkdir -p "${HOME}/Desktop"
    cp "${CONTENT_SHELL_DESKTOP_FILE}" \
        "${HOME}/Desktop/T3 Browser.desktop"
    chmod 0755 "${HOME}/Desktop/T3 Browser.desktop"
fi

kwriteconfig5 \
    --file kdeglobals \
    --group General \
    --key ColorScheme \
    T3Gemstone
kwriteconfig5 \
    --file kdeglobals \
    --group KDE \
    --key widgetStyle \
    Breeze
kwriteconfig5 \
    --file plasmarc \
    --group Theme \
    --key name \
    T3Gemstone
kwriteconfig5 \
    --file gtk-3.0/settings.ini \
    --group Settings \
    --key gtk-theme-name \
    Breeze-Dark
kwriteconfig5 \
    --file gtk-3.0/settings.ini \
    --group Settings \
    --key gtk-icon-theme-name \
    breeze-dark

plasma-apply-colorscheme T3Gemstone >/dev/null 2>&1 || true
plasma-apply-desktoptheme T3Gemstone >/dev/null 2>&1 || true
plasma-apply-wallpaperimage "${WALLPAPER}" >/dev/null 2>&1 || true

if command -v qdbus >/dev/null 2>&1; then
    qdbus org.kde.plasmashell /PlasmaShell \
        org.kde.PlasmaShell.evaluateScript \
        'var ps=panels(); for (var p=0; p<ps.length; p++) { var ws=ps[p].widgets(); for (var w=0; w<ws.length; w++) { if (ws[w].type=="org.kde.plasma.kickoff") { ws[w].currentConfigGroup=["General"]; ws[w].writeConfig("icon","t3-gemstone"); } } }' \
        >/dev/null 2>&1 || true
fi

touch "${STATE_DIR}/applied"
