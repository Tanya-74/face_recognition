#!/bin/bash
# Usage: experiments/install_lib.sh <name> <pip packages...>
# Creates experiments/envs/<name>/.venv (Python 3.11), installs packages,
# logs full pip output + wall-clock time + exit code to experiments/results/install_logs/<name>.log
name=$1; shift
root="$(cd "$(dirname "$0")" && pwd)"
venv="$root/envs/$name/.venv"
log="$root/results/install_logs/$name.log"
mkdir -p "$root/envs/$name" "$root/results/install_logs"
start=$(date +%s)
{
  echo "### $(date -Is)  install '$*' for $name"
  [ -d "$venv" ] || py -3.11 -m venv "$venv"
  "$venv/Scripts/python.exe" -m pip install "$@"
  echo "### EXIT_CODE=$?"
} 2>&1 | tee -a "$log" | tail -25
echo "### SECONDS=$(( $(date +%s) - start ))" | tee -a "$log"
