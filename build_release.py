import os
import zipfile

def create_release(version):
    release_dir = f"mouse_mover_{version}"
    zip_name = f"{release_dir}.zip"
    
    # Файлы для включения в архив
    files = ["mouse_mover.py", "mouse_mover_icon.ico", "requirements.txt", "version.txt"]
    
    # Создаем version.txt
    with open("version.txt", "w") as f:
        f.write(version)
    
    # Создаем ZIP-архив
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            if os.path.exists(file):
                zipf.write(file)
                print(f"Добавлен файл: {file}")
            else:
                print(f"Предупреждение: Файл {file} не найден")
    
    print(f"Создан релиз: {zip_name}")

if __name__ == "__main__":
    version = input("Введите версию релиза (например, v1.1): ")
    create_release(version)