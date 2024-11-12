import json
import math
import os
import random
import textwrap
import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Optional, List, Dict


class GraphApp:
    def __init__(self, main_root: tk.Tk) -> None:
        # Ініціалізація головного вікна
        self.root = main_root
        self.root.title("Graph Application")
        self.root.geometry("600x400")

        # Файл для збереження даних графу між сесіями
        self.data_file = "graph_data.json"

        # Ліва панель для кнопок управління графом
        self.left_frame = tk.Frame(root, width=150, bg="lightgray")
        self.left_frame.pack(side="left", fill="y")

        # Кнопки для управління графом
        self.add_vertex_button = tk.Button(self.left_frame, text="Додати вершину", command=self.add_vertex)
        self.add_vertex_button.pack(pady=10, padx=10, fill="x")

        self.connect_vertices_button = tk.Button(self.left_frame, text="З’єднати вершини",
                                                 command=self.start_connect_vertices)
        self.connect_vertices_button.pack(pady=10, padx=10, fill="x")

        self.delete_element_button = tk.Button(self.left_frame, text="Видалити елемент",
                                               command=self.start_delete_element)
        self.delete_element_button.pack(pady=10, padx=10, fill="x")

        # Полотно для графу
        self.right_frame = tk.Canvas(root, bg="white")
        self.right_frame.pack(side="right", expand=True, fill="both")

        # Зберігання вершин і зв'язків
        self.vertices: List[Dict] = []
        self.connections: List[Dict] = []

        # Завантаження даних, якщо вони існують
        self.load_data_from_json()

        # Зв'язування подій
        self.right_frame.bind("<Double-1>", self.edit_vertex_text)
        self.right_frame.bind("<Button-1>", self.start_move_or_delete_vertex)
        self.right_frame.bind("<B1-Motion>", self.move_vertex)
        self.right_frame.bind("<ButtonRelease-1>", self.end_move_vertex)
        self.right_frame.bind("<ButtonPress-2>", self.start_pan)
        self.right_frame.bind("<B2-Motion>", self.pan)
        self.right_frame.bind("<MouseWheel>", self.zoom)

        # Переміщення та видалення елементів
        self.moving_vertex: Optional[Dict] = None
        self.offset_x = 0
        self.offset_y = 0
        self.delete_mode = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.scale = 1.0

        # З'єднання вершин
        self.connect_mode = False
        self.first_vertex: Optional[Dict] = None

        # Збереження даних
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self) -> None:
        """Збереження даних перед закриттям вікна."""
        self.save_data_to_json()
        self.root.destroy()

    def start_pan(self, event: tk.Event) -> None:
        """Початок режиму панорамування"""
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def pan(self, event: tk.Event) -> None:
        """Переміщення полотна з оновленням положення всіх елементів."""
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        self.right_frame.move("all", dx, dy)

        # Оновлення ствртової точки для наступного переміщення
        self.pan_start_x = event.x
        self.pan_start_y = event.y

        # Оновлення координатів всіх елементів після панорамування
        self.update_internal_positions_after_pan(dx, dy)

    def update_internal_positions_after_pan(self, dx: int, dy: int) -> None:
        """Оновлення координат для кожної вершини після переміщення полотна."""
        for vertex in self.vertices:
            vertex["x"] += dx
            vertex["y"] += dy
        # Оновлення всіх з'єднань
        self.update_connections()

    def add_vertex(self) -> None:
        """Додавання нової вершини з текстом"""
        note = simpledialog.askstring("Додати вершину", "Введіть текст нотатки (макс. 128 символів):")
        if note is None or len(note) > 128:
            messagebox.showerror("Помилка", "Текст нотатки не повинен перевищувати 128 символів.")
            return
        self.create_vertex(note)

    def create_vertex(self, note: str, x: Optional[int] = None, y: Optional[int] = None,
                      radius: Optional[int] = None) -> None:
        """Створення нової вершини з текстом."""
        wrapped_text = textwrap.fill(note, width=10)
        font_size = 10
        line_count = wrapped_text.count("\n") + 1
        radius = radius if radius else max(30, line_count * font_size)

        # Знаходження позиції без перекриття
        if x is None or y is None:
            x, y = self.find_non_overlapping_position(radius)

        # Створення кола для вершини
        vertex_id = self.right_frame.create_oval(x - radius, y - radius, x + radius, y + radius, fill="lightblue")

        # Створення тексту у центрі вершини
        text_id = self.right_frame.create_text(
            x, y, text=wrapped_text, width=radius * 1.8, font=("Arial", font_size), anchor="center"
        )

        vertex = {
            "id": vertex_id,
            "text_id": text_id,
            "note": note,
            "x": x,
            "y": y,
            "radius": radius
        }
        self.vertices.append(vertex)

    def start_connect_vertices(self) -> None:
        """Запуск режиму з'єднання вершин."""
        self.connect_mode = True
        self.first_vertex = None
        messagebox.showinfo("З’єднання вершин", "Натисніть на першу вершину, потім на другу для створення з'єднання.")

    def connect_vertices(self, vertex1: Dict, vertex2: Dict) -> None:
        """З'єднання двох вершин стрілкою."""
        if any((conn["vertex1"] == vertex1 and conn["vertex2"] == vertex2) or
               (conn["vertex1"] == vertex2 and conn["vertex2"] == vertex1) for conn in self.connections):
            messagebox.showinfo("З’єднання існує", "Між цими вершинами вже є з'єднання.")
            return

        x1, y1 = vertex1["x"], vertex1["y"]
        x2, y2 = vertex2["x"], vertex2["y"]
        angle = math.atan2(y2 - y1, x2 - x1)
        offset_x = vertex1["radius"] * math.cos(angle)
        offset_y = vertex1["radius"] * math.sin(angle)

        start_x = x1 + offset_x
        start_y = y1 + offset_y
        end_x = x2 - offset_x
        end_y = y2 - offset_y

        # Створення лінії зі стрілкою
        line_id = self.right_frame.create_line(start_x, start_y, end_x, end_y, arrow=tk.LAST)
        self.connections.append({"vertex1": vertex1, "vertex2": vertex2, "line_id": line_id})

    def start_delete_element(self) -> None:
        """Запуск режиму видалення елементів."""
        self.delete_mode = True
        messagebox.showinfo("Видалення елементу", "Натисніть на вершину або стрілку для видалення.")

    def start_move_or_delete_vertex(self, event: tk.Event) -> None:
        """Початок переміщення або видалення вершини."""
        if self.delete_mode:
            self.delete_element(event)
        elif self.connect_mode:
            clicked_vertex = self.find_vertex(event.x, event.y)
            if clicked_vertex:
                if self.first_vertex is None:
                    self.first_vertex = clicked_vertex
                else:
                    self.connect_vertices(self.first_vertex, clicked_vertex)
                    self.connect_mode = False
                    self.first_vertex = None
        else:
            self.moving_vertex = self.find_vertex(event.x, event.y)
            if self.moving_vertex:
                self.offset_x = event.x - self.moving_vertex["x"]
                self.offset_y = event.y - self.moving_vertex["y"]

    def delete_element(self, event: tk.Event) -> None:
        """Видалення вершини або зв'язку"""
        vertex_to_delete = self.find_vertex(event.x, event.y)
        if vertex_to_delete:
            connections_to_remove = [conn for conn in self.connections if
                                     conn["vertex1"] == vertex_to_delete or conn["vertex2"] == vertex_to_delete]
            for conn in connections_to_remove:
                self.right_frame.delete(conn["line_id"])
                self.connections.remove(conn)
            self.right_frame.delete(vertex_to_delete["id"])
            self.right_frame.delete(vertex_to_delete["text_id"])
            self.vertices.remove(vertex_to_delete)
            self.delete_mode = False
            return

        for connection in self.connections:
            x1, y1, x2, y2 = self.right_frame.coords(connection["line_id"])
            if self.point_near_line(event.x, event.y, x1, y1, x2, y2):
                self.right_frame.delete(connection["line_id"])
                self.connections.remove(connection)
                self.delete_mode = False
                return

    def point_near_line(self, px: int, py: int, x1: float, y1: float, x2: float, y2: float, tolerance: int = 5) -> bool:
        """Перевірка, чи знаходиться точка (px, py) поблизу лінії (x1, y1) -> (x2, y2)."""
        line_dist = abs((y2 - y1) * px - (x2 - x1) * py + x2 * y1 - y2 * x1) / math.sqrt(
            (y2 - y1) ** 2 + (x2 - x1) ** 2)
        return line_dist <= tolerance

    def move_vertex(self, event: tk.Event) -> None:
        """Переміщення вершини з оновленням положення та зв'язків."""
        if self.moving_vertex:
            new_x = event.x - self.offset_x
            new_y = event.y - self.offset_y
            self.moving_vertex["x"] = new_x
            self.moving_vertex["y"] = new_y
            radius = self.moving_vertex["radius"]
            self.right_frame.coords(self.moving_vertex["id"], new_x - radius, new_y - radius, new_x + radius,
                                    new_y + radius)
            self.right_frame.coords(self.moving_vertex["text_id"], new_x, new_y)
            self.update_connections()

    def end_move_vertex(self, event: tk.Event) -> None:
        """Завершення переміщення вершини."""
        self.moving_vertex = None

    def update_connections(self) -> None:
        """Перебудова з'єднань після оновлення вершин"""
        for connection in self.connections:
            vertex1 = connection["vertex1"]
            vertex2 = connection["vertex2"]
            line_id = connection["line_id"]

            # Позиції центрів вершин
            x1, y1 = vertex1["x"], vertex1["y"]
            x2, y2 = vertex2["x"], vertex2["y"]

            # Кут між вершинами
            angle = math.atan2(y2 - y1, x2 - x1)

            # Скориговані координати для стрілки
            start_x = x1 + vertex1["radius"] * math.cos(angle)
            start_y = y1 + vertex1["radius"] * math.sin(angle)
            end_x = x2 - vertex2["radius"] * math.cos(angle)
            end_y = y2 - vertex2["radius"] * math.sin(angle)

            # Оновлення координат стрілки
            self.right_frame.coords(line_id, start_x, start_y, end_x, end_y)

    def find_vertex(self, x: int, y: int) -> Optional[Dict]:
        """Пошук вершини на полотні за координатами."""
        for vertex in self.vertices:
            distance = math.sqrt((x - vertex["x"]) ** 2 + (y - vertex["y"]) ** 2)
            if distance <= vertex["radius"]:
                return vertex
        return None

    def find_non_overlapping_position(self, radius: int) -> (int, int):
        """Знаходження позиції для нової вершини без перекриття з іншими."""
        max_attempts = 100
        for _ in range(max_attempts):
            x = random.randint(radius + 10, 580 - radius)
            y = random.randint(radius + 10, 380 - radius)
            if all(not self.is_overlapping(x, y, radius, vertex) for vertex in self.vertices):
                return x, y
        return 100, 100

    def is_overlapping(self, x: int, y: int, radius: int, vertex: Dict) -> bool:
        """Перевірка, чи перекривається нова вершина з вершиною, що вже існує."""
        distance = math.sqrt((x - vertex["x"]) ** 2 + (y - vertex["y"]) ** 2)
        return distance < radius + vertex["radius"] + 10

    def edit_vertex_text(self, event: tk.Event) -> None:
        """Редагування тексту у вершині за подвійним натисканням."""
        clicked_vertex = self.find_vertex(event.x, event.y)
        if clicked_vertex:
            new_note = simpledialog.askstring("Редагувати вершину", "Введіть новий текст нотатки (макс. 128 символів):",
                                              initialvalue=clicked_vertex["note"])
            if new_note is None or len(new_note) > 128:
                messagebox.showerror("Помилка", "Текст нотатки не повинен перевищувати 128 символів.")
                return
            clicked_vertex["note"] = new_note
            self.update_vertex_display(clicked_vertex)

    def update_vertex_display(self, vertex: Dict) -> None:
        """Оновлення відображення тексту та розміру вершини."""
        wrapped_text = textwrap.fill(vertex["note"], width=10)
        font_size = 13
        line_count = wrapped_text.count("\n") + 1
        radius = max(30, line_count * font_size)
        vertex["radius"] = radius
        x, y = vertex["x"], vertex["y"]
        self.right_frame.coords(vertex["id"], x - radius, y - radius, x + radius, y + radius)
        self.right_frame.itemconfig(vertex["text_id"], text=wrapped_text, width=radius * 1.8)
        self.update_connections()

    def zoom(self, event: tk.Event) -> None:
        """Зміна масштабу"""
        scale_factor = 1.1 if event.delta > 0 else 0.9
        self.scale *= scale_factor
        self.right_frame.scale("all", 0, 0, scale_factor, scale_factor)
        for vertex in self.vertices:
            vertex["x"] *= scale_factor
            vertex["y"] *= scale_factor
            vertex["radius"] *= scale_factor
        self.update_connections()

    # Реалізація сейв-лоад при закритті-відкритті програми
    def save_data_to_json(self) -> None:
        """Збереження графу у файл JSON."""
        data = {
            "vertices": [{"note": v["note"], "x": v["x"], "y": v["y"], "radius": v["radius"]} for v in self.vertices],
            "connections": [
                {"vertex1": self.vertices.index(conn["vertex1"]), "vertex2": self.vertices.index(conn["vertex2"])} for
                conn in self.connections]
        }
        with open(self.data_file, "w") as f:
            json.dump(data, f, indent=4)

    def load_data_from_json(self) -> None:
        """Завантаження графу з JSON-файлу."""
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as f:
                data = json.load(f)
                for v in data["vertices"]:
                    self.create_vertex(v["note"], v["x"], v["y"], v["radius"])
                for conn in data["connections"]:
                    vertex1 = self.vertices[conn["vertex1"]]
                    vertex2 = self.vertices[conn["vertex2"]]
                    self.connect_vertices(vertex1, vertex2)

if __name__ == "__main__":
    root = tk.Tk()
    app = GraphApp(root)
    root.mainloop()


