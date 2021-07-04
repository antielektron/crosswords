# crosswords

A little project experimenting with crossword generation using dumps from the wiktionary project

At the current status a simple first  version of server and client is ready and availble at https://antielektron.github.io/crosswords/ for testing.



Projekt structure:

* `./data` : jupyter notbooks to generate json databases for German and English, containing words and their hints.
* `./server` a websocket backend server, communicating with the client via json
* `./js_client` javascript client 

