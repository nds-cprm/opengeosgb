up:
	# bring up the services
	docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

build:
	docker-compose build django
	docker-compose build celery

sync:
	# TODO: Review sync make. Not working, yet
	# set up the database tables
	docker-compose run django python manage.py makemigrations --noinput
	docker-compose exec django python manage.py migrate account --noinput
	docker-compose run django python manage.py migrate --noinput

wait:
	sleep 5

logs:
	docker-compose -f docker-compose.yml -f docker-compose.override.yml logs --follow

down:
	docker-compose -f docker-compose.yml -f docker-compose.override.yml down

test:
	# TODO: Review test make. Not working, yet
	docker-compose -f docker-compose.yml -f docker-compose.override.yml run django python manage.py test --failfast

reset: down up wait sync

hardreset: pull build reset
