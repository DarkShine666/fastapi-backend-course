from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import os

# Путь к файлу хранения задач
TASKS_FILE_PATH = "tasks.json"


class FileStorage:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._initialize_storage()

    def _initialize_storage(self):
        """Инициализация хранилища при первом запуске"""
        if not os.path.exists(self.file_path):
            self._update_data({"tasks": [], "last_id": 0})

    def _load_data(self) -> dict:
        """Загрузка данных из файла"""
        with open(self.file_path, "r") as file:
            return json.load(file)

    def _update_data(self, data: dict):
        """Обновление данных в файле"""
        with open(self.file_path, "w") as file:
            json.dump(data, file)

    def get_all_tasks(self) -> List[Dict]:
        """Получение всех задач из хранилища"""
        return self._load_data().get("tasks", [])

    def create_task(self, title: str, status: str) -> Dict:
        """Создание новой задачи"""
        data = self._load_data()
        new_id = data["last_id"] + 1
        new_task = {"id": new_id, "title": title, "status": status}
        data["tasks"].append(new_task)
        data["last_id"] = new_id
        self._update_data(data)
        return new_task

    def update_task(
        self, task_id: int, title: Optional[str], status: Optional[str]
    ) -> Dict:
        """Обновление задачи по ID"""
        data = self._load_data()
        for task in data["tasks"]:
            if task["id"] == task_id:
                if title is not None:
                    task["title"] = title
                if status is not None:
                    task["status"] = status
                self._update_data(data)
                return task
        raise ValueError("Task not found")

    def delete_task(self, task_id: int) -> Dict:
        """Удаление задачи по ID"""
        data = self._load_data()
        for i, task in enumerate(data["tasks"]):
            if task["id"] == task_id:
                deleted_task = data["tasks"].pop(i)
                self._update_data(data)
                return deleted_task
        raise ValueError("Task not found")


# Инициализация хранилища
storage = FileStorage(TASKS_FILE_PATH)


# Модели Pydantic
class TaskCreate(BaseModel):
    title: str
    status: str = "pending"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None


# Эндпоинты
app = FastAPI()


@app.get("/tasks", response_model=List[Dict])
def get_tasks():
    """Получение списка всех задач"""
    return storage.get_all_tasks()


@app.post("/tasks", response_model=Dict)
def create_task(task: TaskCreate):
    """Создание новой задачи"""
    return storage.create_task(title=task.title, status=task.status)


@app.put("/tasks/{task_id}", response_model=Dict)
def update_task(task_id: int, task_update: TaskUpdate):
    """Обновление задачи по ID"""
    try:
        return storage.update_task(
            task_id=task_id, title=task_update.title, status=task_update.status
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/tasks/{task_id}", response_model=Dict)
def delete_task(task_id: int):
    """Удаление задачи по ID"""
    try:
        deleted_task = storage.delete_task(task_id)
        return {"message": "Task deleted", "task": deleted_task}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
