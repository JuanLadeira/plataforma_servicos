import csv
import io
from pathlib import Path

import pandas as pd
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from produto.models.produto_model import Produto


def produto_json(request, pk):
    """Retorna o produto, id e estoque."""
    produto = Produto.objects.filter(pk=pk)
    data = [item.to_dict_json() for item in produto]
    return JsonResponse({"data": data})


def save_data(data):
    """
    Salva os dados no banco.
    """
    aux = []
    for item in data:
        produto = item.get("produto")
        ncm = str(item.get("ncm"))
        importado = item.get("importado") == "True"
        preco = item.get("preco")
        estoque = item.get("estoque")
        estoque_minimo = item.get("estoque_minimo")
        obj = Produto(
            produto=produto,
            ncm=ncm,
            importado=importado,
            preco=preco,
            estoque=estoque,
            estoque_minimo=estoque_minimo,
        )
        aux.append(obj)
    Produto.objects.bulk_create(aux)


def import_csv(request):
    if request.method == "POST" and request.FILES["myfile"]:
        myfile = request.FILES["myfile"]
        # Lendo arquivo InMemoryUploadedFile
        file = myfile.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(file))
        # Gerando uma list comprehension
        data = list(reader)
        save_data(data)
        return HttpResponseRedirect(reverse("produto:produto_list"))

    template_name = "produto_import.html"
    return render(request, template_name)


def export_csv(request):
    header = (
        "importado",
        "ncm",
        "produto",
        "preco",
        "estoque",
        "estoque_minimo",
    )
    produtos = Produto.objects.all().values_list(*header)
    with Path.open("fix/produtos_exportados.csv", "w") as csvfile:
        produto_writer = csv.writer(csvfile)
        produto_writer.writerow(header)
        for produto in produtos:
            produto_writer.writerow(produto)
    messages.success(request, "Produtos exportados com sucesso.")
    return HttpResponseRedirect(reverse("produto:produto_list"))


def import_csv_with_pandas(request):
    filename = "fix/produtos.csv"
    data_frame = pd.read_csv(filename)
    aux = []
    for row in data_frame.to_numpy():
        obj = Produto(
            produto=row[0],
            ncm=row[1],
            importado=row[2],
            preco=row[3],
            estoque=row[4],
            estoque_minimo=row[5],
        )
        aux.append(obj)
    Produto.objects.bulk_create(aux)
    messages.success(request, "Produtos importados com sucesso.")
    return HttpResponseRedirect(reverse("produto:produto_list"))
