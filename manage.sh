#!/bin/bash
# Manage experiments on EC2
# Usage:
#   ./manage.sh status          - show what's running
#   ./manage.sh start 1 3 6    - start test1, test3, test6
#   ./manage.sh stop 1 3       - stop test1, test3
#   ./manage.sh stop all       - stop everything
#   ./manage.sh start all      - start everything

SSH="ssh -i ~/.ssh/kev-aws-learning.pem ubuntu@32.194.2.97"
REMOTE_PATH="/home/ubuntu/aws-learning"

case "$1" in
  status)
    $SSH 'ps aux | grep uvicorn | grep -v grep | sed "s/.*--port /Port: /" | sed "s/ .*//"' 2>/dev/null
    running=$($SSH 'pgrep -c -f uvicorn 2>/dev/null || echo 0')
    echo "--- $running experiment(s) running ---"
    ;;

  start)
    shift
    if [ "$1" = "all" ]; then
      tests="1 2 3 4 5 6"
    else
      tests="$@"
    fi
    for n in $tests; do
      echo "Starting test${n}..."
      case $n in
        6)
          $SSH "bash -c 'export PATH=\$HOME/.local/bin:\$PATH; cd $REMOTE_PATH/test6-databases/api; set -a; source ../.env; set +a; nohup uv run uvicorn main:app --host 127.0.0.1 --port 8006 > /tmp/test6.log 2>&1 &'" 2>/dev/null
          ;;
        5)
          $SSH "bash -c 'export PATH=\$HOME/.local/bin:\$PATH; cd $REMOTE_PATH/test5-lambda/test; nohup uv run uvicorn local_server:app --host 127.0.0.1 --port 8005 > /tmp/test5.log 2>&1 &'" 2>/dev/null
          ;;
        *)
          dir=$(ls -d $REMOTE_PATH/test${n}-* 2>/dev/null | head -1)
          $SSH "bash -c 'export PATH=\$HOME/.local/bin:\$PATH; cd $REMOTE_PATH/test${n}-*/api; nohup uv run uvicorn main:app --host 127.0.0.1 --port 800${n} > /tmp/test${n}.log 2>&1 &'" 2>/dev/null
          ;;
      esac
    done
    sleep 2
    $0 status
    ;;

  stop)
    shift
    if [ "$1" = "all" ]; then
      echo "Stopping all experiments..."
      $SSH "killall -q uvicorn 2>/dev/null; sleep 1; killall -q python 2>/dev/null" 2>/dev/null
    else
      for n in "$@"; do
        port="800${n}"
        echo "Stopping test${n} (port $port)..."
        $SSH "kill \$(lsof -ti:$port) 2>/dev/null" 2>/dev/null
      done
    fi
    sleep 1
    $0 status
    ;;

  *)
    echo "Usage: ./manage.sh {status|start|stop} [test numbers or 'all']"
    echo ""
    echo "Examples:"
    echo "  ./manage.sh status"
    echo "  ./manage.sh start 6        # just test6"
    echo "  ./manage.sh start 1 3 6    # test1, test3, test6"
    echo "  ./manage.sh stop 1 3       # stop test1 and test3"
    echo "  ./manage.sh stop all       # stop everything"
    echo "  ./manage.sh start all      # start everything"
    ;;
esac
