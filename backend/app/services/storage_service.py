import os
import shutil
from typing import List, Optional

STORAGE_ROOT = os.path.abspath("./storage/uploads")

class StorageService:
    @staticmethod
    def get_folder_path(folder_name: str) -> str:
        folder_path = os.path.join(STORAGE_ROOT, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    @staticmethod
    def save_file(folder_name: str, filename: str, content: bytes) -> str:
        folder_path = StorageService.get_folder_path(folder_name)
        target_path = os.path.join(folder_path, filename)
        with open(target_path, "wb") as f:
            f.write(content)
        return target_path

    @staticmethod
    def delete_file(file_path: str) -> bool:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except Exception:
                return False
        return False

    @staticmethod
    def list_files_in_folder(folder_name: str) -> List[str]:
        folder_path = StorageService.get_folder_path(folder_name)
        if not os.path.exists(folder_path):
            return []
        return [f for f in os.listdir(folder_path) if f.endswith(".csv")]
