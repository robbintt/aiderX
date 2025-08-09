#!/bin/bash

#  --model-settings-file ~/model.settings.yml \
#  --restore-chat-history \
#  --llm-command "gemini_mod"

. ~/virtualenvs/aider_dev/bin/activate

aider \
  --read CONVENTIONS.md \
  --llm-command "claude -p" \
  --edit-format diff
  
