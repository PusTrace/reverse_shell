
all: client

s:
	python server.py

client:
	gcc client.c -o client

clean:
	rm -f server client

