import os, signal
pids=[2762042,2789266]
for pid in pids:
    try:
        with open(f'/proc/{pid}/cmdline','rb') as f:
            cmd=f.read().replace(b'\0', b' ').decode('utf-8','ignore')
        if 'http.server 3001' in cmd or 'uvicorn app:app --host 127.0.0.1 --port 8000' in cmd:
            os.kill(pid, signal.SIGTERM)
            print('stopped', pid, cmd)
        else:
            print('skip', pid, cmd)
    except FileNotFoundError:
        print('gone', pid)
