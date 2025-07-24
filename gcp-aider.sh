#!/bin/bash

MODEL=gemini/gemini-2.5-pro
#EDITOR_MODEL=google/gemini-2.5-flash


# These notes are only in this file:
#
#  --model $MODEL \
#  --edit-format architect \
#  --editor-model $EDITOR_MODEL \
#  --editor-edit-format whole \

# input color doesnt work with dark mode
#  --user-input-color "#eb6521" \
#
# this is useful sometimes
#  --thinking-tokens 128 \

#  --restore-chat-history \

# should no longer be needed.
#  --model-settings-file scripts/model.settings.yml \

# need to turn off when modifying with project.yml (mostly creating new files, some devops)
#  --yes-always \ 
aider \
  --model $MODEL \
  --model-settings-file ~/model.settings.yml
