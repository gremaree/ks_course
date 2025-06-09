import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import socket
import protocol
import client
import server
import os
import matplotlib.pyplot as plt


class UDPCommunicatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("UDP Communicator")
        self.root.geometry("500x400")

        # Переменные для полей ввода
        self.mode_var = tk.StringVar(value="client")  # "клиент" или "сервер"
        self.ip_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.IntVar(value=5000)
        self.client_port_var = tk.IntVar(value=5001)
        self.fragment_size_var = tk.IntVar(value=1024)
        self.file_path_var = tk.StringVar()
        self.message_var = tk.StringVar()
        self.dir_path_var = tk.StringVar(value=os.getcwd() + "/")  # По умолчанию текущий каталог
        self.simulate_error_var = tk.BooleanVar(value=False)

        
        self._build_ui()

    def _build_ui(self):
        # Выбор режима(Клиент/Сервер)
        tk.Label(self.root, text="Режим:").grid(row=0, column=0, padx=10, pady=5)
        tk.Radiobutton(self.root, text="Клиент", variable=self.mode_var, value="client", command=self.update_ui).grid(
            row=0, column=1, padx=10, pady=5)
        tk.Radiobutton(self.root, text="Сервер", variable=self.mode_var, value="server", command=self.update_ui).grid(
            row=0, column=2, padx=10, pady=5)

        # IP адрес (для клиента)
        self.ip_label = tk.Label(self.root, text="IP адрес сервера:")
        self.ip_entry = tk.Entry(self.root, textvariable=self.ip_var)

        # Порт сервера (для клиента и сервера)
        self.port_label = tk.Label(self.root, text="Порт сервера:")
        self.port_entry = tk.Entry(self.root, textvariable=self.port_var)

        # Порт клиента (для клиента)
        self.client_port_label = tk.Label(self.root, text="Порт клиента:")
        self.client_port_entry = tk.Entry(self.root, textvariable=self.client_port_var)

        # Размер фрагмента (для клиента)
        self.fragment_size_label = tk.Label(self.root, text="Размер фрагмента:")
        self.fragment_size_entry = tk.Entry(self.root, textvariable=self.fragment_size_var)
        self.simulate_error_check = tk.Checkbutton(self.root, text="Симуляция ошибки", variable=self.simulate_error_var)

        # Путь к файлу (для клиента)
        self.file_path_label = tk.Label(self.root, text="Путь к файлу:")
        self.file_path_entry = tk.Entry(self.root, textvariable=self.file_path_var, state="readonly")
        self.file_browse_button = tk.Button(self.root, text="Обзор", command=self.choose_file)

        # Сообщение (для клиента)
        self.message_label = tk.Label(self.root, text="Сообщение:")
        self.message_entry = tk.Entry(self.root, textvariable=self.message_var)

        # Путь к каталогу (для сервера)
        self.dir_path_label = tk.Label(self.root, text="Каталог хранения:")
        self.dir_path_entry = tk.Entry(self.root, textvariable=self.dir_path_var, state="readonly")
        self.dir_browse_button = tk.Button(self.root, text="Обзор", command=self.choose_directory)

        # Кнопка запуска
        self.start_button = tk.Button(self.root, text="Запуск", command=self.start_process)

        self.update_ui()

    def update_ui(self):
        """ Обновление UI в зависимости от выбранного режима. """
        mode = self.mode_var.get()

        self.ip_label.grid_forget()
        self.ip_entry.grid_forget()
        self.port_label.grid_forget()
        self.port_entry.grid_forget()
        self.client_port_label.grid_forget()
        self.client_port_entry.grid_forget()
        self.fragment_size_label.grid_forget()
        self.fragment_size_entry.grid_forget()
        self.simulate_error_check.grid_forget()
        self.file_path_label.grid_forget()
        self.file_path_entry.grid_forget()
        self.file_browse_button.grid_forget()
        self.message_label.grid_forget()
        self.message_entry.grid_forget()
        self.dir_path_label.grid_forget()
        self.dir_path_entry.grid_forget()
        self.dir_browse_button.grid_forget()

        # Отображение элементов интерфейса в зависимости от режима
        if mode == "client":
            self.ip_label.grid(row=1, column=0, padx=10, pady=5)
            self.ip_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=5)
            self.port_label.grid(row=2, column=0, padx=10, pady=5)
            self.port_entry.grid(row=2, column=1, columnspan=2, padx=10, pady=5)
            self.client_port_label.grid(row=3, column=0, padx=10, pady=5)
            self.client_port_entry.grid(row=3, column=1, columnspan=2, padx=10, pady=5)
            self.fragment_size_label.grid(row=4, column=0, padx=10, pady=5)
            self.fragment_size_entry.grid(row=4, column=1, columnspan=2, padx=10, pady=5)
            self.simulate_error_check.grid(row=5, column=0, columnspan=3, padx=10, pady=5)
            self.file_path_label.grid(row=6, column=0, padx=10, pady=5)
            self.file_path_entry.grid(row=6, column=1, padx=10, pady=5)
            self.file_browse_button.grid(row=6, column=2, padx=10, pady=5)
            self.message_label.grid(row=7, column=0, padx=10, pady=5)
            self.message_entry.grid(row=7, column=1, columnspan=2, padx=10, pady=5)
        else:  # для сервера
            self.port_label.grid(row=1, column=0, padx=10, pady=5)
            self.port_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=5)
            self.dir_path_label.grid(row=2, column=0, padx=10, pady=5)
            self.dir_path_entry.grid(row=2, column=1, padx=10, pady=5)
            self.dir_browse_button.grid(row=2, column=2, padx=10, pady=5)

        self.start_button.grid(row=10, column=0, columnspan=3, pady=10)

    def choose_file(self):
        """ Диалоговое окно для выбора файла """
        file_path = filedialog.askopenfilename()
        if file_path:
            self.file_path_var.set(file_path)

    def choose_directory(self):
        """ Диалоговое окно для выбора каталога сохранения. """
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.dir_path_var.set(dir_path + "/")

    def start_process(self):
        """ Запуск процесса в зависимости от выбранного режима (клиент или сервер). """
        mode = self.mode_var.get()
        if mode == "client":
            self.start_client()
        else:
            self.start_server()

    def start_client(self):
        file_path = self.file_path_var.get()
        message = self.message_var.get()

        if not file_path and not message:
            messagebox.showerror("Ошибка", "Пожалуйста, укажите файл или сообщение для отправки.")
            return

        # симуляция ошибки
        client.user_input_mistake = 'д' if self.simulate_error_var.get() else 'н'

        # Запуск клиента в отдельном потоке
        thread = threading.Thread(target=self.run_client, args=(file_path, message))
        thread.start()

    def run_client(self, file_path, message):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", self.client_port_var.get()))

            if file_path:
                client.send_file(
                    server_ip=self.ip_var.get(),
                    client_socket=sock,
                    server_port=self.port_var.get(),
                    fragment_size=self.fragment_size_var.get() + protocol.HEADER_SIZE,
                    file_path=file_path.encode('utf-8')
                )
            elif message:
                client.send_message(
                    server_ip=self.ip_var.get(),
                    client_socket=sock,
                    server_port=self.port_var.get(),
                    fragment_size=self.fragment_size_var.get(),
                    message=message.encode('utf-8')
                )

        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
        finally:
            sock.close()

    def start_server(self):
        """ Запуск процесса сервера. """
        thread = threading.Thread(target=self.run_server)
        thread.start()

    def run_server(self):
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            server_socket.bind(("", self.port_var.get()))

           
            server.receive(server_socket, self.dir_path_var.get())
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
        finally:
            server_socket.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = UDPCommunicatorApp(root)
    root.mainloop()
