#!/bin/bash

#  --model-settings-file ~/model.settings.yml \
#  --restore-chat-history \

. ~/virtualenvs/aider_dev/bin/activate

aider \
  --read CONVENTIONS.md \
  --llm-command "gemini_mod"
  
