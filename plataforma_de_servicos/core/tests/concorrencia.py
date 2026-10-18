"""Helpers para testes de concorrência real, com threads e conexões próprias.

Use com ``@pytest.mark.django_db(transaction=True)``: cada thread abre a própria conexão
com o banco, e por isso só enxerga dados já commitados.
"""

import threading
import time

from django.db import connection


def em_paralelo(*funcoes, timeout=30):
    """Executa as funções em threads, liberadas juntas por uma barreira.

    Devolve uma lista de ("ok", resultado) ou ("erro", exceção), na ordem das funções.
    Cada thread usa e fecha a própria conexão.
    """
    barreira = threading.Barrier(len(funcoes))
    resultados = [None] * len(funcoes)

    def rodar(i, f):
        try:
            barreira.wait()
            resultados[i] = ("ok", f())
        except Exception as exc:  # noqa: BLE001
            resultados[i] = ("erro", exc)
        finally:
            connection.close()

    threads = [
        threading.Thread(target=rodar, args=(i, f)) for i, f in enumerate(funcoes)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout)
        assert not t.is_alive(), "thread presa: possível deadlock"
    return resultados


def atrasar_save(monkeypatch, model, segundos=0.2):
    """Faz model.save dormir antes de gravar, para abrir a janela de corrida."""
    original = model.save

    def save(self, *args, **kwargs):
        time.sleep(segundos)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(model, "save", save)
