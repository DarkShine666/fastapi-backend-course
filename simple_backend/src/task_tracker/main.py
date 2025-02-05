from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict
import requests
import json
from abc import ABC, abstractmethod
from enum import Enum


# --- Общая часть для всех хранилищ --- #
class StorageType(str, Enum):
    JSONBIN = "jsonbin"
    FILE = "file"


class TaskBaseModel(BaseModel):
    title: str
    status: str


class TaskCreate(TaskBaseModel):
    pass


class TaskUpdate(TaskBaseModel):
    pass


class ResponseModel(BaseModel):
    """Доделать!!!!!!!!"""

    pass


class BaseStorage(ABC):
    @abstractmethod
    def get_all_tasks(self) -> List[Dict]:
        """Получение всех задач из хранилища"""
        pass

    @abstractmethod
    def create_task(self, task: TaskCreate) -> Dict:
        """Создание новой задачи"""
        pass

    @abstractmethod
    def update_task(self, task_id: int, task: TaskUpdate) -> Dict:
        """Обновление данных в хранилище"""
        pass

    @abstractmethod
    def delete_task(self, task_id: int) -> Dict:
        """Удаление задачи по ID"""
        pass


# --- Реализация для JSONBin.io --- #
class JsonBinStorage(BaseStorage):
    def __init__(self, bin_url: str, api_key: str):
        self.bin_url = bin_url
        self.headers = {
            "X-Access-Key": api_key,
            "Content-Type": "application/json",
        }
        self._initialize()

    def _initialize(self):
        """Инициализация хранилища при первом запуске"""
        try:
            data = self._load_data()
            if not data.get("tasks") or not data.get("last_id"):
                self._save_data({"tasks": [], "last_id": 0})
        except requests.RequestException:
            self._save_data({"tasks": [], "last_id": 0})

    def _load_data(self) -> Dict:
        """Получение данных из хранилища"""
        response = requests.get(self.bin_url, headers=self.headers)
        response.raise_for_status()
        return response.json().get("record", {})

    def _save_data(self, data: dict):
        """Обновление данных в хранилище"""
        response = requests.put(self.bin_url, json=data, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_all_tasks(self) -> List[Dict]:
        """Получение всех задач из хранилища"""
        return self._load_data().get("tasks", [])

    def create_task(self, task: TaskCreate) -> Dict:
        """Создание новой задачи"""
        data = self._load_data()
        new_id = data["last_id"] + 1
        new_task = {"id": new_id, "title": task.title, "status": task.status}
        data["tasks"].append(new_task)
        data["last_id"] = new_id
        self._save_data(data)
        return new_task

    def update_task(self, task_id: int, task: TaskUpdate) -> Dict:
        """Обновление данных в хранилище"""
        data = self._load_data()
        for t in data["tasks"]:
            if t["id"] == task_id:
                t.update(task.dict())
                self._save_data(data)
                return t
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found"
        )

    def delete_task(self, task_id: int) -> Dict:
        """Удаление задачи по ID"""
        data = self._load_data()
        for idx, t in enumerate(data["tasks"]):
            if t["id"] == task_id:
                deleted = data["tasks"].pop(idx)
                self._save_data(data)
                return deleted
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found"
        )


# --- Реализация для файлового хранилища --- #
class FileStorage(BaseStorage):
    def __init__(self, file_path: str = "tasks.json"):
        self.file_path = file_path
        self._initialize()

    def _initialize(self):
        """Инициализация хранилища при первом запуске"""
        try:
            self._load_data()
        except FileNotFoundError:
            self._save_data({"tasks": [], "last_id": 0})

    def _load_data(self) -> dict:
        """Загрузка данных из файла"""
        with open(self.file_path, "r") as f:
            return json.load(f)

    def _save_data(self, data: dict):
        """Обновление данных в файле"""
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_all_tasks(self) -> List[Dict]:
        """Получение всех задач из хранилища"""
        return self._load_data().get("tasks", [])

    def create_task(self, task: TaskCreate) -> Dict:
        """Создание новой задачи"""
        data = self._load_data()
        new_id = data["last_id"] + 1
        new_task = {"id": new_id, "title": task.title, "status": task.status}
        data["tasks"].append(new_task)
        data["last_id"] = new_id
        self._save_data(data)
        return new_task

    def update_task(self, task_id: int, task: TaskUpdate) -> Dict:
        """Обновление задачи по ID"""
        data = self._load_data()
        for t in data["tasks"]:
            if t["id"] == task_id:
                t.update(task.dict())
                self._save_data(data)
                return t
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found"
        )

    def delete_task(self, task_id: int) -> Dict:
        """Удаление задачи по ID"""
        data = self._load_data()
        for idx, t in enumerate(data["tasks"]):
            if t["id"] == task_id:
                deleted = data["tasks"].pop(idx)
                self._save_data(data)
                return deleted
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found"
        )


# --- Инициализация приложения --- #
app = FastAPI()

# Выбор хранилища при старте приложения


# Для использования JSONBin:
# storage = JsonBinStorage(
#     bin_url="https://api.jsonbin.io/v3/b/67a10e4aad19ca34f8f93eb7",
#     api_key="$2a$10$CKC/md8VxneemAk5v1bVMen/t66AErG0wE/4CJqMWzg9uFIXgnvrK",
# )

# Для использования файлового хранилища
storage = FileStorage(file_path="tasks.json")


# --- Эндпоинты --- #
@app.get("/tasks", response_model=List[Dict])
def get_all_tasks():
    return storage.get_all_tasks()


@app.post("/tasks", response_model=Dict, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate):
    return storage.create_task(task)


@app.put("/tasks/{task_id}", response_model=Dict)
def update_task(task_id: int, task: TaskUpdate):
    return storage.update_task(task_id, task)


@app.delete("/tasks/{task_id}", response_model=Dict)
def delete_task(task_id: int):
    deleted = storage.delete_task(task_id)
    return {"message": "Task deleted", "task": deleted}
