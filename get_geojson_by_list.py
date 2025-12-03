# FILENAME: get_geojson_by_list.py
# Version 3.2 – config-driven, emoji output, telemetry summary,
#               pending list saved to pending.txt (always overwritten).

import os
import subprocess
import shutil
import time
from datetime import datetime
import json
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# Load config
if os.path.isfile(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
else:
    cfg = {
        "downloader": {
            "delay_seconds": 0.1,
            "retry_cycles": 10,
            "dynamic_backoff": False
        },
        "paths": {
            "output_dir": "output",
            "temp_dir": "output_temp",
            "log_dir": "."
        }
    }

DELAY = cfg["downloader"]["delay_seconds"]
RETRY_CYCLES = cfg["downloader"]["retry_cycles"]

OUTPUT_DIR = os.path.join(BASE_DIR, cfg["paths"]["output_dir"])
TEMP_DIR = os.path.join(BASE_DIR, cfg["paths"]["temp_dir"])
LOG_DIR = os.path.join(BASE_DIR, cfg["paths"]["log_dir"])

INPUT_FILE = os.path.join(BASE_DIR, "cad_nums.txt")
LOG_TEXT = os.path.join(LOG_DIR, "rosreestr_custom.log")
LOG_JSON = os.path.join(LOG_DIR, "rosreestr_telemetry.json")
PENDING_FILE = os.path.join(BASE_DIR, "pending.txt")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

telemetry = []

def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def ts_iso():
    return datetime.now().isoformat()

def log_text(event, msg):
    with open(LOG_TEXT, "a", encoding="utf-8") as f:
        f.write(f"{ts()} | {event:<7} | {msg}\n")

def log_json(event, cad, **kwargs):
    entry = {"ts": ts_iso(), "cad": cad, "event": event}
    entry.update(kwargs)
    telemetry.append(entry)

def classify_error(stderr_text):
    if not stderr_text:
        return "retry"
    t = stderr_text.lower()
    not_found_keys = [
        "no object", "не найден", "not found",
        "object does not exist", "отсутствуют данные"
    ]
    for k in not_found_keys:
        if k in t:
            return "not_found"
    return "retry"

def run_single_download(cad_num, index=None, total=None):
    filename = cad_num.replace(":", "_") + ".geojson"
    temp_path = os.path.join(TEMP_DIR, filename)
    final_path = os.path.join(OUTPUT_DIR, filename)

    if index is not None and total is not None:
        print(f"📦 [{index}/{total}] Запрашиваем: {cad_num}")

    log_text("START", cad_num)
    log_json("start", cad_num)

    if os.path.isfile(temp_path):
        os.remove(temp_path)
    elif os.path.isdir(temp_path):
        shutil.rmtree(temp_path)

    try:
        result = subprocess.run(
            ["rosreestr2coord", "-c", cad_num, "-o", temp_path],
            text=True,
            capture_output=True
        )
    except KeyboardInterrupt:
        raise
    except Exception as e:
        err = str(e)
        print(f"  🔁 Ошибка запуска → retry: {cad_num}")
        log_text("RETRY", f"{cad_num} | {err}")
        log_json("retry", cad_num, error=err)
        return ("retry", None)

    if os.path.isfile(temp_path):
        shutil.copy2(temp_path, final_path)
        size = os.path.getsize(final_path)
        print(f"  ✅ Скопировано: {final_path}")
        log_text("OK", f"{final_path} | {size} bytes")
        log_json("success", cad_num, file=filename, size=size)
        return ("success", final_path)

    if os.path.isdir(temp_path):
        nested = os.path.join(temp_path, "geojson", filename)
        if os.path.isfile(nested):
            shutil.copy2(nested, final_path)
            size = os.path.getsize(final_path)
            print(f"  ✅ Извлечено из структуры: {final_path}")
            log_text("OK", f"{final_path} | {size} bytes")
            log_json("success", cad_num, file=filename, size=size)
            return ("success", final_path)

    err_type = classify_error(result.stderr)
    if err_type == "not_found":
        print(f"  ❌ Не найдено: {cad_num}")
        log_text("ERROR", f"{cad_num} | not found")
        log_json("error", cad_num, error="not_found")
        return ("not_found", None)
    else:
        print(f"  🔁 Сервер отказал → retry: {cad_num}")
        log_text("RETRY", f"{cad_num} | {result.stderr.strip()}")
        log_json("retry", cad_num, error=result.stderr.strip())
        return ("retry", None)

def process_pass(cads):
    success = []
    not_found = []
    retry = []
    total = len(cads)
    for idx, cad in enumerate(cads, 1):
        # STOP FLAG CHECK
        if os.path.exists('stop.flag'):
            print('⛔ Обнаружен stop.flag — завершаю и формирую отчёт...')
            try: os.remove('stop.flag')
            except: pass
            graceful_exit()
        status, _ = run_single_download(cad, idx, total)
        if status == "success":
            success.append(cad)
        elif status == "not_found":
            not_found.append(cad)
        else:
            retry.append(cad)
        time.sleep(DELAY)
    return success, not_found, retry

def compute_summary_from_telemetry():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            all_cads = [x.strip() for x in f if x.strip()]
    except FileNotFoundError:
        all_cads = []

    success_set = {e["cad"] for e in telemetry if e.get("event") == "success"}
    not_found_set = {
        e["cad"] for e in telemetry
        if e.get("event") == "error" and e.get("error") == "not_found"
    }

    pending = [c for c in all_cads if c not in success_set and c not in not_found_set]

    return success_set, not_found_set, pending

def write_pending_file(pending):
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        for cad in pending:
            f.write(cad + "\n")

def graceful_exit():
    print("\n⛔ Прервано пользователем. Идёт сохранение логов...")

    shutil.rmtree(TEMP_DIR, ignore_errors=True)

    with open(LOG_JSON, "w", encoding="utf-8") as f:
        json.dump(telemetry, f, ensure_ascii=False, indent=2)

    success_set, not_found_set, pending = compute_summary_from_telemetry()

    write_pending_file(pending)

    print("\n=========== ПРЕДВАРИТЕЛЬНЫЙ ОТЧЁТ ===========")
    print(f"Успешно скачано:  {len(success_set)}")
    print(f"Не найдено:        {len(not_found_set)}")
    print(f"Недогружено:       {len(pending)}")
    print(f"Список недогрузок сохранён в: {PENDING_FILE}")
    print("==============================================\n")
    sys.exit(1)

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        cads = [x.strip() for x in f if x.strip()]

    success_all = []
    not_found_all = []
    retry_list = cads

    try:
        s, nf, r = process_pass(retry_list)
        success_all.extend(s)
        not_found_all.extend(nf)
        retry_list = r

        for _ in range(RETRY_CYCLES - 1):
            if not retry_list:
                break
            s, nf, r = process_pass(retry_list)
            success_all.extend(s)
            not_found_all.extend(nf)
            retry_list = r

    except KeyboardInterrupt:
        graceful_exit()

    shutil.rmtree(TEMP_DIR, ignore_errors=True)

    with open(LOG_JSON, "w", encoding="utf-8") as f:
        json.dump(telemetry, f, ensure_ascii=False, indent=2)

    success_set, not_found_set, pending = compute_summary_from_telemetry()
    write_pending_file(pending)

    print("\n================= REPORT =================")
    print(f"Успешно скачано:  {len(success_set)}")
    print(f"Не найдено:        {len(not_found_set)}")
    print(f"После {RETRY_CYCLES} попыток недогружено: {len(pending)}")
    print(f"Список недогрузок сохранён в: {PENDING_FILE}")
    print("==========================================\n")

if __name__ == '__main__':
    main()
