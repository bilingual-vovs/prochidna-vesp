import ujson as json
import os
import uasyncio as asyncio

# V1

class DatabaseController:
    def __init__(self, db_path: str = "db.json", log = print):
        self.db_path = db_path
        self.logF = log
        self.lock = asyncio.Lock()
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

    async def _read_db(self) -> list:
        """Read current database content with lock"""
        async with self.lock:
            try:
                with open(self.db_path, 'r') as f:
                    return json.loads(f.read())
            except OSError as e:
                self.log(f"Failed to read database: {str(e)}")
                return []
            except json.JSONDecodeError as e:
                self.log(f"Invalid JSON in database: {str(e)}")
                return []

    async def _write_db(self, data: list) -> None:
        """Write data to database with lock"""
        async with self.lock:
            try:
                with open(self.db_path, 'w') as f:
                    f.write(json.dumps(data))
            except (OSError, TypeError) as e:
                self.log(f"Failed to write to database: {str(e)}")

    async def add_record(self, dec: str, fourth: str, time) -> None:
        """Add new record to database"""
        try:
            records = await self._read_db()
            records.append({
                "dec": dec,
                "fourth": fourth,
                "time": time
            })
            await self._write_db(records)
            # self.log(f"Added record {dec}")
        except Exception as e:
            self.log(f"Failed to add record: {str(e)}")

    async def get_record(self, block):
        """Get record with oldest timestamp"""
        try:
            records = await self._read_db()
            if not records:
                return None
            return min(records, key=lambda x: float('inf') if x['dec'] in block else x["dec"])
        except Exception as e:
            self.log(f"Failed to get record: {str(e)}")
        except (KeyError, TypeError) as e:
            self.log(f"Invalid record format: {str(e)}")

    async def remove_record(self, dec) -> bool:
        """Remove record with specified timestamp"""
        try:
            records = await self._read_db()
            if not records: 
                self.log("There is no records")
                return 
            records = [r for r in records if r['dec'] != dec]
            await self._write_db(records)
            # self.log(f"Removed record {dec}")
            return True
        except Exception as e:
            self.log(f"Failed to remove record: {str(e)}")
            return False