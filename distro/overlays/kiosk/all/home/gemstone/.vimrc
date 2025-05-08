" ## General settings
filetype indent on
filetype plugin on
set backspace=eol,start,indent " Make backspace work like other editors in insert mode
set encoding=UTF-8 " Set character encoding
set history=100
set hlsearch
set ignorecase smartcase " By default ignore case when searching
                         " If intentionally uppercase letters are used in search then override ignorecase
set mouse=nvchr " Enable mouse for all modes except insert mode
set nobackup " Disable backup files
set novisualbell " Disable screen flashes
set scrolloff=4 " Set number of screen lines to always keep above and below the cursor
set splitbelow " Open horizontal splits to below
set splitright " Open vertical splits to right
set timeoutlen=800 " Shrink the window for time-outable commands

" ## Line numbers
set nocursorcolumn
set nocursorline
set number

" ## Whitespace settings
set expandtab
set shiftwidth=4
set smartindent
set softtabstop=4
set tabstop=4

" ## Visual settings
set shortmess+=c " Disable hit ENTER prompts for completion
set showtabline=2 " Always show tab line

" ## Commands
command! V e $MYVIMRC | cd %:h
