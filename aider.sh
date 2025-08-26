#!/bin/bash

#MODEL=gemini/gemini-2.5-pro-1p-freebie
#MODEL=gemini/gemini-2.5-pro
#MODEL=deepinfra/google/gemini-2.5-pro

# these are useful sometimes
#  --thinking-tokens 128 \
#  --restore-chat-history \
#  --yes-always \ 
# --use-jinja2-templates \
#  --model $MODEL

# install experimental aider via venv for now
. ~/virtualenvs/aider_dev/bin/activate
# stock aider (when i break things)
#. ~/virtualenvs/stock_aider/bin/activate

#aider --handlers file-adder --handlers potato-handler --controller-model gemini/gemini-2.5-flash

aider
