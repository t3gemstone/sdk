# ~/.bash_aliases

alias nano="nano -c"
alias ls="ls -lahF --color=always --group-directories-first"
alias ..='cd ..'

m:clr() {
    clear && printf '\e[3J' && tput reset
}

m:mk() {
    [ ! -z "$1" ] && mkdir -p $1 && cd $1 && return 0 || return 1
}

m:size() {
    local where=${1:-/}
    local level=${level:-1}
    sudo du -h -d $level --exclude=/{proc,sys,dev,mnt} $where | sort -h
}

m:find() {
    local what=$1
    local where=${2:-.}
    local extra=$3

    eval "sudo find $where -name $what $extra \
        -not -path '/dev/*' \
        -not -path '/sys/*' \
        -not -path '/tmp/*' \
        -not -path '/run/*' \
        -not -path './.local/share/Trash/*' \
        -not -path './.git/*';"
}

m:grep() {
    eval "sudo grep \"$1\" ${2:-$PWD} ${@%$1} \
        -rlFiI --color=always \
        --exclude-dir=.git \
        --exclude-dir=/run \
        --exclude-dir=/sys \
        --exclude-dir=/dev \
        --exclude-dir=/lib $3 2>/dev/null"
}

m:info() {
    local logfile=info.log
    rm -f $logfile && touch $logfile

    cmd() {
        echo -e "\n>> $1\n" >> $logfile
        eval $1 | sed 's/^/\t/' >> $logfile
    }

    # OS&Hardware info
    cmd "cat /etc/lsb-release"
    cmd "uname --all"
    cmd "df --human-readable"

    # Installed apps
    cmd "sudo apt list --installed"

    # Systemd services
    cmd "sudo systemctl list-unit-files"
    
    # Filesystem sizes
    cmd "m:size /"
    cmd "level=2 m:size /"
    cmd "level=3 m:size /"

    # Boot time
    cmd "sudo systemd-analyze blame"

    # dmesg
    cmd "sudo dmesg"

    # Journal
    cmd "sudo journalctl -b"

    # Modules
    cmd "sudo lsmod"
}

m:reload() {
    source $HOME/.bash_aliases
}

function m() {
    [ ! -z ${1+x} ] && eval m:$1 "${@:2}"
}

if [ -d $HOME/.bash_completion.d ]; then
    for i in $HOME/.bash_completion.d/*; do
        . $i
    done
fi
