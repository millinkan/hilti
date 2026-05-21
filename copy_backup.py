# copy_backup.py
import shutil

print("Restoring 1574-line app.py from backup...")
shutil.copy("app_refactored.py", "app.py")
print("Restored successfully!")
