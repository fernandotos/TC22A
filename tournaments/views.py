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
