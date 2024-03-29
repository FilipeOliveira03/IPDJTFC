from django.forms import ModelForm
from django import forms
from .models import *


class FormNumerosInteiros(ModelForm):

    class Meta:
        model = RespostaNumerica
        fields = ['numero']
        labels = {'numero': ''}


class FormTextoLivre(ModelForm):
    class Meta:
        model = RespostaTextual
        fields = ['texto']
        labels = {'texto': ''}


class FormTextoLivreObservacoes(ModelForm):
    class Meta:
        model = RespostaTextual
        fields = ['texto']
        labels = {'texto': ''}

        widgets = {
            'texto': forms.Textarea(attrs={'cols': 25, 'rows': 20}),
        }


class FormEscolhaMultipla(ModelForm):
    opcao = forms.ModelChoiceField(queryset=Opcao.objects.all(), empty_label='')

    class Meta:
        model = RespostaTextual
        fields = ['opcao']
        labels = {'opcao': ''}

    def save(self, commit=True):
        instance = super().save(commit=False)
        opcao_escolhida = self.cleaned_data['opcao']
        instance.texto = opcao_escolhida.nome
        if commit:
            instance.save()
        return instance

class FormFicheiro(ModelForm):
    class Meta:
        model = Ficheiro
        fields = ['ficheiro']
