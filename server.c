
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/select.h>

#define PORT 54321
#define BUFFER_SIZE 1024

void process_output(char *buffer);

// network
int create_server() {
    int server_fd;
    struct sockaddr_in address;

    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("socket");
        exit(EXIT_FAILURE);
    }

    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);

    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        perror("bind");
        exit(EXIT_FAILURE);
    }

    if (listen(server_fd, 5) < 0) {
        perror("listen");
        exit(EXIT_FAILURE);
    }

    return server_fd;
}

int accept_client(int server_fd) {
    struct sockaddr_in address;
    int addrlen = sizeof(address);

    int client_fd = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen);
    if (client_fd < 0) {
        perror("accept");
        return -1;
    }

    printf("Клиент подключился\n");
    return client_fd;
}


// logic


// sender
const char* process_request(char *buffer) {
    if (strstr(buffer, "type: init") != NULL) {
        return "type: ok\n";
    }
    return "type: error, payload: unknown\n";
}

// readers
void handle_client(int client_fd) {
    char buffer[BUFFER_SIZE];
    fd_set readfds;

    while (1) {
        FD_ZERO(&readfds);
        FD_SET(client_fd, &readfds);
        FD_SET(STDIN_FILENO, &readfds);

        int max_fd = client_fd > STDIN_FILENO ? client_fd : STDIN_FILENO;

        int activity = select(max_fd + 1, &readfds, NULL, NULL, NULL);

        if (activity < 0) {
            perror("select");
            break;
        }

        // 📥 данные от клиента
        if (FD_ISSET(client_fd, &readfds)) {
            int bytes = recv(client_fd, buffer, BUFFER_SIZE - 1, 0);

            if (bytes <= 0) {
                printf("Клиент отключился\n");
                break;
            }

            buffer[bytes] = '\0';
            
            process_output(buffer);
            
        }

        // ⌨️ ввод с сервера → отправка клиенту
        if (FD_ISSET(STDIN_FILENO, &readfds)) {
            if (fgets(buffer, BUFFER_SIZE, stdin) != NULL) {

                // убираем '\n', иначе будет мусор
                buffer[strcspn(buffer, "\n")] = 0;

                char message[BUFFER_SIZE];
                snprintf(message, sizeof(message), "type: message, payload: %s\n", buffer);

                send(client_fd, message, strlen(message), 0);

                printf("Отправлено клиенту: %s\n", message);
            }
        }
    }

    close(client_fd);
}

void process_output(char *buffer) {
    if (strstr(buffer, "client_line") != NULL) {

        char *payload = strstr(buffer, "payload:");

        if (payload != NULL) {
            payload += strlen("payload:");  // сдвигаемся к значению

            // убираем пробелы в начале
            while (*payload == ' ') payload++;
           
            printf("%s\n", payload);
        } else {
            printf("payload не найден\n");
        }
    }
}

// start
int main() {
    int server_fd = create_server();

    printf("Сервер запущен...\n");

    while (1) {
        int client_fd = accept_client(server_fd);
        if (client_fd < 0) continue;

        handle_client(client_fd);
    }

    close(server_fd);
    return 0;
}

