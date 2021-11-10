. $HOME/.override_env
$(which python || which python3 || echo python) $GEONODE_ROOT/manage.py $@
