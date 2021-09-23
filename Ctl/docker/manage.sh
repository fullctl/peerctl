SERVICE_HOME=/src/peerctl
VIRTUAL_ENV=venv


. "$SERVICE_HOME/$VIRTUAL_ENV/bin/activate"
cd "$SERVICE_HOME/main"

./manage.py $@
