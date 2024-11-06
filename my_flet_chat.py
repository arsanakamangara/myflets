import flet as ft
import socket
import threading
import os
import uuid

# Get the port from the environment variable (for Render deployment)
PORT = int(os.getenv('PORT', 5002))  # Default to 5002 if not provided
LOCAL_IP = "0.0.0.0"  # Allow connections from any IP (as Render will handle it)
ROOM_ADDRESS = f"http://{LOCAL_IP}:{PORT}"
connected_clients = []

# Use UUID for unique room identification
def generate_room_uuid():
    return str(uuid.uuid4())

# Create a unique room address based on UUID
ROOM_UUID = generate_room_uuid()
ROOM_ADDRESS = f"http://{LOCAL_IP}:{PORT}/{ROOM_UUID}"

# Automatically detect local IP address for hosting (for local testing, not needed in Render)
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((LOCAL_IP, PORT))
    server_socket.listen()
    print(f"Server started on {ROOM_ADDRESS}, waiting for connections...")
    
    while True:
        client_socket, address = server_socket.accept()
        print(f"Connection from {address} has been established!")
        connected_clients.append(client_socket)
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

def handle_client(client_socket):
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if not message:
                break
            print(f"Received message: {message}")
            broadcast_message(message)
        except:
            break
    client_socket.close()
    connected_clients.remove(client_socket)

def broadcast_message(message):
    for client in connected_clients:
        try:
            client.send(message.encode('utf-8'))
        except:
            client.close()
            connected_clients.remove(client)

class Message:
    def __init__(self, user_name: str, text: str, message_type: str):
        self.user_name = user_name
        self.text = text
        self.message_type = message_type

class ChatMessage(ft.Row):
    def __init__(self, message: Message):
        super().__init__()
        self.vertical_alignment = ft.CrossAxisAlignment.START
        self.controls = [
            ft.CircleAvatar(
                content=ft.Text(self.get_initials(message.user_name)),
                color=ft.colors.WHITE,
                bgcolor=self.get_avatar_color(message.user_name),
            ),
            ft.Column(
                [
                    ft.Text(message.user_name, weight="bold"),
                    ft.Text(message.text, selectable=True, size=20, font_family="Shabnam"),
                ],
                tight=True,
                spacing=5,
            ),
        ]

    def get_initials(self, user_name: str):
        return user_name[:1].capitalize() if user_name else "?"

    def get_avatar_color(self, user_name: str):
        colors_lookup = [
            ft.colors.AMBER,
            ft.colors.BLUE,
            ft.colors.BROWN,
            ft.colors.CYAN,
            ft.colors.GREEN,
            ft.colors.INDIGO,
            ft.colors.LIME,
            ft.colors.ORANGE,
            ft.colors.PINK,
            ft.colors.PURPLE,
            ft.colors.RED,
            ft.colors.TEAL,
            ft.colors.YELLOW,
        ]
        return colors_lookup[hash(user_name) % len(colors_lookup)]

def main(page: ft.Page):
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    page.title = "Flet Chat"
    global chat, new_message, join_room_dialog
    chat = None
    new_message = None
    join_room_dialog = None

    def on_message(message: Message):
        if chat is None:
            return
        if message.message_type == "chat_message":
            chat.controls.append(ChatMessage(message))
            page.update()
        elif message.message_type == "login_message":
            chat.controls.append(ft.Text(f"{message.user_name} joined the room!", italic=True, color=ft.colors.GREEN))
            page.update()

    def on_message_received_from_terminal(message_text):
        try:
            user_name, text = message_text.split(":", 1)
            if user_name != page.session.get("user_name"):  # Avoid showing own messages again
                message = Message(user_name.strip(), text.strip(), message_type="chat_message")
                on_message(message)
        except ValueError:
            print("Error in message format")

    join_user_name = ft.TextField(
        label="Enter your name to join the chat",
        autofocus=True,
        on_submit=lambda _: start_chat(),
    )
    
    join_dialog = ft.AlertDialog(
        open=True,
        modal=True,
        title=ft.Text("Welcome!"),
        content=ft.Column([join_user_name], width=300, height=70, tight=True),
        actions=[ft.ElevatedButton(text="Join chat", on_click=lambda _: start_chat())],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.overlay.append(join_dialog)
    page.update()

    def start_chat():
        user_name = join_user_name.value.strip()
        if user_name:
            page.session.set("user_name", user_name)
            join_dialog.open = False
            page.update()
            show_room_selection()

    def show_room_selection():
        room_selection_dialog = ft.AlertDialog(
            open=True,
            modal=True,
            title=ft.Text("Choose an option"),
            content=ft.Column(
                [
                    ft.ElevatedButton("Create Room", on_click=create_room),
                    ft.ElevatedButton("Join Room", on_click=join_room),
                ],
                tight=True,
                spacing=10,
            ),
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(room_selection_dialog)
        page.update()

    def show_room_address():
        room_address_dialog = ft.AlertDialog(
            open=True,
            modal=True,
            title=ft.Text("Room Created!"),
            content=ft.Text(f"Your room address: {ROOM_ADDRESS}", color=ft.colors.GREEN),
            actions=[
                ft.ElevatedButton("Copy Address", on_click=lambda _: copy_room_address()),
                ft.ElevatedButton("Close", on_click=lambda _: close_room_dialog(room_address_dialog)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(room_address_dialog)
        page.update()

    def copy_room_address():
        page.set_clipboard(ROOM_ADDRESS)
        print("Room address copied to clipboard.")

    def close_room_dialog(dialog):
        dialog.open = False
        page.update()
        show_room_selection()

    server_started = False

    def create_room(e):
        nonlocal server_started
        if not server_started:
            threading.Thread(target=start_server, daemon=True).start()
            server_started = True
        show_room_address()

    def join_room(e):
        room_address_input = ft.TextField(
            label="Enter room address",
            autofocus=True,
            on_submit=lambda _: connect_to_room(room_address_input),
        )

        global join_room_dialog
        join_room_dialog = ft.AlertDialog(
            open=True,
            modal=True,
            title=ft.Text("Join Room"),
            content=ft.Column([room_address_input], tight=True),
            actions=[
                ft.ElevatedButton("Connect", on_click=lambda _: connect_to_room(room_address_input)),
                ft.ElevatedButton("Cancel", on_click=lambda _: close_dialog(join_room_dialog)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.overlay.append(join_room_dialog)
        page.update()

    def close_dialog(dialog):
        dialog.open = False
        page.update()

    def connect_to_room(room_address_input):
        try:
            room_address = room_address_input.value.strip().split(":")
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((room_address[0], PORT))
            print("Connected to the room successfully!")
            initialize_chat(client_socket)
            close_dialog(join_room_dialog)
            threading.Thread(target=listen_for_messages, args=(client_socket,), daemon=True).start()
        except Exception as ex:
            print("Error connecting to room:", ex)

    def initialize_chat(client_socket):
        global chat, new_message
        chat = ft.ListView(
            expand=True,
            spacing=10,
            auto_scroll=True,
        )

        new_message = ft.TextField(
            hint_text="Write a message...",
            autofocus=True,
            shift_enter=True,
            min_lines=1,
            max_lines=5,
            filled=True,
            expand=True,
            on_submit=lambda _: send_message_click(client_socket),
        )

        page.controls.clear()
        page.add(
            ft.Container(
                content=chat,
                border=ft.border.all(1, ft.colors.OUTLINE),
                border_radius=5,
                padding=10,
                expand=True,
            ),
            ft.Row(
                [
                    new_message,
                    ft.IconButton(
                        icon=ft.icons.SEND_ROUNDED,
                        tooltip="Send message",
                        on_click=lambda _: send_message_click(client_socket),
                    ),
                ]
            ),
        )
        page.update()

    def send_message_click(client_socket):
        if new_message.value.strip() != "":
            user_name = page.session.get("user_name")
            message_text = new_message.value.strip()
            full_message = f"{user_name}: {message_text}"

            try:
                client_socket.send(full_message.encode('utf-8'))
                message = Message(user_name, message_text, message_type="chat_message")
                on_message(message)
                new_message.value = ""
                page.update()
            except Exception as ex:
                print("Failed to send message:", ex)

    def listen_for_messages(client_socket):
        while True:
            try:
                message_text = client_socket.recv(1024).decode('utf-8')
                if not message_text:
                    break
                on_message_received_from_terminal(message_text)
            except Exception as ex:
                print("Failed to receive message:", ex)
                break

ft.app(target=main)
