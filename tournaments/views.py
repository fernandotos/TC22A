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
    
    matches = Match.objects.filter(tournament=tournament).select_related('category').order_by('category__name', 'round_number', 'position_in_bracket')
    
    matches_list = list(matches)
    match_by_id = {}
    children_by_next_match = {}
    
    brackets_dict = {}
    
    match_counter = 1
    for m in matches_list:
        m.match_number = match_counter
        match_by_id[m.id] = m
        match_counter += 1
        
        if m.next_match_id:
            if m.next_match_id not in children_by_next_match:
                children_by_next_match[m.next_match_id] = []
            children_by_next_match[m.next_match_id].append(m)
            
        cat_key = m.category.name if m.category else "Chave Principal"
        
        if cat_key not in brackets_dict:
            brackets_dict[cat_key] = {}
            
        if m.round_number not in brackets_dict[cat_key]:
            brackets_dict[cat_key][m.round_number] = []
        brackets_dict[cat_key][m.round_number].append(m)
        
    for m in matches_list:
        m.prev_match_a = None
        m.prev_match_b = None
        if m.id in children_by_next_match:
            for prev in children_by_next_match[m.id]:
                if prev.position_in_bracket % 2 != 0:
                    m.prev_match_a = prev
                else:
                    m.prev_match_b = prev
                    
    brackets_list = []
    for cat_name, rounds in brackets_dict.items():
        brackets_list.append({
            'name': cat_name,
            'rounds': rounds
        })
                    
    return render(request, 'tournaments/knockout_detail.html', {
        'tournament': tournament,
        'brackets': brackets_list
    })
