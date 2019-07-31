#! /bin/bash -

cd ~/stanford-intern-2019/website || return
jupyter notebook --port 8888 --ip 172.31.24.1 --no-browser