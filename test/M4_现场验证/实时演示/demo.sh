#!/usr/bin/env bash
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
case "${1:-start}" in
  moving|video|approach|sweep) shift; exec python3 "$HERE/console.py" start "$@" ;;
  restart) shift; python3 "$HERE/console.py" stop; exec python3 "$HERE/console.py" start "$@" ;;
  sim) shift; exec python3 "$HERE/console.py" start --mode sim "$@" ;;
  *) exec python3 "$HERE/console.py" "$@" ;;
esac
