import socket
import threading
import tkinter as tk
from tkinter import messagebox

# Server connection details
HOST = '127.0.0.1'
PORT = 5002

# UI theme settings
UI = {
    "bg": "#f4f4f4",
    "fg": "#1f1f1f",
    "accent": "#4a90e2",
    "button": "#1e88e5",
    "danger": "#e53935",
    "success": "#43a047",
    "font": "Helvetica Neue"
}

class QuizClientGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Quiz Game")
        self.master.geometry("640x480")
        self.master.configure(bg=UI["bg"])
        
        # Variable for tracking disconnect overlay
        self.disconnect_overlay = None
        
        # Create client socket and connect to server
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client.connect((HOST, PORT))
        except ConnectionRefusedError:
            messagebox.showerror("Connection Error", "Could not connect to the server. Please ensure the server is running.")
            self.master.destroy()
            return
        except socket.gaierror:
            messagebox.showerror("Connection Error", "Invalid hostname or IP address.")
            self.master.destroy()
            return
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            self.master.destroy()
            return

        # Variables to manage state
        self.nickname = ""
        self.current_question = tk.StringVar()
        self.scoreboard_text = tk.StringVar()
        self.timer_text = tk.StringVar()
        self.answer_buttons = []
        self.answered = False
        self.timer_running = False
        self.timer_id = None
        self.last_feedback = None

        # Show nickname input screen
        self.nickname_prompt()

    def nickname_prompt(self):
        # Display screen to ask the user for a nickname.
        self.clear_window()
        tk.Label(self.master, text="Welcome to Quizzie!\n\n What's your name?", 
                 font=(UI["font"], 20), bg=UI["bg"], fg=UI["fg"]).pack(pady=40)
        self.entry = tk.Entry(self.master, font=(UI["font"], 16), width=25, bg="white")
        self.entry.pack(pady=15)
        tk.Button(self.master, text="Join Game", font=(UI["font"], 14), bg=UI["button"], fg="black",
                  command=self.send_nickname).pack(pady=20)

    def send_nickname(self):
        # Send the nickname to the server and start receiving messages.
        self.nickname = self.entry.get()
        if self.nickname:
            try:
                self.client.sendall(self.nickname.encode())
                threading.Thread(target=self.receive_messages, daemon=True).start()
                self.show_waiting_message("\u23f3 Waiting for players...")
            except ConnectionError:
                messagebox.showerror("Connection Error", "Lost connection to the server while sending nickname.")
                self.master.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred while sending nickname: {str(e)}")
        else:
            messagebox.showwarning("Nickname Missing", "Please enter a nickname to join.")

    def show_waiting_message(self, message):
        # Display a waiting message (e.g. waiting for players).
        try:
            self.clear_window()
            self.waiting_label = tk.Label(self.master, text=message, font=(UI["font"], 18), bg=UI["bg"], fg=UI["accent"])
            self.waiting_label.pack(pady=140)
        except Exception as e:
            messagebox.showerror("UI Error", f"Failed to display waiting message: {str(e)}")

    def show_question(self, text):
        # Display a question and answer buttons.
        try:
            self.clear_window()
            self.answered = False
            self.timer_running = True

            tk.Label(self.master, textvariable=self.current_question, wraplength=600,
                     font=(UI["font"], 16), bg=UI["bg"], fg=UI["fg"]).pack(pady=30)
            self.current_question.set(text)

            tk.Label(self.master, textvariable=self.timer_text, font=(UI["font"], 14),
                     bg=UI["bg"], fg=UI["danger"]).pack()

            # Create answer buttons
            btn_frame = tk.Frame(self.master, bg=UI["bg"])
            btn_frame.pack(pady=20)

            self.answer_buttons = []
            for ch in ['A', 'B', 'C', 'D']:
                btn = tk.Button(
                    btn_frame,
                    text=ch,
                    width=12, height=3,
                    font=(UI["font"], 16),
                    relief='raised', bd=2,
                    command=lambda c=ch: self.send_answer(c),
                    bg=UI["button"], fg="black",
                    activebackground="#1565C0", activeforeground="white",
                    cursor="hand2"
                )
                btn.pack(side=tk.LEFT, padx=15, pady=10)
                self.answer_buttons.append(btn)

            # Scoreboard
            tk.Label(self.master, textvariable=self.scoreboard_text, font=(UI["font"], 14),
                     bg=UI["bg"], fg=UI["success"]).pack(pady=15)

            self.start_timer(20)
        except Exception as e:
            messagebox.showerror("UI Error", f"Failed to display question: {str(e)}")

    def start_timer(self, seconds):
        # Start countdown timer for answering the question.
        try:
            if self.timer_running:
                if seconds > 0:
                    self.timer_text.set(f"\u23f1 Time left: {seconds} sec")
                    self.timer_id = self.master.after(1000, self.start_timer, seconds - 1)
                else:
                    self.timer_text.set("\u274c Time's up!")
                    self.disable_buttons()
        except Exception as e:
            print(f"Timer error: {str(e)}")  # Using print since messagebox might disrupt the UI flow

    def send_answer(self, choice):
        # Send selected answer to the server.
        if not self.answered:
            try:
                self.client.sendall(choice.encode())
                self.answered = True
                self.disable_buttons()
                
                # Show a temporary message that your answer has been submitted
                self.show_answer_submitted_message()
                
            except ConnectionResetError:
                messagebox.showerror("Connection Error", "Connection was reset by the server.")
                self.master.destroy()
            except ConnectionAbortedError:
                messagebox.showerror("Connection Error", "Connection was aborted.")
                self.master.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Could not send answer: {str(e)}")
                
    def show_answer_submitted_message(self):
        # Show a temporary message that answer was submitted and we're waiting for others
        try:
            msg_frame = tk.Frame(self.master, bg=UI["bg"])
            msg_frame.pack(pady=5)
            
            submitted_label = tk.Label(
                msg_frame, 
                text="Answer submitted! Waiting for other players...",
                font=(UI["font"], 12),
                bg=UI["bg"],
                fg=UI["accent"]
            )
            submitted_label.pack(pady=10)
            
            # Auto-destroy after 3 seconds if no other response comes from server
            self.master.after(3000, lambda: submitted_label.destroy() if submitted_label.winfo_exists() else None)
        except Exception as e:
            print(f"Error showing answer submitted message: {str(e)}")

    def disable_buttons(self):
        # Disable all answer buttons and stop the timer.
        try:
            self.timer_running = False
            if self.timer_id:
                self.master.after_cancel(self.timer_id)
                self.timer_id = None
            for btn in self.answer_buttons:
                btn.config(state=tk.DISABLED)
        except Exception as e:
            print(f"Error disabling buttons: {str(e)}")  # Using print to avoid disrupting UI

    def color_buttons(self, is_correct):
        # Change the color of buttons based on correctness.
        try:
            for btn in self.answer_buttons:
                if btn['state'] == tk.DISABLED:
                    btn.config(bg=UI["success"] if is_correct else UI["danger"])
            self.master.update()
        except Exception as e:
            print(f"Error coloring buttons: {str(e)}")  # Using print to avoid disrupting UI

    def animate_score(self):
        # Visual animation when score changes (green for correct, red for incorrect)
        try:
            if self.answered:
                if self.last_feedback == "CORRECT":
                    self.master.after(100, lambda: self.master.config(bg="#e8f5e9"))  # Light green
                    self.master.after(400, lambda: self.master.config(bg=UI["bg"]))
                else:
                    self.master.after(100, lambda: self.master.config(bg="#ffebee"))  # Light red
                    self.master.after(400, lambda: self.master.config(bg=UI["bg"]))
        except Exception as e:
            print(f"Animation error: {str(e)}")  # Using print to avoid disrupting UI

    def receive_messages(self):
        # Continuously receive and handle messages from the server.
        while True:
            try:
                msg = self.client.recv(4096).decode()
                if not msg:  # Connection closed by server
                    raise ConnectionError("Server closed the connection")
                
                if msg.startswith("QUESTION||"):
                    self.show_question(msg.replace("QUESTION||", ""))
                elif msg.startswith("SCORE||"):
                    self.scoreboard_text.set(msg.replace("SCORE||", ""))
                elif msg.startswith("FINAL||"):
                    self.clear_window()
                    tk.Label(self.master, text=msg.replace("FINAL||", ""), font=(UI["font"], 16),
                             bg=UI["bg"], fg=UI["fg"], wraplength=600).pack(pady=100)
                elif msg.startswith("STATUS||"):
                    self.show_waiting_message(msg.replace("STATUS||", ""))
                elif msg.startswith("WAIT_DISCONNECT||"):
                    # Show a message that we're waiting because a player disconnected
                    # This could be an overlay on the current question screen
                    self.show_disconnect_wait_message(msg.replace("WAIT_DISCONNECT||", ""))
                elif msg.startswith("RESUME_AFTER_DISCONNECT||"):
                    # Remove the disconnect wait message if it exists
                    self.remove_disconnect_wait_message()
                elif msg.startswith("FEEDBACK||"):
                    status = msg.replace("FEEDBACK||", "")
                    self.last_feedback = status  # Store the feedback status
                    self.color_buttons(is_correct=(status == "CORRECT"))
                    self.animate_score()
            except ConnectionResetError:
                self.master.after(0, lambda: messagebox.showerror("Disconnected", "Connection was reset by the server."))
                break
            except ConnectionAbortedError:
                self.master.after(0, lambda: messagebox.showerror("Disconnected", "Connection was aborted."))
                break
            except socket.timeout:
                self.master.after(0, lambda: messagebox.showwarning("Timeout", "Connection timed out. Trying to reconnect..."))
                try:
                    self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.client.connect((HOST, PORT))
                    if self.nickname:
                        self.client.sendall(self.nickname.encode())
                except Exception:
                    self.master.after(0, lambda: messagebox.showerror("Reconnection Failed", "Could not reconnect to server."))
                    break
            except Exception as e:
                self.master.after(0, lambda: messagebox.showerror("Disconnected", f"Lost connection to server: {str(e)}"))
                break

    def show_disconnect_wait_message(self, message):
        # Display an overlay message when a player disconnects
        try:
            # Create a semi-transparent overlay frame
            self.disconnect_overlay = tk.Frame(self.master, bg="#333333", bd=2)
            self.disconnect_overlay.place(relx=0.5, rely=0.5, relwidth=0.8, relheight=0.3, anchor="center")
            
            # Create the message with the player's name
            wait_msg = tk.Label(
                self.disconnect_overlay,
                text=message,
                font=(UI["font"], 14, "bold"),
                bg="#333333",
                fg="#ffffff",
                wraplength=500
            )
            wait_msg.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
            
        except Exception as e:
            print(f"Error showing disconnect message: {str(e)}")
    
    def remove_disconnect_wait_message(self):
        # Remove the disconnect wait message overlay
        try:
            if self.disconnect_overlay:
                self.disconnect_overlay.destroy()
                self.disconnect_overlay = None
        except Exception as e:
            print(f"Error removing disconnect message: {str(e)}")
    
    def clear_window(self):
        # Remove all widgets from the window and reset timer state.
        try:
            for widget in self.master.winfo_children():
                widget.destroy()
            self.disconnect_overlay = None  # Reset overlay reference
            self.timer_running = False
            if self.timer_id:
                self.master.after_cancel(self.timer_id)
                self.timer_id = None
        except Exception as e:
            print(f"Error clearing window: {str(e)}")  # Using print to avoid disrupting UI

def main():
    try:
        root = tk.Tk()
        app = QuizClientGUI(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Application Error", f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()