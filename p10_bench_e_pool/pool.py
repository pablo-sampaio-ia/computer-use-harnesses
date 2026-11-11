"""P10: pool de sandboxes com fila + benchmark.

Um JOB = (agente, tarefa). O pool tem N "vagas" (sessoes paralelas); cada job pega uma vaga, ganha uma sessao NOVA
(sistema legado isolado), roda o worker como subprocesso com TIMEOUT, verifica o ESTADO e libera a sessao.

    uv run python -m p10_bench_e_pool.pool --agents p02:dom p03:codigo --tasks w1_um_cliente --parallel 3
    uv run python -m p10_bench_e_pool.pool --backend docker ...      # um container por sessao (nao testado aqui)
"""
import argparse
import json
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from p10_bench_e_pool.backends import BACKENDS
from p10_bench_e_pool.tasks import BY_ID, TASKS

AGENTS = ["p01:native", "p02:dom", "p03:codigo", "p05:som", "p06:hibrido", "p07:robusto"]


def run_job(backend, agent, task, timeout):
    sess = backend.start()
    t0 = time.time()
    try:
        state_file = None
        # o worker precisa do caminho do estado para o P07 (evidencia); o backend local o expoe via read_state
        state_path = Path("runs/p10") / f"{agent.replace(':', '_')}-{task.id}-{int(t0)}"
        state_path.mkdir(parents=True, exist_ok=True)
        sp = state_path / "estado.txt"
        sp.write_text("", encoding="utf-8")
        stop = threading.Event()

        def mirror():                             # copia o estado da sessao p/ um arquivo que o worker (P07) le
            while not stop.is_set():
                sp.write_text(sess.read_state(), encoding="utf-8")
                time.sleep(0.5)
        threading.Thread(target=mirror, daemon=True).start()
        try:
            r = subprocess.run([sys.executable, "-W", "ignore", "-m", "p10_bench_e_pool.worker", agent, task.id, sess.base_url, str(sp)],
                               capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
            line = [l for l in r.stdout.splitlines() if l.startswith("RESULT ")]
            res = json.loads(line[-1][7:]) if line else dict(done=False, steps=0, tokens_in=0, tokens_out=0, answer="",
                                                             error=(r.stderr or "sem saida")[-200:])
        except subprocess.TimeoutExpired:
            res = dict(done=False, steps=0, tokens_in=0, tokens_out=0, answer="", error=f"TIMEOUT {timeout}s")
        stop.set()
        ok, detail = task.verify(sess.read_state(), res.get("answer", ""))
        return dict(agent=agent, task=task.id, success=ok, detail=detail, seconds=round(time.time() - t0), **res)
    finally:
        sess.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", nargs="+", default=AGENTS)
    ap.add_argument("--tasks", nargs="+", default=[t.id for t in TASKS])
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--backend", default="local", choices=list(BACKENDS))
    ap.add_argument("--out", default="runs/p10_report")
    a = ap.parse_args()

    backend = BACKENDS[a.backend]()
    jobs = queue.Queue()
    for ag in a.agents:
        for t in a.tasks:
            jobs.put((ag, BY_ID[t]))
    results, lock = [], threading.Lock()

    def worker():
        while True:
            try:
                ag, t = jobs.get_nowait()
            except queue.Empty:
                return
            r = run_job(backend, ag, t, a.timeout)
            with lock:
                results.append(r)
                print(f"{'OK  ' if r['success'] else 'FAIL'} {ag:12} {t.id:16} passos={r['steps']:3} tok={r['tokens_in']:7} {r['seconds']:4}s  {r['detail']}"
                      + (f"  [{r['error']}]" if r.get("error") else ""), flush=True)

    t0 = time.time()
    threads = [threading.Thread(target=worker) for _ in range(a.parallel)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    report(results, a.out, round(time.time() - t0))


def report(results, out, wall):
    Path(out).parent.mkdir(exist_ok=True)
    Path(out + ".jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in results), encoding="utf-8")
    agents = sorted({r["agent"] for r in results})
    tasks = [t.id for t in TASKS if any(r["task"] == t.id for r in results)]
    by = {(r["agent"], r["task"]): r for r in results}
    lines = ["| agente | " + " | ".join(tasks) + " | sucessos | tokens (entrada) |", "|---|" + "---|" * (len(tasks) + 2)]
    for ag in agents:
        cells, ok, tok = [], 0, 0
        for t in tasks:
            r = by.get((ag, t))
            if r is None:
                cells.append("-")
                continue
            ok += r["success"]
            tok += r["tokens_in"]
            cells.append(("OK" if r["success"] else "FALHA") + f" ({r['steps']}p, {r['tokens_in'] // 1000}k)")
        lines.append(f"| {ag} | " + " | ".join(cells) + f" | {ok}/{len(tasks)} | {tok // 1000}k |")
    md = "\n".join(lines) + f"\n\nTempo total (parede): {wall}s\n"
    Path(out + ".md").write_text(md, encoding="utf-8")
    print("\n" + md)


if __name__ == "__main__":
    main()
