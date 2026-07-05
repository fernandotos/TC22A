import io
import pandas as pd
from django.http import HttpResponse
from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Category, Player, CategoryPlayer, Match, HomeBanner
from .services import process_excel_tournament

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
    list_display = ('name',)
    inlines = [CategoryPlayerInline]
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-excel/', self.admin_site.admin_view(self.upload_excel_view), name='tournaments_category_upload_excel'),
            path('download-template/', self.admin_site.admin_view(self.download_template_view), name='tournaments_category_download_template'),
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
        response['Content-Disposition'] = 'attachment; filename="template_barragem.xlsx"'
        return response

    def upload_excel_view(self, request):
        if request.method == 'POST':
            excel_file = request.FILES.get('excel_file')

            if not excel_file:
                messages.error(request, "Por favor, selecione um arquivo Excel.")
            else:
                try:
                    success, main_msg, error_logs = process_excel_tournament(excel_file)
                    messages.success(request, main_msg)
                    for log in error_logs:
                        messages.warning(request, log)
                except Exception as e:
                    messages.error(request, f"Erro ao processar arquivo: {str(e)}")
                
                return redirect('..')
        
        context = dict(
            self.admin_site.each_context(request),
            title="Upload de Barragem (Excel)"
        )
        return render(request, 'admin/tournaments/upload_excel.html', context)

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('round_number', 'category', 'player_a', 'player_b', 'status', 'sets_a', 'sets_b')
    list_filter = ('category', 'status', 'round_number')
    search_fields = ('player_a__name', 'player_b__name')
    readonly_fields = ('winner',)

@admin.register(CategoryPlayer)
class CategoryPlayerAdmin(admin.ModelAdmin):
    list_display = ('player', 'category', 'points', 'matches_played', 'wins', 'losses')
    list_filter = ('category',)
    search_fields = ('player__name',)
    ordering = ('-points', '-wins')

@admin.register(HomeBanner)
class HomeBannerAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'current_round', 'start_date', 'end_date', 'is_active')
    list_editable = ('is_active',)
