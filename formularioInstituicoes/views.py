import copy
import os
import sys
from pathlib import Path

from django.contrib.auth import authenticate, logout, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, PasswordChangeForm
from django.core.mail import send_mail
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.template.defaulttags import register
from slugify import slugify

from project import settings
from .models import *
from .forms import *

perguntas_form = {}
perguntas_update_form = {}


def getEntidade(request) -> Entidade:
    if Entidade.objects.filter(user__id=request.user.id).first():
        return Entidade.objects.filter(user__id=request.user.id).first()
    else:
        return None


def criar_perguntas_form(perguntas_form_object):
    questionario = Questionario.objects.get(nome="Questionário Instalações Desportivas")

    for tema in questionario.temas.all().order_by('ordem_perguntas_formulario'):

        subtemas = {}

        subtemas_todos = SubTema.objects.filter(tema_id=tema.id).order_by('nome')

        if subtemas_todos.filter(nome='Valores relevantes').exists() & subtemas_todos.filter(nome='Outro').exists():
            excluindo_valores = subtemas_todos.exclude(nome='Valores relevantes')
            subtema_valores = subtemas_todos.get(nome='Valores relevantes')

            valores_escluidos = excluindo_valores.exclude(nome='Outro')
            subtema_outro = subtemas_todos.get(nome='Outro')

            subtemas_todos = [subtema_valores] + list(valores_escluidos) + [subtema_outro]

        elif subtemas_todos.filter(nome='Outro').exists():
            valores_escluidos = subtemas_todos.exclude(nome='Outro')
            subtema_outro = subtemas_todos.get(nome='Outro')

            subtemas_todos = list(valores_escluidos) + [subtema_outro]

        elif subtemas_todos.filter(nome='Outros').exists():
            valores_escluidos = subtemas_todos.exclude(nome='Outros')
            subtema_outro = subtemas_todos.get(nome='Outros')

            subtemas_todos = list(valores_escluidos) + [subtema_outro]

        for subtema in subtemas_todos:
            formulario = {}

            perguntas_todos = Pergunta.objects.filter(subtema_id=subtema.id).order_by('texto')

            if perguntas_todos.filter(texto='Número de veículos da instalação').exists():
                valores_escluidos = perguntas_todos.exclude(texto='Número de veículos da instalação')
                pergunta_escluida = perguntas_todos.get(texto='Número de veículos da instalação')

                perguntas_todos = [pergunta_escluida] + list(valores_escluidos)

            elif perguntas_todos.filter(tipo='ESCOLHA_MULTIPLA_VARIAS').exists():
                valores_escluidos = perguntas_todos.exclude(tipo='ESCOLHA_MULTIPLA_VARIAS')
                pergunta_escluida = perguntas_todos.get(tipo='ESCOLHA_MULTIPLA_VARIAS')

                perguntas_todos = [pergunta_escluida] + list(valores_escluidos)

            elif perguntas_todos.filter(texto='Com potência de').exists():
                valores_escluidos = perguntas_todos.exclude(texto='Com potência de')
                pergunta_escluida = perguntas_todos.get(texto='Com potência de')

                perguntas_todos = list(valores_escluidos) + [pergunta_escluida]

            elif perguntas_todos.filter(texto='Com valor de').exists():
                valores_escluidos = perguntas_todos.exclude(texto='Com valor de')
                pergunta_escluida = perguntas_todos.get(texto='Com valor de')

                perguntas_todos = list(valores_escluidos) + [pergunta_escluida]

            elif perguntas_todos.filter(texto='Nome').exists():
                valores_escluidos = perguntas_todos.exclude(texto='Nome')
                pergunta_escluida = perguntas_todos.get(texto='Nome')

                perguntas_todos = [pergunta_escluida] + list(valores_escluidos)

            elif perguntas_todos.filter(texto='Tipos de atividade desportiva').exists():
                valores_escluidos = perguntas_todos.exclude(texto='Tipos de atividade desportiva')
                pergunta_escluida = perguntas_todos.get(texto='Tipos de atividade desportiva')

                perguntas_todos = [pergunta_escluida] + list(valores_escluidos)

            for pergunta in perguntas_todos:
                if pergunta.tipo == 'NUMERO_INTEIRO':
                    formint = FormNumerosInteiros(prefix=pergunta.id)
                    formulario[pergunta] = formint

                elif pergunta.tipo == 'TEXTO_LIVRE':
                    formtext = FormTextoLivre(prefix=pergunta.id)
                    formulario[pergunta] = formtext

                elif pergunta.tipo == 'ESCOLHA_MULTIPLA_UNICA':
                    formescolha = FormEscolhaMultiplaUnica(prefix=pergunta.id)
                    formescolha.fields['opcao'].queryset = pergunta.opcoes.all().order_by('nome')
                    formulario[pergunta] = formescolha

                elif pergunta.tipo == 'ESCOLHA_MULTIPLA_VARIAS':
                    formescolha = FormEscolhaMultiplaVarias(prefix=pergunta.id)

                    escolhas = []

                    opcoes = pergunta.opcoes.all().order_by('nome')

                    if opcoes.filter(nome='Outro').exists():
                        opcoes = opcoes.exclude(nome='Outro')
                        opcao_outro = pergunta.opcoes.get(nome='Outro')
                        opcoes = list(opcoes) + [opcao_outro]

                    for count, opcao in enumerate(opcoes, start=0):
                        escolha = (str(count), opcao.nome)
                        escolhas.append(escolha)

                    escolhas_final = tuple(escolhas)

                    formescolha.fields['opcoes'].choices = escolhas_final
                    formulario[pergunta] = formescolha

                elif pergunta.tipo == 'FICHEIRO':
                    formficheiro = FormFicheiro(prefix=pergunta.id)
                    formulario[pergunta] = formficheiro

                elif pergunta.tipo == 'MES':
                    formdata = FormMes(prefix=pergunta.id)
                    formulario[pergunta] = formdata

            subtemas[subtema] = formulario

        perguntas_form_object[tema] = subtemas


def update_respostas_view(request, perguntas_form_object, instalacao, ano_questionario):
    avaliacoes = Avaliacao.objects.filter(instalacao__id=instalacao)

    avaliacao = avaliacoes.get(ano=ano_questionario)

    questionario = avaliacao.questionario

    for tema in questionario.temas.all().order_by('ordem_perguntas_formulario'):

        subtemas = {}

        subtemas_todos = SubTema.objects.filter(tema_id=tema.id).order_by('nome')

        if subtemas_todos.filter(nome='Valores relevantes').exists() & subtemas_todos.filter(nome='Outro').exists():
            excluindo_valores = subtemas_todos.exclude(nome='Valores relevantes')
            subtema_valores = subtemas_todos.get(nome='Valores relevantes')

            valores_escluidos = excluindo_valores.exclude(nome='Outro')
            subtema_outro = subtemas_todos.get(nome='Outro')

            subtemas_todos = [subtema_valores] + list(valores_escluidos) + [subtema_outro]

        elif subtemas_todos.filter(nome='Outro').exists():
            valores_escluidos = subtemas_todos.exclude(nome='Outro')
            subtema_outro = subtemas_todos.get(nome='Outro')

            subtemas_todos = list(valores_escluidos) + [subtema_outro]

        elif subtemas_todos.filter(nome='Outros').exists():
            valores_escluidos = subtemas_todos.exclude(nome='Outros')
            subtema_outro = subtemas_todos.get(nome='Outros')

            subtemas_todos = list(valores_escluidos) + [subtema_outro]

        for subtema in subtemas_todos:
            formulario = {}

            perguntas_todos = Pergunta.objects.filter(subtema_id=subtema.id).order_by('texto')

            if perguntas_todos.filter(texto='Número de veículos da instalação').exists():
                valores_escluidos = perguntas_todos.exclude(texto='Número de veículos da instalação')
                pergunta_escluida = perguntas_todos.get(texto='Número de veículos da instalação')

                perguntas_todos = [pergunta_escluida] + list(valores_escluidos)

            elif perguntas_todos.filter(tipo='ESCOLHA_MULTIPLA_VARIAS').exists():
                valores_escluidos = perguntas_todos.exclude(tipo='ESCOLHA_MULTIPLA_VARIAS')
                pergunta_escluida = perguntas_todos.get(tipo='ESCOLHA_MULTIPLA_VARIAS')

                perguntas_todos = [pergunta_escluida] + list(valores_escluidos)

            elif perguntas_todos.filter(texto='Com potência de').exists():
                valores_escluidos = perguntas_todos.exclude(texto='Com potência de')
                pergunta_escluida = perguntas_todos.get(texto='Com potência de')

                perguntas_todos = list(valores_escluidos) + [pergunta_escluida]

            elif perguntas_todos.filter(texto='Com valor de').exists():
                valores_escluidos = perguntas_todos.exclude(texto='Com valor de')
                pergunta_escluida = perguntas_todos.get(texto='Com valor de')

                perguntas_todos = list(valores_escluidos) + [pergunta_escluida]

            elif perguntas_todos.filter(texto='Nome').exists():
                valores_escluidos = perguntas_todos.exclude(texto='Nome')
                pergunta_escluida = perguntas_todos.get(texto='Nome')

                perguntas_todos = [pergunta_escluida] + list(valores_escluidos)

            elif perguntas_todos.filter(texto='Tipos de atividade desportiva').exists():
                valores_escluidos = perguntas_todos.exclude(texto='Tipos de atividade desportiva')
                pergunta_escluida = perguntas_todos.get(texto='Tipos de atividade desportiva')

                perguntas_todos = [pergunta_escluida] + list(valores_escluidos)

            for pergunta in perguntas_todos:

                if pergunta.tipo == 'NUMERO_INTEIRO':
                    respostas_perguntas = RespostaNumerica.objects.filter(pergunta_id=pergunta.id)
                    respostas_dadas = respostas_perguntas.filter(avaliacao__instalacao_id=instalacao)
                    formulario[pergunta] = []

                    pergunta_tem_resposta = RespostaNumerica.objects.filter(pergunta_id=pergunta).filter(
                        avaliacao=avaliacao).count()

                    if pergunta_tem_resposta == 0:
                        formint = FormNumerosInteiros(prefix=pergunta.id)
                        formulario[pergunta].append(formint)
                    else:
                        for resposta_dada in respostas_dadas:
                            formint = FormNumerosInteiros(prefix=pergunta.id, instance=resposta_dada)
                            formulario[pergunta].append(formint)


                elif pergunta.tipo == 'TEXTO_LIVRE':

                    respostas_perguntas = RespostaTextual.objects.filter(pergunta_id=pergunta.id)
                    respostas_dadas = respostas_perguntas.filter(avaliacao__instalacao_id=instalacao)
                    formulario[pergunta] = []

                    pergunta_tem_resposta = RespostaTextual.objects.filter(pergunta_id=pergunta).filter(
                        avaliacao=avaliacao).count()

                    if pergunta_tem_resposta == 0:
                        formtxt = FormTextoLivre(prefix=pergunta.id)
                        formulario[pergunta].append(formtxt)
                    else:
                        for resposta_dada in respostas_dadas:
                            formtxt = FormTextoLivre(prefix=pergunta.id, instance=resposta_dada)
                            formulario[pergunta].append(formtxt)

                elif pergunta.tipo == 'ESCOLHA_MULTIPLA_UNICA':

                    respostas_perguntas = RespostaTextual.objects.filter(pergunta_id=pergunta.id)
                    respostas_dadas = respostas_perguntas.filter(avaliacao__instalacao_id=instalacao)
                    formulario[pergunta] = []

                    pergunta_tem_resposta = RespostaTextual.objects.filter(pergunta_id=pergunta).filter(
                        avaliacao=avaliacao).count()

                    if pergunta_tem_resposta == 0:
                        formescolha = FormEscolhaMultiplaUnica(request.POST or None, prefix=pergunta.id)
                        formescolha.fields['opcao'].queryset = pergunta.opcoes.all().order_by('nome')
                        formulario[pergunta].append(formescolha)
                    else:
                        for resposta_dada in respostas_dadas:
                            formescolha = FormEscolhaMultiplaUnica(request.POST or None, prefix=pergunta.id,
                                                                   instance=resposta_dada)
                            formescolha.fields['opcao'].queryset = pergunta.opcoes.all().order_by('nome')
                            formulario[pergunta].append(formescolha)

                elif pergunta.tipo == 'ESCOLHA_MULTIPLA_VARIAS':

                    respostas_perguntas = RespostaTextual.objects.filter(pergunta_id=pergunta.id)
                    respostas_dadas = respostas_perguntas.filter(avaliacao__instalacao_id=instalacao)

                    formulario[pergunta] = []

                    pergunta_tem_resposta = RespostaTextual.objects.filter(pergunta_id=pergunta).filter(
                        avaliacao=avaliacao).count()

                    if pergunta_tem_resposta == 0:
                        formescolha = FormEscolhaMultiplaVarias(prefix=pergunta.id)

                        escolhas = []

                        opcoes = pergunta.opcoes.all().order_by('nome')

                        if opcoes.filter(nome='Outro').exists():
                            opcoes = opcoes.exclude(nome='Outro')
                            opcao_outro = pergunta.opcoes.get(nome='Outro')
                            opcoes = list(opcoes) + [opcao_outro]

                        escolhas.append(('100', 'hidden'))

                        for count, opcao in enumerate(opcoes, start=1):
                            escolha = (str(count), opcao.nome)
                            escolhas.append(escolha)

                        escolhas_final = tuple(escolhas)

                        formescolha.fields['opcoes'].choices = escolhas_final
                        formulario[pergunta] = formescolha
                    else:

                        formescolha = FormEscolhaMultiplaVarias(prefix=pergunta.id)

                        escolhas = []

                        opcoes = pergunta.opcoes.all().order_by('nome')

                        if opcoes.filter(nome='Outro').exists():
                            opcoes = opcoes.exclude(nome='Outro')
                            opcao_outro = pergunta.opcoes.get(nome='Outro')
                            opcoes = list(opcoes) + [opcao_outro]

                        valores_init = None

                        escolhas.append(('100', 'hidden'))

                        for count, opcao in enumerate(opcoes, start=1):
                            escolha = (str(count), opcao.nome)

                            for resposta_dada in respostas_dadas:
                                opcao_resposta = resposta_dada.texto
                                if opcao_resposta == escolha[1]:
                                    if valores_init is None:
                                        valores_init = escolha
                                    else:
                                        valores_init = valores_init + escolha

                            escolhas.append(escolha)

                        formescolha.fields['opcoes'].initial = valores_init

                        escolhas_final = tuple(escolhas)

                        formescolha.fields['opcoes'].choices = escolhas_final

                        formulario[pergunta] = formescolha

                elif pergunta.tipo == 'FICHEIRO':

                    respostas_perguntas = Ficheiro.objects.filter(pergunta_id=pergunta.id)
                    respostas_dadas = respostas_perguntas.filter(avaliacao__instalacao_id=instalacao)
                    formulario[pergunta] = []

                    pergunta_tem_resposta = Ficheiro.objects.filter(pergunta_id=pergunta).filter(
                        avaliacao=avaliacao).count()

                    if pergunta_tem_resposta == 0:
                        formficheiro = FormFicheiro(prefix=pergunta.id)
                        formficheiro.fields['ficheiro'].upload_to = f'media/{avaliacao.id}'
                        formulario[pergunta] = formficheiro
                    else:
                        for resposta_dada in respostas_dadas:
                            formficheiro = FormFicheiro(prefix=pergunta.id, instance=resposta_dada)
                            formficheiro.fields['ficheiro'].upload_to = f'media/{avaliacao.id}'
                            formulario[pergunta].append(formficheiro)

                elif pergunta.tipo == 'MES':

                    respostas_perguntas = RespostaTextual.objects.filter(pergunta_id=pergunta.id)
                    respostas_dadas = respostas_perguntas.filter(avaliacao__instalacao_id=instalacao)
                    formulario[pergunta] = []

                    pergunta_tem_resposta = RespostaTextual.objects.filter(pergunta_id=pergunta).filter(
                        avaliacao=avaliacao).count()

                    if pergunta_tem_resposta == 0:
                        formdata = FormMes(prefix=pergunta.id)
                        formulario[pergunta] = formdata
                    else:
                        formdata = FormMes(prefix=pergunta.id)

                        for resposta_dada in respostas_dadas:

                            for opcao in formdata.fields['month'].choices:
                                if opcao[1] == resposta_dada.texto:
                                    formdata.fields['month'].initial = opcao

                        formulario[pergunta] = formdata

            subtemas[subtema] = formulario

        perguntas_form_object[tema] = subtemas


def post(request, instalacao, ano_questionario, update):
    avaliacoes = Avaliacao.objects.filter(instalacao__id=instalacao)

    avaliacao = avaliacoes.get(ano=ano_questionario)

    if request.method == "POST":

        files = request.FILES
        print(files)

        for chave, respostas_recebida in files.items():
            pergunta_tiporesposta = chave.split('-')
            id_pergunta_retirado = pergunta_tiporesposta[0]
            if id_pergunta_retirado.isdigit():
                tipofile = pergunta_tiporesposta[1]

                if tipofile == "ficheiro":

                    ficheiros = Ficheiro.objects.filter(avaliacao=avaliacao).filter(
                        pergunta=Pergunta.objects.get(id=int(id_pergunta_retirado)))

                    if len(ficheiros) > 0:
                        for ficheiro in ficheiros:
                            ficheiro.delete()

                    folder_path = os.path.join(settings.MEDIA_ROOT, f'{avaliacao.id}')

                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path)

                    filename = os.path.basename(respostas_recebida.name)

                    file_path = os.path.join(folder_path, filename)
                    with open(file_path, 'wb') as f:
                        f.write(respostas_recebida.read())

                    file = Ficheiro(
                        avaliacao=avaliacao,
                        pergunta=Pergunta.objects.get(id=int(id_pergunta_retirado)),
                        ficheiro=os.path.join(folder_path, filename)
                    )
                    file.save()

        print(request.POST)

        post = request.POST
        post_dicionario = dict(post)

        for chave, respostas_recebida in post_dicionario.items():
            for valor in respostas_recebida:
                if chave == 'tema_subtema':
                    tema_id, subtema_id = valor.split('-')

                    subtema_adicionar = SubTema.objects.get(id=subtema_id)

                    perguntas = {}

                    for pergunta in Pergunta.objects.filter(subtema_id=subtema_id):
                        if pergunta.tipo == 'NUMERO_INTEIRO':
                            formint = FormNumerosInteiros(prefix=pergunta.id)
                            perguntas[pergunta] = formint

                        elif pergunta.tipo == 'TEXTO_LIVRE':
                            formtext = FormTextoLivre(prefix=pergunta.id)
                            perguntas[pergunta] = formtext

                        elif pergunta.tipo == 'ESCOLHA_MULTIPLA_UNICA':
                            formescolha = FormEscolhaMultiplaUnica(prefix=pergunta.id)
                            formescolha.fields['opcao'].queryset = Opcao.objects.filter(pergunta_id=pergunta.id)
                            perguntas[pergunta] = formescolha

                        elif pergunta.tipo == 'FICHEIRO':
                            formficheiro = FormFicheiro(prefix=pergunta.id)
                            perguntas[pergunta] = formficheiro

                        elif pergunta.tipo == 'MES':
                            formdata = FormMes(prefix=pergunta.id)
                            perguntas[pergunta] = formdata

                    perguntas_form.get(Tema.objects.get(id=tema_id))[subtema_adicionar] = perguntas

                else:

                    pergunta_tiporesposta = chave.split('-')
                    id_pergunta_retirado = pergunta_tiporesposta[0]
                    if id_pergunta_retirado.isdigit():
                        tiporesposta = pergunta_tiporesposta[1]

                        len_bd_valores_texto = len(RespostaTextual.objects.filter(
                            avaliacao=avaliacao).filter(
                            pergunta_id=id_pergunta_retirado))

                        len_bd_valores_num = len(RespostaNumerica.objects.filter(
                            avaliacao=avaliacao).filter(
                            pergunta_id=id_pergunta_retirado))

                        if valor == '' or len_bd_valores_texto > len(respostas_recebida) or len_bd_valores_num > len(
                                respostas_recebida):

                            if update:
                                if tiporesposta == "numero":

                                    resposta_num = RespostaNumerica.objects.filter(avaliacao=avaliacao).filter(
                                        pergunta=Pergunta.objects.get(id=int(id_pergunta_retirado)))

                                    resposta_num_list = RespostaNumerica.objects.filter(
                                        avaliacao=avaliacao,
                                        pergunta=Pergunta.objects.get(id=int(id_pergunta_retirado))
                                    ).values_list('numero', flat=True)

                                    respostas_post = list(resposta_num_list)
                                    for resposta_recebida in respostas_recebida:
                                        if resposta_recebida in resposta_num_list:
                                            respostas_post.remove(resposta_recebida)

                                    for elementos_remove in respostas_post:
                                        delete = resposta_num.get(numero=elementos_remove)
                                        delete.delete()

                                elif tiporesposta == "texto" or tiporesposta == "month":
                                    resposta_txt = RespostaTextual.objects.filter(avaliacao=avaliacao).filter(
                                        pergunta=Pergunta.objects.get(id=int(id_pergunta_retirado)))

                                    resposta_txt_list = RespostaTextual.objects.filter(
                                        avaliacao=avaliacao,
                                        pergunta=Pergunta.objects.get(id=int(id_pergunta_retirado))
                                    ).values_list('texto', flat=True)

                                    respostas_post = list(resposta_txt_list)
                                    for resposta_recebida in respostas_recebida:
                                        if resposta_recebida in resposta_txt_list:
                                            respostas_post.remove(resposta_recebida)

                                    for elementos_remove in respostas_post:
                                        delete = resposta_txt.get(texto=elementos_remove)
                                        delete.delete()

                                elif tiporesposta == "opcao":

                                    resposta_txt = RespostaTextual(
                                        avaliacao=avaliacao,  # só com o login feito é que fica bom
                                        pergunta=Pergunta.objects.get(id=int(id_pergunta_retirado)),
                                        texto=
                                        Pergunta.objects.get(id=int(id_pergunta_retirado)).opcoes.order_by('nome')[
                                            int(valor)],
                                    )

                                    # resposta_txt.save()
                                    #
                                    # pergunta = Pergunta.objects.get(id=id_pergunta_retirado)
                                    #
                                    # opcoes_pergunta = RespostaTextual.objects.filter(pergunta_id=pergunta.id)
                                    #
                                    # respostas_duplicadas = list()
                                    #
                                    # for opcao in opcoes_pergunta:
                                    #     if opcao.texto in respostas_duplicadas:
                                    #         opcao.delete()
                                    #     else:
                                    #         respostas_duplicadas.append(opcao.texto)
                                elif tiporesposta == "opcoes":

                                    if int(valor) != 100:
                                        pergunta = Pergunta.objects.get(id=int(id_pergunta_retirado))
                                        tema_pergunta = pergunta.subtema.tema.id
                                        subtemas = SubTema.objects.filter(tema_id=tema_pergunta)

                                        opcoes_DB = list(
                                            RespostaTextual.objects.filter(avaliacao=avaliacao).filter(
                                                pergunta_id=pergunta.id).values_list(
                                                'texto',
                                                flat=True))

                                        for opcao_DB in opcoes_DB:
                                            slugify(opcao_DB)

                                        valores_nao_remover = list()

                                        for resposta_id in respostas_recebida:
                                            if int(resposta_id) != 100:
                                                opcao = \
                                                    Pergunta.objects.get(
                                                        id=int(id_pergunta_retirado)).opcoes.order_by(
                                                        'nome')[int(resposta_id) - 1]
                                                if slugify(opcao.nome) not in opcoes_DB:
                                                    valores_nao_remover.append(opcao.nome)

                                        set_opcoes_DB = set(opcoes_DB)
                                        set_valores_nao_remover = set(valores_nao_remover)

                                        diferenca_simetrica = set_opcoes_DB.symmetric_difference(
                                            set_valores_nao_remover)

                                        diferenca_simetrica = list(diferenca_simetrica)

                                        print(diferenca_simetrica)

                                        for valor_delete in diferenca_simetrica:
                                            RespostaTextual.objects.filter(avaliacao=avaliacao).filter(
                                                pergunta_id=pergunta.id).get(
                                                texto=valor_delete).delete()

                                        for valores_remove in diferenca_simetrica:
                                            for subtema in subtemas:
                                                if slugify(subtema.nome) == slugify(valores_remove):
                                                    subtema_perguntas = Pergunta.objects.filter(
                                                        subtema_id=subtema.id)
                                                    for pergunta in subtema_perguntas:
                                                        resposta_textual = RespostaTextual.objects.filter(
                                                            avaliacao=avaliacao).filter(
                                                            pergunta_id=pergunta.id)
                                                        resposta_inteiro = RespostaNumerica.objects.filter(
                                                            avaliacao=avaliacao).filter(
                                                            pergunta_id=pergunta.id)
                                                        resposta_ficheiro = Ficheiro.objects.filter(
                                                            avaliacao=avaliacao).filter(
                                                            pergunta_id=pergunta.id)

                                                        print(resposta_ficheiro)
                                                        print('3')

                                                        for resposta_t in resposta_textual:
                                                            resposta_t.delete()

                                                        for resposta_i in resposta_inteiro:
                                                            resposta_i.delete()

                                                        for resposta_f in resposta_ficheiro:
                                                            resposta_f.delete()
                                        return redirect('/')
                                    else:
                                        print('a')
                        elif valor != '':

                            if tiporesposta == "numero":

                                subtema_repetido = Pergunta.objects.get(
                                    id=id_pergunta_retirado).subtema.resposta_duplicavel
                                pergunta_repetida = Pergunta.objects.get(
                                    id=id_pergunta_retirado).resposta_permite_repetidos

                                if not (subtema_repetido is True and pergunta_repetida is False):
                                    if not (subtema_repetido is False and pergunta_repetida is True):
                                        verificaResposta1 = RespostaNumerica.objects.filter(
                                            avaliacao=avaliacao).filter(
                                            pergunta_id=id_pergunta_retirado)
                                        verificaResposta1.delete()

                                if (subtema_repetido is True and pergunta_repetida is False) or (
                                        subtema_repetido is False and pergunta_repetida is True):
                                    verificaResposta1 = RespostaNumerica.objects.filter(
                                        avaliacao=avaliacao).filter(
                                        pergunta_id=id_pergunta_retirado)

                                    for item in verificaResposta1:
                                        numero_repetido = item.numero
                                        respostas_repetidas = RespostaNumerica.objects.filter(
                                            avaliacao=avaliacao,
                                            pergunta_id=id_pergunta_retirado,
                                            numero=numero_repetido
                                        ).order_by('id')[1:]

                                        for resposta in respostas_repetidas:
                                            resposta.delete()

                                resposta_num = RespostaNumerica(
                                    avaliacao=avaliacao,
                                    pergunta=Pergunta.objects.get(id=int(id_pergunta_retirado)),
                                    numero=int(valor),
                                )

                                respostas_dadas = RespostaNumerica.objects.filter(avaliacao=avaliacao).filter(
                                    pergunta=Pergunta.objects.get(id=int(id_pergunta_retirado))).values_list('numero',
                                                                                                             flat=True)
                                if valor not in respostas_dadas:
                                    resposta_num.save()

                            elif tiporesposta == "texto" or tiporesposta == "month":

                                subtema_repetido = Pergunta.objects.get(
                                    id=id_pergunta_retirado).subtema.resposta_duplicavel
                                pergunta_repetida = Pergunta.objects.get(
                                    id=id_pergunta_retirado).resposta_permite_repetidos

                                if not (subtema_repetido is True and pergunta_repetida is False):
                                    if not (subtema_repetido is False and pergunta_repetida is True):
                                        verificaResposta1 = RespostaTextual.objects.filter(
                                            avaliacao=avaliacao).filter(
                                            pergunta_id=id_pergunta_retirado)
                                        verificaResposta1.delete()

                                if (subtema_repetido is True and pergunta_repetida is False) or (
                                        subtema_repetido is False and pergunta_repetida is True):
                                    verificaResposta1 = RespostaTextual.objects.filter(
                                        avaliacao=avaliacao).filter(
                                        pergunta_id=id_pergunta_retirado)
                                    for item in verificaResposta1:
                                        texto_repetido = item.texto

                                        respostas_repetidas = RespostaTextual.objects.filter(
                                            avaliacao=avaliacao,
                                            pergunta_id=id_pergunta_retirado,
                                            texto=texto_repetido
                                        ).order_by('id')[1:]

                                        for resposta in respostas_repetidas:
                                            resposta.delete()

                                resposta_txt = RespostaTextual(
                                    avaliacao=avaliacao,  # só com o login feito é que fica bom
                                    pergunta=Pergunta.objects.get(id=int(id_pergunta_retirado)),
                                    texto=valor,
                                )

                                respostas_dadas = RespostaTextual.objects.filter(avaliacao=avaliacao).filter(
                                    pergunta=Pergunta.objects.get(id=int(id_pergunta_retirado))).values_list('texto',
                                                                                                             flat=True)
                                if valor not in respostas_dadas:
                                    resposta_txt.save()

                            elif tiporesposta == "opcao":

                                verificaResposta1 = RespostaTextual.objects.filter(
                                    avaliacao=avaliacao).filter(
                                    pergunta_id=id_pergunta_retirado)  # só com o login feito é que fica bom
                                verificaResposta1.delete()  # ver se ele remove apenas o valor da conta associada, e não de todas as contas

                                resposta_txt = RespostaTextual(
                                    avaliacao=avaliacao,  # só com o login feito é que fica bom
                                    pergunta=Pergunta.objects.get(id=int(id_pergunta_retirado)),
                                    texto=Opcao.objects.get(id=int(valor)),
                                )
                                resposta_txt.save()


                            elif tiporesposta == "opcoes":

                                len_bd_valores_texto_opt = len(RespostaTextual.objects.filter(
                                    avaliacao=avaliacao).filter(
                                    pergunta_id=id_pergunta_retirado))

                                if len_bd_valores_texto_opt > len(respostas_recebida) - 1:

                                    if int(valor) == 100 and len(respostas_recebida) == 1:
                                        pergunta = Pergunta.objects.get(id=int(id_pergunta_retirado))
                                        tema_pergunta = pergunta.subtema.tema.id
                                        subtemas = SubTema.objects.filter(tema_id=tema_pergunta)

                                        opcoes_DB = list(
                                            RespostaTextual.objects.filter(avaliacao=avaliacao).filter(
                                                pergunta_id=pergunta.id).values_list(
                                                'texto',
                                                flat=True))

                                        for opcao_DB in opcoes_DB:
                                            slugify(opcao_DB)

                                        valores_nao_remover = list()

                                        for resposta_id in respostas_recebida:
                                            if int(resposta_id) != 100:
                                                opcao = \
                                                    Pergunta.objects.get(
                                                        id=int(id_pergunta_retirado)).opcoes.order_by(
                                                        'nome')[int(resposta_id) - 1]
                                                if slugify(opcao.nome) not in opcoes_DB:
                                                    valores_nao_remover.append(opcao.nome)

                                        set_opcoes_DB = set(opcoes_DB)
                                        set_valores_nao_remover = set(valores_nao_remover)

                                        diferenca_simetrica = set_opcoes_DB.symmetric_difference(
                                            set_valores_nao_remover)

                                        diferenca_simetrica = list(diferenca_simetrica)

                                        print(diferenca_simetrica)

                                        for valor_delete in diferenca_simetrica:
                                            try:
                                                RespostaTextual.objects.filter(avaliacao=avaliacao).filter(
                                                    pergunta_id=pergunta.id).get(
                                                    texto=valor_delete).delete()
                                            finally:
                                                break

                                        for valores_remove in diferenca_simetrica:
                                            for subtema in subtemas:
                                                if slugify(subtema.nome) == slugify(valores_remove):
                                                    subtema_perguntas = Pergunta.objects.filter(
                                                        subtema_id=subtema.id)
                                                    for pergunta in subtema_perguntas:
                                                        resposta_textual = RespostaTextual.objects.filter(
                                                            avaliacao=avaliacao).filter(
                                                            pergunta_id=pergunta.id)
                                                        resposta_inteiro = RespostaNumerica.objects.filter(
                                                            avaliacao=avaliacao).filter(
                                                            pergunta_id=pergunta.id)
                                                        resposta_ficheiro = Ficheiro.objects.filter(
                                                            avaliacao=avaliacao).filter(
                                                            pergunta_id=pergunta.id)

                                                        print(resposta_ficheiro)
                                                        print('1')

                                                        for resposta_t in resposta_textual:
                                                            resposta_t.delete()

                                                        for resposta_i in resposta_inteiro:
                                                            resposta_i.delete()

                                                        for resposta_f in resposta_ficheiro:
                                                            resposta_f.delete()
                                        return redirect('/')
                                    elif int(valor) != 100:
                                        pergunta = Pergunta.objects.get(id=int(id_pergunta_retirado))
                                        tema_pergunta = pergunta.subtema.tema.id
                                        subtemas = SubTema.objects.filter(tema_id=tema_pergunta)

                                        opcoes_DB = list(
                                            RespostaTextual.objects.filter(avaliacao=avaliacao).filter(
                                                pergunta_id=pergunta.id).values_list('texto',
                                                                                     flat=True))

                                        for opcao_DB in opcoes_DB:
                                            slugify(opcao_DB)

                                        valores_nao_remover = list()

                                        for resposta_id in respostas_recebida:
                                            if int(resposta_id) != 100:
                                                if int(resposta_id) == 0:
                                                    opcao = \
                                                        Pergunta.objects.get(
                                                            id=int(id_pergunta_retirado)).opcoes.order_by(
                                                            'nome')[int(resposta_id)]
                                                else:
                                                    opcao = \
                                                        Pergunta.objects.get(
                                                            id=int(id_pergunta_retirado)).opcoes.order_by(
                                                            'nome')[int(resposta_id) - 1]
                                                if slugify(opcao.nome) not in opcoes_DB:
                                                    valores_nao_remover.append(opcao.nome)

                                        set_opcoes_DB = set(opcoes_DB)
                                        set_valores_nao_remover = set(valores_nao_remover)

                                        diferenca_simetrica = set_opcoes_DB.symmetric_difference(
                                            set_valores_nao_remover)

                                        diferenca_simetrica = list(diferenca_simetrica)

                                        for valor_delete in diferenca_simetrica:
                                            try:
                                                RespostaTextual.objects.filter(avaliacao=avaliacao).filter(
                                                    pergunta_id=pergunta.id).get(
                                                    texto=valor_delete).delete()
                                            finally:
                                                break

                                        for valores_remove in diferenca_simetrica:
                                            for subtema in subtemas:
                                                if slugify(subtema.nome) == slugify(valores_remove):
                                                    subtema_perguntas = Pergunta.objects.filter(subtema_id=subtema.id)
                                                    for pergunta in subtema_perguntas:
                                                        resposta_textual = RespostaTextual.objects.filter(
                                                            avaliacao=avaliacao).filter(
                                                            pergunta_id=pergunta.id)
                                                        resposta_inteiro = RespostaNumerica.objects.filter(
                                                            avaliacao=avaliacao).filter(
                                                            pergunta_id=pergunta.id)
                                                        resposta_ficheiro = Ficheiro.objects.filter(
                                                            avaliacao=avaliacao).filter(
                                                            pergunta_id=pergunta.id)

                                                        print(resposta_ficheiro)
                                                        print('2')

                                                        for resposta_t in resposta_textual:
                                                            resposta_t.delete()

                                                        for resposta_i in resposta_inteiro:
                                                            resposta_i.delete()

                                                        for resposta_f in resposta_ficheiro:
                                                            resposta_f.delete()

                                        return redirect('/')

                                else:
                                    if int(valor) != 100:
                                        if update:
                                            resposta_txt = RespostaTextual(
                                                avaliacao=avaliacao,  # só com o login feito é que fica bom
                                                pergunta=Pergunta.objects.get(id=int(id_pergunta_retirado)),
                                                texto=
                                                Pergunta.objects.get(id=int(id_pergunta_retirado)).opcoes.order_by(
                                                    'nome')[
                                                    int(valor) - 1],
                                            )
                                            resposta_txt.save()
                                        else:
                                            resposta_txt = RespostaTextual(
                                                avaliacao=avaliacao,  # só com o login feito é que fica bom
                                                pergunta=Pergunta.objects.get(id=int(id_pergunta_retirado)),
                                                texto=
                                                Pergunta.objects.get(id=int(id_pergunta_retirado)).opcoes.order_by(
                                                    'nome')[
                                                    int(valor)],
                                            )
                                            resposta_txt.save()

                                    pergunta = Pergunta.objects.get(id=id_pergunta_retirado)

                                    opcoes_pergunta = RespostaTextual.objects.filter(avaliacao=avaliacao).filter(
                                        pergunta_id=pergunta.id)

                                    respostas_duplicadas = list()

                                    for opcao in opcoes_pergunta:
                                        if opcao.texto in respostas_duplicadas:
                                            opcao.delete()
                                        else:
                                            respostas_duplicadas.append(opcao.texto)


@login_required
def formulario_view(request):
    criar_perguntas_form(perguntas_form)

    instalacao_id = request.GET.get('instalacao')

    post(request, instalacao_id, 2024, update=False)

    if request.method == "POST" or request.method == "FILES":
        base_url = request.path_info
        nova_url = f"{base_url}?instalacao={instalacao_id}"

        return HttpResponseRedirect(nova_url)

    context = {
        'perguntas_form': perguntas_form,
        'instalacao_submmit': Instalacao.objects.get(id=instalacao_id).submetido
    }

    return render(request, 'formulario.html', context)


@login_required
def update_form_view(request, tema_id):
    instalacao_id = request.GET.get('instalacao')

    ano_questionario = 2024

    update_respostas_view(request, perguntas_update_form, instalacao_id, ano_questionario)

    post(request, instalacao_id, 2024, update=True)

    if request.method == "POST" or request.method == "FILES":
        base_url = request.path_info
        nova_url = f"{base_url}?instalacao={instalacao_id}"

        return HttpResponseRedirect(nova_url)

    context = {
        'perguntas_form': perguntas_update_form,
        'instalacao_submmit': Instalacao.objects.get(id=instalacao_id).submetido
    }

    return render(request, 'update_formulario.html', context)


perguntas_respostas_submmit = {}


def guarda_respostas_submmit(instalacao, ano_questionario, perguntas_submmit_object):
    avaliacoes = Avaliacao.objects.filter(instalacao_id=instalacao)

    avaliacao = avaliacoes.get(ano=ano_questionario)

    questionario = avaliacao.questionario

    for tema in questionario.temas.all().order_by('ordem_perguntas_formulario'):

        subtemas = {}

        subtemas_todos = SubTema.objects.filter(tema_id=tema.id).order_by('nome')

        if subtemas_todos.filter(nome='Valores relevantes').exists() & subtemas_todos.filter(nome='Outro').exists():
            excluindo_valores = subtemas_todos.exclude(nome='Valores relevantes')
            subtema_valores = subtemas_todos.get(nome='Valores relevantes')

            valores_escluidos = excluindo_valores.exclude(nome='Outro')
            subtema_outro = subtemas_todos.get(nome='Outro')

            subtemas_todos = [subtema_valores] + list(valores_escluidos) + [subtema_outro]

        elif subtemas_todos.filter(nome='Outro').exists():
            valores_escluidos = subtemas_todos.exclude(nome='Outro')
            subtema_outro = subtemas_todos.get(nome='Outro')

            subtemas_todos = list(valores_escluidos) + [subtema_outro]

        elif subtemas_todos.filter(nome='Outros').exists():
            valores_escluidos = subtemas_todos.exclude(nome='Outros')
            subtema_outro = subtemas_todos.get(nome='Outros')

            subtemas_todos = list(valores_escluidos) + [subtema_outro]

        for subtema in subtemas_todos:
            respostas = {}

            # if(subtema.resposta_duplicavel is False):

            perguntas_todos = Pergunta.objects.filter(subtema_id=subtema.id).order_by('texto')

            if perguntas_todos.filter(tipo='ESCOLHA_MULTIPLA_VARIAS').exists():
                valores_escluidos = perguntas_todos.exclude(tipo='ESCOLHA_MULTIPLA_VARIAS')
                pergunta_escluida = perguntas_todos.get(tipo='ESCOLHA_MULTIPLA_VARIAS')

                perguntas_todos = [pergunta_escluida] + list(valores_escluidos)

            elif perguntas_todos.filter(texto='Com potência de').exists():
                valores_escluidos = perguntas_todos.exclude(texto='Com potência de')
                pergunta_escluida = perguntas_todos.get(texto='Com potência de')

                perguntas_todos = list(valores_escluidos) + [pergunta_escluida]

            elif perguntas_todos.filter(texto='Com valor de').exists():
                valores_escluidos = perguntas_todos.exclude(texto='Com valor de')
                pergunta_escluida = perguntas_todos.get(texto='Com valor de')

                perguntas_todos = list(valores_escluidos) + [pergunta_escluida]

            elif perguntas_todos.filter(texto='Nome').exists():
                valores_escluidos = perguntas_todos.exclude(texto='Nome')
                pergunta_escluida = perguntas_todos.get(texto='Nome')

                perguntas_todos = [pergunta_escluida] + list(valores_escluidos)

            elif perguntas_todos.filter(texto='Número de veículos da instalação').exists():
                valores_escluidos = perguntas_todos.exclude(texto='Nome')
                pergunta_escluida = perguntas_todos.get(texto='Nome')

                perguntas_todos = [pergunta_escluida] + list(valores_escluidos)

            for pergunta in perguntas_todos:

                if pergunta.tipo == 'NUMERO_INTEIRO':

                    respostas_perguntas = RespostaNumerica.objects.filter(pergunta_id=pergunta.id)
                    respostas_dadas = respostas_perguntas.filter(avaliacao__instalacao_id=instalacao)

                    respostas[pergunta] = []
                    for resposta_dada in respostas_dadas:
                        respostas[pergunta].append(resposta_dada)

                elif pergunta.tipo == 'TEXTO_LIVRE' or pergunta.tipo == 'ESCOLHA_MULTIPLA_UNICA' or pergunta.tipo == 'ESCOLHA_MULTIPLA_VARIAS' or pergunta.tipo == 'MES':

                    respostas_perguntas = RespostaTextual.objects.filter(pergunta_id=pergunta.id)
                    respostas_dadas = respostas_perguntas.filter(avaliacao__instalacao_id=instalacao).order_by(
                        'texto')

                    respostas[pergunta] = []
                    for resposta_dada in respostas_dadas:
                        respostas[pergunta].append(resposta_dada)


                elif pergunta.tipo == 'FICHEIRO':
                    respostas_perguntas = Ficheiro.objects.filter(pergunta_id=pergunta.id)
                    respostas_dadas = respostas_perguntas.filter(avaliacao__instalacao_id=instalacao)

                    respostas[pergunta] = []
                    for resposta_dada in respostas_dadas:
                        respostas[pergunta].append((resposta_dada.ficheiro.name.split('media/')[0],
                                                    f'media/{avaliacao.id}/{resposta_dada.ficheiro.url}'))

            subtemas[subtema] = respostas

        perguntas_submmit_object[tema] = subtemas


@login_required
def respostas_view(request):
    instalacao_id = request.GET.get('instalacao')

    ano_questionario = 2024

    guarda_respostas_submmit(instalacao_id, ano_questionario, perguntas_respostas_submmit)

    context = {
        'perguntas_respostas_submmit': perguntas_respostas_submmit,
        'instalacao_submmit': Instalacao.objects.get(id=instalacao_id).submetido

    }

    return render(request, 'submmit.html', context)


@login_required
def post_request_submmit(request):
    post = request.POST

    post_dicionario = dict(post)
    lista_items = list(post_dicionario.items())
    print(lista_items)

    if lista_items[0][0] == 'metodo' and lista_items[0][1][0] == 'post':
        if lista_items[1][0] == 'tipo_query' and lista_items[1][1][0] == 'editar':
            print('edit')
        elif lista_items[1][0] == 'tipo_query' and lista_items[1][1][0] == 'remover':
            if lista_items[2][0] == 'tipo_resposta' and lista_items[2][1][0] == 'NUMERO_INTEIRO':
                resposta = RespostaNumerica.objects.get(id=int(lista_items[3][1][0]))
                resposta.delete()

            elif lista_items[2][0] == 'tipo_resposta' and (
                    lista_items[2][1][0] == 'TEXTO_LIVRE' or lista_items[2][1][0] == 'ESCOLHA_MULTIPLA_UNICA'):
                resposta = RespostaTextual.objects.get(id=int(lista_items[3][1][0]))
                resposta.delete()

            elif lista_items[2][0] == 'tipo_resposta' and lista_items[2][1][0] == 'ESCOLHA_MULTIPLA_VARIAS':
                eliminar_valores_escolha_multipla(lista_items)

            elif lista_items[2][0] == 'tipo_resposta' and lista_items[2][1][0] == 'FICHEIRO':
                print('ficheiro')
    elif lista_items[0][0] == 'instalacao':
        obsjetoSave = Instalacao.objects.get(id=int(lista_items[0][1][0]))
        obsjetoSave.submetido = True
        obsjetoSave.save()

    return HttpResponse("POST request")


def eliminar_valores_escolha_multipla(lista_items):
    resposta = RespostaTextual.objects.get(id=int(lista_items[3][1][0]))
    print(resposta)
    subtema_resposta = resposta.pergunta.subtema
    tema = Tema.objects.get(nome=subtema_resposta.tema.nome)
    try:
        subtema = SubTema.objects.filter(tema_id=tema.id).get(nome=resposta.texto)

        perguntas = Pergunta.objects.filter(subtema_id=subtema.id)

        for pergunta in perguntas:

            if pergunta.tipo == 'NUMERO_INTEIRO':
                respostas_eliminar = RespostaNumerica.objects.filter(pergunta_id=pergunta.id)
                for resposta_eliminar in respostas_eliminar:
                    resposta_eliminar.delete()

            elif pergunta.tipo == 'TEXTO_LIVRE' or pergunta.tipo == 'MES' or pergunta.tipo == 'ESCOLHA_MULTIPLA_UNICA':
                respostas_eliminar = RespostaTextual.objects.filter(pergunta_id=pergunta.id)
                for resposta_eliminar in respostas_eliminar:
                    resposta_eliminar.delete()


    except SubTema.DoesNotExist:
        subtema = SubTema.objects.get(id=subtema_resposta.id)
        perguntas = Pergunta.objects.filter(subtema_id=subtema.id)
        lista_perguntas = list(perguntas)

        pergunta_remover = None
        for pergunta in lista_perguntas:
            if pergunta.texto.split("com potência média de")[0].strip() == resposta.texto:
                pergunta_remover = pergunta

        if pergunta_remover != None:
            if pergunta.tipo == 'NUMERO_INTEIRO':
                resposta_eliminar = RespostaNumerica.objects.get(pergunta_id=pergunta.id)
                resposta_eliminar.delete()

            elif pergunta.tipo == 'TEXTO_LIVRE' or pergunta.tipo == 'MES' or pergunta.tipo == 'ESCOLHA_MULTIPLA_UNICA':
                resposta_eliminar = RespostaTextual.objects.get(pergunta_id=pergunta.id)
                resposta_eliminar.delete()
    resposta.delete()


@register.filter(name='split')
def split(value, key):
    return value.split(key)


@login_required
def dashboard_view(request):
    consumosAnuaisElectricidade = getRespostaNumericaOr0(11)
    consumosAnuaisGasNatural = getRespostaNumericaOr0(21)
    consumosAnuaisPropano = getRespostaNumericaOr0(31)
    consumosAnuaisGasoleo = getRespostaNumericaOr0(41)
    consumosAnuaisGasolina = getRespostaNumericaOr0(51)
    consumosAnuaisFotovoltaica = getRespostaNumericaOr0(61)
    consumosAnuaisBiomassa = getRespostaNumericaOr0(208)
    consumosAnuaisEolica = getRespostaNumericaOr0(81)
    consumosAnuaisTermica = getRespostaNumericaOr0(91)
    consumosAnuaisOutros = getRespostaNumericaOr0(101)

    consumos = [consumosAnuaisElectricidade, consumosAnuaisGasNatural, consumosAnuaisPropano,
                consumosAnuaisGasoleo, consumosAnuaisGasolina, consumosAnuaisFotovoltaica,
                consumosAnuaisBiomassa, consumosAnuaisEolica, consumosAnuaisTermica, consumosAnuaisOutros]

    consumos_labels = ["Electricidade", "Gas Natural", "Propano", "Gasoleo", "Gasolina", "Fotovoltaica", "Biomassa",
                       "Eolica", "Térmica", "Outros"]

    custosAnuaisElectricidade = getRespostaNumericaOr0(12)
    custosAnuaisGasNatural = getRespostaNumericaOr0(22)
    custosAnuaisPropano = getRespostaNumericaOr0(32)
    custosAnuaisGasoleo = getRespostaNumericaOr0(42)
    custosAnuaisGasolina = getRespostaNumericaOr0(52)
    custosAnuaisFotovoltaica = getRespostaNumericaOr0(62)
    custosAnuaisBiomassa = getRespostaNumericaOr0(209)
    custosAnuaisEolica = getRespostaNumericaOr0(82)
    custosAnuaisTermica = getRespostaNumericaOr0(92)
    custosAnuaisOutros = getRespostaNumericaOr0(103)

    custos = [custosAnuaisElectricidade, custosAnuaisGasNatural, custosAnuaisPropano,
              custosAnuaisGasoleo, custosAnuaisGasolina, custosAnuaisFotovoltaica,
              custosAnuaisBiomassa, custosAnuaisEolica, custosAnuaisTermica, custosAnuaisOutros]

    custosconsumo = [
        divByZero(custosAnuaisElectricidade, consumosAnuaisElectricidade),
        divByZero(custosAnuaisGasNatural, consumosAnuaisGasNatural),
        divByZero(custosAnuaisPropano, consumosAnuaisPropano),
        divByZero(custosAnuaisGasoleo, consumosAnuaisGasoleo),
        divByZero(custosAnuaisGasolina, consumosAnuaisGasolina),
        divByZero(custosAnuaisFotovoltaica, consumosAnuaisFotovoltaica),
        divByZero(custosAnuaisBiomassa, consumosAnuaisBiomassa),
        divByZero(custosAnuaisEolica, consumosAnuaisEolica),
        divByZero(custosAnuaisTermica, consumosAnuaisTermica),
        divByZero(custosAnuaisOutros, consumosAnuaisOutros)

    ]

    faturasMinimaskWh = [
        getRespostaNumericaOr0(15),
        getRespostaNumericaOr0(25),
        getRespostaNumericaOr0(35),
        getRespostaNumericaOr0(45),
        getRespostaNumericaOr0(55),
        getRespostaNumericaOr0(65),
        getRespostaNumericaOr0(211),
        getRespostaNumericaOr0(85),
        getRespostaNumericaOr0(95),
        getRespostaNumericaOr0(106)
    ]

    faturasMaximaskWh = [
        getRespostaNumericaOr0(18),
        getRespostaNumericaOr0(28),
        getRespostaNumericaOr0(38),
        getRespostaNumericaOr0(48),
        getRespostaNumericaOr0(58),
        getRespostaNumericaOr0(68),
        getRespostaNumericaOr0(214),
        getRespostaNumericaOr0(88),
        getRespostaNumericaOr0(98),
        getRespostaNumericaOr0(103)
    ]

    faturasMinimasEur = [
        getRespostaNumericaOr0(17),
        getRespostaNumericaOr0(27),
        getRespostaNumericaOr0(37),
        getRespostaNumericaOr0(47),
        getRespostaNumericaOr0(57),
        getRespostaNumericaOr0(67),
        getRespostaNumericaOr0(213),
        getRespostaNumericaOr0(87),
        getRespostaNumericaOr0(97),
        getRespostaNumericaOr0(108)
    ]

    faturasMaximasEur = [
        getRespostaNumericaOr0(20),
        getRespostaNumericaOr0(30),
        getRespostaNumericaOr0(40),
        getRespostaNumericaOr0(50),
        getRespostaNumericaOr0(60),
        getRespostaNumericaOr0(70),
        getRespostaNumericaOr0(216),
        getRespostaNumericaOr0(90),
        getRespostaNumericaOr0(100),
        getRespostaNumericaOr0(105)
    ]

    faturas = zip(consumos_labels, faturasMinimaskWh, faturasMinimasEur, faturasMaximaskWh, faturasMaximasEur)

    return render(request, 'dashboard.html', {"consumos": consumos, "consumos_labels": consumos_labels,
                                              "custos": custos, "custosconsumo": custosconsumo, "faturas": faturas})


def getRespostaNumericaOr0(pergunta_id):
    if RespostaNumerica.objects.filter(pergunta_id=Pergunta.objects.get(id=pergunta_id)).first():
        return RespostaNumerica.objects.filter(pergunta_id=Pergunta.objects.get(id=pergunta_id)).first().numero
    else:
        return 0


def divByZero(n, d):
    return n / d if d else 0


def login_view(request):
    print(getEntidade(request))
    if request.method == 'POST':
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            return redirect("/")

    return render(request, 'login.html', {"authForm": AuthenticationForm()})


@login_required
def logout_view(request):
    logout(request)
    return redirect("/login")


def sign_up_view(request):
    formEntidade = FormEntidade(request.POST or None)
    formUser = SignupForm(request.POST or None)

    if request.method == "POST":
        if formEntidade.is_valid():
            user = formUser.save(commit=True)

            utilizador = formEntidade.save(commit=False)

            utilizador.user = user
            utilizador.save()

            return redirect("/login")

    return render(request, 'signup.html', {"formUser": formUser, "formUtilizador": formEntidade})


@login_required
def instalacoes_view(request):
    entidade = getEntidade(request)

    instalacaoForm = FormInstalacoes(request.POST or None)

    if request.method == "POST":
        instalacao = instalacaoForm.save(commit=False)

        entidade.instalacoes.add(instalacao, bulk=False)

        instalacao = instalacaoForm.save(commit=True)

        avaliacao = Avaliacao(instalacao=instalacao, ano=datetime.date.today().year,
                              questionario=Questionario.objects.filter(id=3).first())

        avaliacao.save()

    instalacaoForm = FormInstalacoes()

    return render(request, 'instalacoes.html',
                  {'instalacoes': Instalacao.objects.filter(entidade=entidade), 'instalacaoForm': instalacaoForm})


@login_required
def editinstalacao_view(request):
    instalacao = Instalacao.objects.filter(id=request.GET["instalacao"]).first()

    print(instalacao)

    if request.method == 'POST':
        editInstalacaoForm = FormInstalacoes(request.POST, instance=instalacao)
        editInstalacaoForm.save()
        return redirect('/')

    editInstalacaoForm = FormInstalacoes(instance=instalacao)
    return render(request, 'editinstalacao.html', {"instalacaoForm": editInstalacaoForm})


@login_required
def deleteinstalacao_view(request):
    instalacao = Instalacao.objects.filter(id=request.GET["instalacao"]).first()
    instalacao.delete()

    return redirect('/')


def passwordreset_view(request):
    form = PasswordResetForm()

    if request.method == 'GET':
        if "user" in request.GET and "token" in request.GET:
            form = PasswordChangeForm(User.objects.filter(id=request.GET["user"]).first())
            print("stuff")

    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if "email" in request.POST and form.is_valid() and User.objects.filter(email=request.POST["email"]).exists():

            message = ("Password reset link: " + "http://127.0.0.1:8000/password_reset?user=" +
                       str(User.objects.filter(email=request.POST["email"]).first().id) + "&token=" + str(1))

            send_mail(
                "Subject here",
                message,
                "from@example.com",
                ["to@example.com"],
                fail_silently=False,
            )

        else:
            print(User.objects.filter(id=request.GET["user"]).first())
            form = PasswordChangeForm(user=User.objects.filter(id=request.GET["user"]).first(), data=request.POST)
            if form.is_valid():
                form.save()
                return redirect('/login')
            pass

    return render(request, 'passwordreset.html', {"form": form})
