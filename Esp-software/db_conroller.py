import ujson as json
import os

class DatabaseController:
    def __init__(self, db_path: str = "db.json", log = print):
        self.db_path = db_path
        self.logF = log
        try:
            self._ensure_db_exists()
        except OSError as e:
            self.log(f"Failed to initialize database: {str(e)}")

    def log(self, t):
        self.logF(f'DB: {t}')

    def _ensure_db_exists(self) -> None:
        """Create database file if it doesn't exist"""
        try:
            os.stat(self.db_path)
        except OSError:
            try:
                with open(self.db_path, 'w') as f:
                    f.write('[]')
            except OSError as e:
                self.log(f"Failed to create database file: {str(e)}")

    def _read_db(self) -> list:
        """Read current database content"""
        try:
            with open(self.db_path, 'r') as f:
                return json.loads(f.read())
        except OSError as e:
            self.log(f"Failed to read database: {str(e)}")
        except json.JSONDecodeError as e:
            self.log(f"Invalid JSON in database: {str(e)}")

    def _write_db(self, data: list) -> None:
        """Write data to database"""
        try:
            with open(self.db_path, 'w') as f:
                f.write(json.dumps(data))
        except (OSError, TypeError) as e:
            self.log(f"Failed to write to database: {str(e)}")

    def add_record(self, dec: float, fourth: float, time: float) -> None:
        """Add new record to database"""
        if not all(isinstance(x, (int, float)) for x in [dec, fourth, time]):
            raise ValueError("All parameters must be numbers")
        try:
            records = self._read_db()
            records.append({
                "dec": dec,
                "fourth": fourth,
                "time": time
            })
            self._write_db(records)
            self.log(f"Added record {time}")
        except Exception as e:
            self.log(f"Failed to add record: {str(e)}")

    def get_record(self):
        """Get record with oldest timestamp"""
        try:
            records = self._read_db()
            if not records:
                return None
            return min(records, key=lambda x: x["time"])
        except Exception as e:
            self.log(f"Failed to get record: {str(e)}")
        except (KeyError, TypeError) as e:
            self.log(f"Invalid record format: {str(e)}")

    def remove_record(self, time: float) -> bool:
        """Remove record with specified timestamp"""
        if not isinstance(time, (int, float)):
            raise ValueError("Time must be a number")
        try:
            records = self._read_db()
            initial_len = len(records)
            records = [r for r in records if r["time"] != time]
            self._write_db(records)
            self.log(f"Removed record {time}")
            return True
        except Exception as e:
            self.log(f"Failed to remove record: {str(e)}")
            return False