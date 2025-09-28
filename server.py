import socket
import threading
import json
import time
import select

# Server configuration
HOST = '127.0.0.1'
PORT = 5002

# Client tracking
clients = {}            # Maps client sockets to nicknames
scores = {}             # Maps nicknames to their scores
ready_clients = []      # List of clients who joined and are ready
quiz_started = False    # Flag to indicate whether the quiz has started
lock = threading.Lock() # Lock for thread-safe operations
questions = []          # List to store quiz questions

# Constants
QUESTION_TIME_LIMIT = 20  # Time limit for each question in seconds
MIN_PLAYERS = 3           # Minimum players required to start the quiz

def load_questions():
    # Load quiz questions from a JSON file.
    with open('questions.json', 'r') as file:
        return json.load(file)

def broadcast(message):
    # Send a message to all connected clients.
    for client in list(clients.keys()):
        try:
            client.sendall(message.encode())
        except:
            remove_client(client)

def remove_client(client_socket):
    # Remove a disconnected client and clean up related data.
    with lock:
        if client_socket in clients:
            nickname = clients[client_socket]
            print(f"[-] {nickname} disconnected.")
            del clients[client_socket]
            del scores[nickname]
            if client_socket in ready_clients:
                ready_clients.remove(client_socket)

def handle_client(client_socket):
    # Handle a newly connected client.
    global quiz_started
    try:
        # Receive the nickname from the client
        nickname = client_socket.recv(1024).decode()
        with lock:
            # Register the client
            clients[client_socket] = nickname
            scores[nickname] = 0
            ready_clients.append(client_socket)
            print(f"[+] {nickname} joined. Total players: {len(ready_clients)}")

            # Notify clients of current status
            needed = max(0, MIN_PLAYERS - len(ready_clients))
            if needed > 0:
                status = f"⏳ {len(ready_clients)}/{MIN_PLAYERS} players connected. Waiting for {needed} more..."
            else:
                status = f"✅ {len(ready_clients)}/{MIN_PLAYERS} players connected. Starting quiz..."
            broadcast("STATUS||" + status)

            # Start quiz if enough players are connected
            if not quiz_started and len(ready_clients) >= MIN_PLAYERS:
                quiz_started = True
                threading.Thread(target=start_quiz, daemon=True).start()
    except:
        remove_client(client_socket)

def collect_answers(timeout_seconds, correct_answer):
    # Collect answers from all clients within a time limit.
    answers = {}
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        if len(answers) >= len(clients):
            break

        try:
            remaining = timeout_seconds - (time.time() - start_time)
            if remaining <= 0:
                break

            # Wait for readable client sockets
            readable, _, _ = select.select(list(clients.keys()), [], [], 1)
            for sock in readable:
                try:
                    data = sock.recv(1024)
                    if data:
                        answer = data.decode().strip().upper()
                        if sock not in answers:
                            answers[sock] = answer
                            # Only send feedback to the client who answered
                            nickname = clients.get(sock)
                            if nickname and answer == correct_answer:
                                scores[nickname] += 1
                                sock.sendall("FEEDBACK||CORRECT".encode())
                            else:
                                sock.sendall("FEEDBACK||WRONG".encode())
                except:
                    continue
        except:
            break

    # After all answers are collected or time is up, broadcast the scoreboard to everyone
    with lock:
        score_text = "\n[SCOREBOARD]\n"
        for name, score in sorted(scores.items(), key=lambda x: (-x[1], x[0])):
            score_text += f"{name}: {score} pts\n"
    broadcast("SCORE||" + score_text)

    return answers

def start_quiz():
    # Main quiz logic: send questions, collect answers, update scores.
    time.sleep(1)
    for idx, q in enumerate(questions):
        # Send question to all clients
        q_text = f"\n❓ Question {idx+1}: {q['question']}\nA) {q['A']}  B) {q['B']}  C) {q['C']}  D) {q['D']}\n⏱️ You have {QUESTION_TIME_LIMIT} seconds!"
        broadcast("QUESTION||" + q_text)

        # Collect and evaluate answers
        answers = collect_answers(QUESTION_TIME_LIMIT, q['answer'])
        
        # Wait a bit before next question
        time.sleep(2)

    # Final scores and winner announcement
    with lock:
        final_text = "\n🏁 FINAL SCORES 🏁\n"
        for name, score in sorted(scores.items(), key=lambda x: (-x[1], x[0])):
            final_text += f"{name}: {score} pts\n"
        top_score = max(scores.values())
        winners = [name for name, score in scores.items() if score == top_score]
        if len(winners) == 1:
            final_text += f"\n🏆 Winner: {winners[0]} 🏆"
        else:
            final_text += f"\n🤝 It's a draw between: {', '.join(winners)}"
        broadcast("FINAL||" + final_text)

def main():
    # Start the server and accept incoming client connections.
    global questions
    questions = load_questions()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVER] Running on {HOST}:{PORT}")

    while True:
        try:
            # Accept a new client
            client_socket, _ = server.accept()
            threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()
        except KeyboardInterrupt:
            print("\n[SERVER] Shutting down.")
            break

if __name__ == "__main__":
    main()
