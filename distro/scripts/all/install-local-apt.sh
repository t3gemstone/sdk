#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

MACHINE="$(printf '%s' "$1" | tr '-' '_')"

