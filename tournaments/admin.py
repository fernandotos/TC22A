import io
import pandas as pd
from django.http import HttpResponse
from django.contrib import admin
from django import forms
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Tournament, RankingTournament, KnockoutTournament, Category, Player, CategoryPlayer, Match
from .services import process_excel_tournament, process_excel_knockout

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class CategoryPlayerInline(admin.TabularInline):
    model = CategoryPlayer
    extra = 0
    readonly_fields = ('points', 'matches_played', 'wins', 'losses')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'tournament', 'is_finished')
    list_filter = ('tournament', 'is_finished')
    list_editable = ('is_finished',)
    inlines = [CategoryPlayerInline]

class CategoryInline(admin.TabularInline):
    model = Category
    extra = 0
    fields = ('name', 'is_finished')

from django.utils.safestring import mark_safe

class RankingTournamentAdminForm(forms.ModelForm):
    excel_file = forms.FileField(
        required=False, 
        label="Planilha Excel (Opcional)", 
        help_text=mark_safe("Envie a planilha para popular este Ranking ao salvar. <a href='/admin/tournaments/rankingtournament/download-template/' target='_blank'>Baixar Modelo</a>")
    )

    class Meta:
        model = RankingTournament
        fields = '__all__'

@admin.register(RankingTournament)
class RankingTournamentAdmin(admin.ModelAdmin):
    form = RankingTournamentAdminForm
    list_display = ('name', 'current_round', 'start_date', 'end_date', 'is_active')
    list_editable = ('is_active', 'current_round')
    inlines = [CategoryInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(tournament_type='ranking')

    def save_model(self, request, obj, form, change):
        obj.tournament_type = 'ranking'
        super().save_model(request, obj, form, change)
        excel_file = form.cleaned_data.get('excel_file')
        if excel_file:
            try:
                success, main_msg, error_logs = process_excel_tournament(excel_file, obj)
                messages.success(request, main_msg)
                for log in error_logs:
                    messages.warning(request, log)
            except Exception as e:
                messages.error(request, f"Erro ao processar arquivo: {str(e)}")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('download-template/', self.admin_site.admin_view(self.download_template_view), name='tournaments_rankingtournament_download_template'),
        ]
        return custom_urls + urls

    def download_template_view(self, request):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_cadastro = pd.DataFrame(columns=['Nome do Atleta', 'Categoria'])
            df_cadastro.to_excel(writer, sheet_name='Cadastro', index=False)
            
            df_confrontos = pd.DataFrame(columns=['Categoria', 'Rodada', 'Atleta A', 'Atleta B', 'Resultado'])
            df_confrontos.to_excel(writer, sheet_name='Confrontos', index=False)
            
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="template_ranking.xlsx"'
        return response

class KnockoutTournamentAdminForm(forms.ModelForm):
    excel_file = forms.FileField(
        required=False, 
        label="Planilha Excel (Opcional)", 
        help_text=mark_safe("Envie a planilha para gerar a chave eliminatória. <a href='/admin/tournaments/knockouttournament/download-template/' target='_blank'>Baixar Modelo</a>")
    )

    class Meta:
        model = KnockoutTournament
        fields = '__all__'

@admin.register(KnockoutTournament)
class KnockoutTournamentAdmin(admin.ModelAdmin):
    form = KnockoutTournamentAdminForm
    list_display = ('name', 'competition_type', 'set_format', 'start_date', 'end_date', 'is_active')
    list_editable = ('is_active',)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(tournament_type='knockout')

    def save_model(self, request, obj, form, change):
        obj.tournament_type = 'knockout'
        super().save_model(request, obj, form, change)
        excel_file = form.cleaned_data.get('excel_file')
        if excel_file:
            try:
                success, main_msg, error_logs = process_excel_knockout(excel_file, obj)
                if success:
                    messages.success(request, main_msg)
                else:
                    messages.error(request, main_msg)
            except Exception as e:
                messages.error(request, f"Erro ao processar arquivo: {str(e)}")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('download-template/', self.admin_site.admin_view(self.download_template_view), name='tournaments_knockouttournament_download_template'),
        ]
        return custom_urls + urls

    def download_template_view(self, request):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_cadastro = pd.DataFrame(columns=['Nome', 'Cabeça de Chave'])
            df_cadastro.to_excel(writer, sheet_name='Atletas', index=False)
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="template_eliminatorio.xlsx"'
        return response

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('round_number', 'phase', 'category', 'tournament', 'player_a', 'player_b', 'status')
    list_filter = ('tournament', 'category', 'status', 'round_number', 'phase')
    search_fields = ('player_a__name', 'player_b__name')
    readonly_fields = ('winner', 'next_match')
    
    fieldsets = (
        ('Informações Gerais', {
            'fields': ('tournament', 'category', 'round_number', 'phase', 'position_in_bracket', 'next_match', 'status', 'winner')
        }),
        ('Atletas', {
            'fields': ('player_a', 'player_b')
        }),
        ('Placar - Visão Geral', {
            'fields': ('sets_a', 'sets_b')
        }),
        ('Placar - Games (Set a Set)', {
            'fields': (
                ('set1_a', 'set1_b'),
                ('set2_a', 'set2_b'),
                ('set3_a', 'set3_b'),
                ('set4_a', 'set4_b'),
                ('set5_a', 'set5_b'),
            )
        }),
    )

@admin.register(CategoryPlayer)
class CategoryPlayerAdmin(admin.ModelAdmin):
    list_display = ('player', 'category', 'points', 'matches_played', 'wins', 'losses')
    list_filter = ('category',)
    search_fields = ('player__name',)
    ordering = ('-points', '-wins')


