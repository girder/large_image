test:
	docker-compose exec large_image cmake -DPYTHON_EXECUTABLE:FILEPATH=/usr/bin/python3 girder
	docker-compose exec large_image make
	docker-compose exec large_image ctest -VV -R mapnik
