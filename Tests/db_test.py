from db_conroller import DatabaseController #type: ignore 
import uasyncio as asyncio
import time

db = DatabaseController()


async def main():
    t1 = time.time()

    for i in range(1000):
        t = time.time()
        asyncio.run(db.add_record(i, i, t))
    
    
    for i in range(1000):
        r = await db.get_record(set())
        if r: asyncio.run(db.remove_record(r['dec']))
    
    print(time.time() - t1)
    print(await db._read_db())

async def get():
    print(await db.get_record(set([1111])))

asyncio.run(main())

# db_controller V1: 100 add + remove -> 23 sec
# db_controller V1: 1000 add + remove -> 23 sec