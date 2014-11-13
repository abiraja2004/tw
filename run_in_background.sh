echo Starting $1...
nohup python $1.py $2 > $1.log 2>&1  &
echo $1 running.
echo 