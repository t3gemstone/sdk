#!/bin/bash
#
# T3 Foundation Gemstone Project [t3gemstone.org]
#
# This file is copied from the jetify.com/devbox
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

readonly TITLE="🚀 T3 Gemstone Software Development Kit"
readonly DOCS_URL="https://docs.t3gemstone.org"
readonly COMMUNITY_URL="https://community.t3gemstone.org"

readonly BOLD="$(tput bold 2>/dev/null || echo '')"
readonly GREY="$(tput setaf 8 2>/dev/null || echo '')"
readonly UNDERLINE="$(tput smul 2>/dev/null || echo '')"
readonly RED="$(tput setaf 1 2>/dev/null || echo '')"
readonly GREEN="$(tput setaf 2 2>/dev/null || echo '')"
readonly YELLOW="$(tput setaf 3 2>/dev/null || echo '')"
readonly BLUE="$(tput setaf 4 2>/dev/null || echo '')"
readonly MAGENTA="$(tput setaf 5 2>/dev/null || echo '')"
readonly CYAN="$(tput setaf 6 2>/dev/null || echo '')"
readonly NO_COLOR="$(tput sgr0 2>/dev/null || echo '')"
readonly CLEAR_LAST_MSG="\033[1F\033[0K"

readonly DESCRIPTION=$(
    cat <<EOF
  This script downloads and installs T3 Gemstone Board's required packages 📦 for the development of its GNU/Linux Distro.
  Powered by Jetify Devbox, Distrobox, ${BOLD}Love${NO_COLOR} and ${BOLD}Passion${NO_COLOR}.
EOF
)

SILENT="${SILENT:-0}"

parse_flags() {
    while [ "$#" -gt 0 ]; do
        case "$1" in
        -s | --silent)
            SILENT=1
            shift 1
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
        esac
    done
}

has() {
    command -v "$1" 1>/dev/null 2>&1
}

delay() {
    sleep ${1:-0.3}
}

title() {
    local -r text="$*"
    printf "\n%s\n" "${BOLD}${MAGENTA}${text}${NO_COLOR}"
}

header() {
    local -r text="$*"
    printf "%s\n" "${BOLD}${text}${NO_COLOR}"
}

plain() {
    local -r text="$*"
    printf "%s\n" "${text}"
}

info() {
    local -r text="$*"
    printf "%s\n" "${BOLD}${GREY}→${NO_COLOR} ${text}"
}

warn() {
    local -r text="$*"
    printf "%s\n" "${YELLOW}! $*${NO_COLOR}"
}

error() {
    local -r text="$*"
    printf "%s\n" "${RED}✘ ${text}${NO_COLOR}" >&2
}

success() {
    local -r text="$*"
    printf "%s\n" "${GREEN}✓${NO_COLOR} ${text}"
}

start_task() {
    local -r text="$*"
    printf "%s\n" "${BOLD}${GREY}→${NO_COLOR} ${text}..."
}

end_task() {
    local -r text="$*"
    printf "${CLEAR_LAST_MSG}%s\n" "${GREEN}✓${NO_COLOR} ${text}... [DONE]"
}

fail_task() {
    local -r text="$*"
    printf "${CLEAR_LAST_MSG}%s\n" "${RED}✘ ${text}... [FAILED]${NO_COLOR}" >&2
}

check_requirements() {
    start_task requirements
    for i in "curl" "git" "sudo"; do
        if ! has "$i"; then
            echo "$i must be installed to start the setup! For Help: $DOCS_URL/sdk"
            fail_task
            return 1
        fi
    done
    success
    end_task requirements
}

install_docker() {
    start_task docker
    has docker && success || { curl -fsSL https://get.docker.com | sh && success || fail_task; }
    end_task docker
}

set_docker_perms() {
    start_task docker-permissions

    if ! has docker; then
        error "Docker is not found, permissions could not set."
        fail_task
    elif id -nG "$USER" | grep -qwv "docker"; then
        info "sudo groupadd docker && sudo usermod -aG docker $USER"
        sudo groupadd docker || true
        sudo usermod -aG docker $USER || true
        warn "You should log out and log back in so that your docker group membership is re-evaluated."
        success
    fi

    end_task docker-permissions
}

install_devbox() {
    start_task devbox
    has "devbox" && success || { curl -fsSL https://get.jetify.com/devbox | bash && success || fail_task; }
    end_task devbox
}

intro_msg() {
    title "${TITLE}"
    printf "\n"
    plain "${DESCRIPTION}"
    printf "\n"
}

next_steps_msg() {
    printf "\n"
    header "What's the next?"
    plain "  1. ${BOLD}Learn how to build 🌍 a new world${NO_COLOR}"
    plain "     ${GREY}Read the docs at ${UNDERLINE}${BLUE}${DOCS_URL}${NO_COLOR}"
    plain "  2. ${BOLD}Get help and give feedback${NO_COLOR}"
    plain "     ${GREY}Join our community at ${UNDERLINE}${BLUE}${COMMUNITY_URL}${NO_COLOR}"
    printf "\n"
}

main() {
    intro_msg
    delay 3
    check_requirements
    install_docker
    set_docker_perms
    install_devbox
    next_steps_msg
}

main "$@"
