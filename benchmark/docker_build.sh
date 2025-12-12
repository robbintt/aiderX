#!/bin/bash

shopt -s expand_aliases
alias docker=podman

set -e

docker build \
       --file benchmark/Dockerfile \
       -t aider-benchmark \
       .
