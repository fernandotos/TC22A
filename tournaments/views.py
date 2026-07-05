from django.shortcuts import render, get_object_or_404
from .models import Category, Match, CategoryPlayer, HomeBanner

def home(request):
    categories = Category.objects.all().order_by('name')
    banner = HomeBanner.objects.filter(is_active=True).first()
    return render(request, 'tournaments/home.html', {'categories': categories, 'banner': banner})

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
