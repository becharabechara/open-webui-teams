#!/bin/bash

# Ensure /sandbox/persistent is owned by jovyan (UID 1000, GID 100)
chown -R 1000:100 /sandbox/persistent

# Switch to jovyan user and execute the notebook server
exec gosu jovyan start-notebook.sh --NotebookApp.base_url=/jupyter --NotebookApp.allow_origin='*' --notebook-dir=/sandbox/persistent --log-level=DEBUG