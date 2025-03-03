alias t='task'
alias nano="nano -c"
alias ls="ls -lahF --color=always --group-directories-first"
alias py='python3'
alias bb='bitbake'
alias ..='cd ..'

m:clr() {
    clear && printf '\e[3J' && tput reset
}

m:mk() {
    [ ! -z "$1" ] && mkdir -p $1 && cd $1 && return 0 || return 1
}

m:size() {
    local where=${1:-/}
    sudo du -h -d 1 --exclude=/{proc,sys,dev,mnt} $where | sort -h
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

m:oeinit() {
    MACHINE="${1:-beagley-ai}"
    TEMPLATECONF="$WORKDIR/yocto/meta-gemstone/conf/templates/${MACHINE}" source $WORKDIR/yocto/poky/oe-init-build-env "$WORKDIR/build/$MACHINE"
}

function m() {
    [ ! -z ${1+x} ] && eval m:$1 "${@:2}"
}

if [ -f $HOME/.bash_completion ]; then
    source $HOME/.bash_completion
    complete -F _complete_alias t
    complete -F _complete_alias bb
fi

# Write the commands you want to run inside distrobox just after opening.
touch $HOME/.env && source $HOME/.env
