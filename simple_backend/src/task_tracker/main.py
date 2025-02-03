from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import requests

# Конфигурация окружения
JSONBIN_URL = "https://api.jsonbin.io/v3/b/67a10e4aad19ca34f8f93eb7"
HEADERS = {
    "X-Access-Key": "$2a$10$CKC/md8VxneemAk5v1bVMen/t66AErG0wE/4CJqMWzg9uFIXgnvrK",
    "Content-Type": "application/json",
}


class JsonBinStorage:
    def __init__(self):
        self._init_storage()

    def _init_storage(self):
        """Инициализация хранилища при первом запуске"""
        try:
            data = self._get_data()
            if "tasks" not in data or "last_id" not in data:
                self._put_data({"tasks": [], "last_id": 0})
        except requests.exceptions.HTTPError:
            self._put_data({"tasks": [], "last_id": 0})

    def _get_data(self) -> dict:
        """Получение данных из хранилища"""
        response = requests.get(JSONBIN_URL, headers=HEADERS)
        response.raise_for_status()
        return response.json().get("record", {})

    def _put_data(self, data: dict):
        """Обновление данных в хранилище"""
        response = requests.put(JSONBIN_URL, json=data, headers=HEADERS)
        response.raise_for_status()
        return response.json()

    def get_all_tasks(self) -> List[Dict]:
        """Получение всех задач из хранилища и обновление last_id"""
        data = self._get_data()
        if data["tasks"]:
            data["last_id"] = max(task["id"] for task in data["tasks"])
        else:
            data["last_id"] = 0
        self._put_data(data)
        return data.get("tasks", [])

    def create_task(self, title: str, status: str) -> Dict:
        """Создание новой задачи"""
        data = self._get_data()
        new_id = data["last_id"] + 1
        new_task = {"id": new_id, "title": title, "status": status}
        data["tasks"].append(new_task)
        data["last_id"] = new_id
        self._put_data(data)
        return new_task

    def update_task(
        self, task_id: int, title: Optional[str], status: Optional[str]
    ) -> Dict:
        """Обновление задачи по ID"""
        data = self._get_data()
        for task in data["tasks"]:
            if task["id"] == task_id:
                if title is not None:
                    task["title"] = title
                if status is not None:
                    task["status"] = status
                self._put_data(data)
                return task
        raise ValueError("Task not found")

    def delete_task(self, task_id: int) -> Dict:
        """Удаление задачи по ID"""
        data = self._get_data()
        for i, task in enumerate(data["tasks"]):
            if task["id"] == task_id:
                deleted_task = data["tasks"].pop(i)

                if data["tasks"]:
                    data["last_id"] = max(task["id"] for task in data["tasks"])
                else:
                    data["last_id"] = 0
                self._put_data(data)
                return deleted_task
        raise ValueError("Task not found")


# Инициализация хранилища с дефолтными значениями
storage = JsonBinStorage()


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
