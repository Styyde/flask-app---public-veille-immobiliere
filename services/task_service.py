import threading
import traceback
import asyncio
from database.db_manager import update_task_status

def run_scraper_sync(task_id, source, target_func, args, kwargs):
    """
    Exécute un scraper bloquant (synchrone)
    """
    try:
        update_task_status(task_id, 'en_cours', message=f"Lancement du scraping {source}...")
        result = target_func(*args, **kwargs)
        update_task_status(task_id, 'termine', message=f"Scraping terminé.", result=result)
    except Exception as e:
        error_msg = f"Erreur lors du scraping {source}: {str(e)}"
        print(f"[{task_id}] {error_msg}")
        traceback.print_exc()
        update_task_status(task_id, 'erreur', message=error_msg)


def run_scraper_async(task_id, source, target_coro_func, args, kwargs):
    """
    Exécute un scraper asynchrone (nécessite sa propre event loop dans ce thread)
    """
    try:
        update_task_status(task_id, 'en_cours', message=f"Lancement du scraping {source}...")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(target_coro_func(*args, **kwargs))
        
        update_task_status(task_id, 'termine', message=f"Scraping terminé.", result=result)
    except Exception as e:
        error_msg = f"Erreur lors du scraping {source}: {str(e)}"
        print(f"[{task_id}] {error_msg}")
        traceback.print_exc()
        update_task_status(task_id, 'erreur', message=error_msg)
    finally:
        try:
            loop.close()
        except:
            pass


def start_scraping_task(task_id, source, is_async, target_func, *args, **kwargs):
    """
    Lance le scraping dans un thread séparé (daemon=True pour s'arrêter avec l'app).
    """
    if is_async:
        thread = threading.Thread(
            target=run_scraper_async,
            args=(task_id, source, target_func, args, kwargs),
            daemon=True
        )
    else:
        thread = threading.Thread(
            target=run_scraper_sync,
            args=(task_id, source, target_func, args, kwargs),
            daemon=True
        )
    
    thread.start()
    return thread
