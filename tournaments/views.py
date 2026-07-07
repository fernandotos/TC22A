from django.shortcuts import render, get_object_or_404
from .models import Tournament, Category, Match, CategoryPlayer

def home(request):
    tournaments = Tournament.objects.filter(is_active=True, tournament_type='ranking').order_by('-id')
    return render(request, 'tournaments/home.html', {'tournaments': tournaments})

def tournament_detail(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id, tournament_type='ranking')
    categories = Category.objects.filter(tournament=tournament).order_by('name')
    return render(request, 'tournaments/tournament_detail.html', {'tournament': tournament, 'categories': categories})

def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    matches = Match.objects.filter(category=category).order_by('round_number', 'id')
    
    # Group by round
    rounds = {}
    for m in matches:
        if m.round_number not in rounds:
            rounds[m.round_number] = []
        rounds[m.round_number].append(m)
        
    return render(request, 'tournaments/category_detail.html', {
        'category': category,
        'rounds': rounds
    })

def category_ranking(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    players = CategoryPlayer.objects.filter(category=category).order_by('-points', '-wins', 'matches_played')
    
    return render(request, 'tournaments/category_ranking.html', {
        'category': category,
        'players': players
    })

def knockout_list(request):
    tournaments = Tournament.objects.filter(is_active=True, tournament_type='knockout').order_by('-id')
    return render(request, 'tournaments/knockout_list.html', {'tournaments': tournaments})

def knockout_detail(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id, tournament_type='knockout')
    
    matches = Match.objects.filter(tournament=tournament).order_by('round_number', 'position_in_bracket')
    
    matches_list = list(matches)
    match_by_id = {}
    children_by_next_match = {}
    
    num_brackets = getattr(tournament, 'number_of_brackets', 1)
    
    # Calculate bracket labels for round 1
    if num_brackets > 1:
        r1_matches = [m for m in matches_list if m.round_number == 1]
        total_r1 = len(r1_matches)
        if total_r1 > 0:
            matches_per_bracket = total_r1 // num_brackets
            if matches_per_bracket > 0:
                for m in r1_matches:
                    idx = m.position_in_bracket - 1
                    if idx % matches_per_bracket == 0:
                        m.bracket_label = f"Chave { (idx // matches_per_bracket) + 1 }"

    rounds_dict = {}
    
    match_counter = 1
    for m in matches_list:
        m.match_number = match_counter
        match_by_id[m.id] = m
        match_counter += 1
        
        if m.next_match_id:
            if m.next_match_id not in children_by_next_match:
                children_by_next_match[m.next_match_id] = []
            children_by_next_match[m.next_match_id].append(m)
            
        if m.round_number not in rounds_dict:
            rounds_dict[m.round_number] = []
        rounds_dict[m.round_number].append(m)
        
    for m in matches_list:
        m.prev_match_a = None
        m.prev_match_b = None
        if m.id in children_by_next_match:
            for prev in children_by_next_match[m.id]:
                if prev.position_in_bracket % 2 != 0:
                    m.prev_match_a = prev
                else:
                    m.prev_match_b = prev
                    
    if not matches_list:
        brackets_list = []
    else:
        brackets_list = [{
            'name': "Chave Principal",
            'rounds': rounds_dict
        }]
                    
    return render(request, 'tournaments/knockout_detail.html', {
        'tournament': tournament,
        'brackets': brackets_list
    })

import io
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime, timedelta

def tournament_schedule_pdf(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id, tournament_type='knockout')
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(A4), 
        rightMargin=30, 
        leftMargin=30, 
        topMargin=30, 
        bottomMargin=30,
        title=f"Chamada - {tournament.name}"
    )
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1 # Center
    
    normal_style = styles['Normal']
    normal_style.alignment = 1 # Center
    
    elements.append(Paragraph("TC22A - Tenis Clube 22 de Agosto", title_style))
    elements.append(Paragraph(f"Lista de Chamada: {tournament.name}", title_style))
    
    date_str = ""
    if tournament.start_date:
        date_str += f"Início: {tournament.start_date.strftime('%d/%m/%Y')} "
    if tournament.end_date:
        date_str += f"| Fim: {tournament.end_date.strftime('%d/%m/%Y')}"
        
    formato_sets = tournament.get_set_format_display()
        
    elements.append(Paragraph(f"Tipo: Torneio Eliminatório | {formato_sets} | {date_str}", normal_style))
    elements.append(Spacer(1, 20))
    
    matches = list(Match.objects.filter(tournament=tournament).order_by('round_number', 'position_in_bracket'))
    
    match_number_map = {}
    for idx, match in enumerate(matches, 1):
        match_number_map[match.id] = idx
        
    if tournament.start_date:
        current_datetime = datetime.combine(tournament.start_date, datetime.min.time().replace(hour=8, minute=0))
    else:
        current_datetime = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        
    end_of_day = current_datetime.replace(hour=18, minute=0)
    match_interval = timedelta(hours=1, minutes=30)
    
    DIAS_SEMANA = ["SEGUNDA-FEIRA", "TERÇA-FEIRA", "QUARTA-FEIRA", "QUINTA-FEIRA", "SEXTA-FEIRA", "SÁBADO", "DOMINGO"]
    
    def create_day_table(t_data, p_rows):
        # Ajusta colWidths para Hora mais estreita e os outros campos mais largos
        t = Table(t_data, colWidths=[50, 40, 190, 40, 20, 40, 190, 100])
        t_styles = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('ALIGN', (6, 1), (6, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        
        for r_idx in p_rows:
            t_styles.extend([
                ('SPAN', (0, r_idx), (-1, r_idx)),
                ('BACKGROUND', (0, r_idx), (-1, r_idx), colors.HexColor('#dbeafe')),
                ('TEXTCOLOR', (0, r_idx), (-1, r_idx), colors.black),
                ('FONTNAME', (0, r_idx), (-1, r_idx), 'Helvetica-Bold'),
                ('ALIGN', (0, r_idx), (-1, r_idx), 'CENTER'),
                ('ALIGN', (2, r_idx), (2, r_idx), 'CENTER'),
                ('ALIGN', (6, r_idx), (6, r_idx), 'CENTER'),
            ])
            
        t.setStyle(TableStyle(t_styles))
        return t

    def start_new_day(dt, elems):
        d = [['Hora', 'Jogo', 'Tenista A', 'Sets A', 'X', 'Sets B', 'Tenista B', 'Resultado']]
        dia_semana = DIAS_SEMANA[dt.weekday()]
        data_str = dt.strftime("%d/%m/%Y")
        
        heading_text = f"PROGRAMAÇÃO DOS JOGOS {data_str}  |  {dia_semana}"
        heading_style = ParagraphStyle(
            'DayHeading',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            alignment=1, # Center
            spaceAfter=10
        )
        elems.append(Paragraph(heading_text, heading_style))
        return d, []
        
    data, phase_rows = start_new_day(current_datetime, elements)
    current_phase = None
    
    for idx, match in enumerate(matches, 1):
        if current_datetime + match_interval > end_of_day:
            # Encerra tabela atual
            elements.append(create_day_table(data, phase_rows))
            elements.append(Spacer(1, 20))
            
            # Vai para próximo dia
            current_datetime = current_datetime + timedelta(days=1)
            current_datetime = current_datetime.replace(hour=8, minute=0)
            end_of_day = current_datetime.replace(hour=18, minute=0)
            
            # Inicia nova tabela
            data, phase_rows = start_new_day(current_datetime, elements)
            current_phase = None
            
        time_str = current_datetime.strftime("%H:%M")
        
        # Insere a linha de fase se mudou
        if match.phase != current_phase:
            current_phase = match.phase
            phase_rows.append(len(data))
            data.append([current_phase.upper() if current_phase else "FASE INDEFINIDA", "", "", "", "", "", "", ""])
        
        prev_a = None
        prev_b = None
        for prev in match.previous_matches.all():
            if prev.position_in_bracket % 2 != 0:
                prev_a = prev
            else:
                prev_b = prev
                
        if match.player_a:
            tenista_a = match.player_a.name
        elif prev_a:
            tenista_a = f"Vencedor Jogo {match_number_map.get(prev_a.id, '?')}"
        else:
            tenista_a = "Bye"
            
        if match.player_b:
            tenista_b = match.player_b.name
        elif prev_b:
            tenista_b = f"Vencedor Jogo {match_number_map.get(prev_b.id, '?')}"
        else:
            tenista_b = "Bye"
        
        sets_a = str(match.sets_a) if match.status == 'completed' else ""
        sets_b = str(match.sets_b) if match.status == 'completed' else ""
        
        resultado_str = ""
        if match.status == 'completed':
            sets_scores = []
            for i in range(1, 6):
                sa = getattr(match, f'set{i}_a')
                sb = getattr(match, f'set{i}_b')
                if sa is not None and sb is not None:
                    sets_scores.append(f"{sa}/{sb}")
            
            if sets_scores:
                resultado_str = " ".join(sets_scores)
            elif sets_a != "" and sets_b != "":
                resultado_str = f"{sets_a} x {sets_b}"
            else:
                resultado_str = "W.O." if match.winner else "Encerrado"
        
        data.append([time_str, f"{idx}", tenista_a, sets_a, "X", sets_b, tenista_b, resultado_str])
        
        current_datetime += match_interval
        
    if len(data) > 1:
        elements.append(create_day_table(data, phase_rows))
    doc.build(elements)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="chamada_{tournament.id}.pdf"'
    response.write(pdf)
    return response
