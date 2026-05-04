
import asyncio
import threading

def worker():
    try:
        # Simula o que o LlamaIndex faz: tenta rodar um loop
        asyncio.run(asyncio.sleep(0.1))
        print("Success: asyncio.run works in a separate thread")
    except Exception as e:
        print(f"Failure: {e}")

async def main():
    print("In main loop (async)")
    # Se chamarmos diretamente, falha
    try:
        asyncio.run(asyncio.sleep(0.1))
    except Exception as e:
        print(f"Expected failure in main loop: {e}")
    
    # Se rodarmos em uma thread, funciona
    t = threading.Thread(target=worker)
    t.start()
    t.join()

if __name__ == "__main__":
    asyncio.run(main())
