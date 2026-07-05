import pandas as pd
from .models import Tournament, Category, Player, CategoryPlayer, Match

def generate_round_robin_matches(category, players):
    """
    Generates round-robin matches for a list of players in a category.
    Handles 'Bye' for odd number of players.
    """
    if not players:
        return

    # If odd number of players, add a None (Bye)
    if len(players) % 2 != 0:
        players.append(None)

    num_players = len(players)
    num_rounds = num_players - 1
    half_size = num_players // 2

    matches_to_create = []

    for round_idx in range(num_rounds):
        round_number = round_idx + 1
        for i in range(half_size):
            player_a = players[i]
            player_b = players[num_players - 1 - i]
            
            if player_a is not None or player_b is not None:
                matches_to_create.append(
                    Match(
                        category=category,
                        round_number=round_number,
                        player_a=player_a,
                        player_b=player_b,
                        status='pending'
                    )
                )

        # Rotate players: keep the first player fixed, rotate the rest clockwise
        players = [players[0]] + [players[-1]] + players[1:-1]

    Match.objects.bulk_create(matches_to_create)

def process_excel_tournament(file, tournament):
    """
    Process an Excel file. Unified logic:
    If 'Confrontos' sheet exists and has data -> In Progress Tournament
    Otherwise -> New Tournament (Generates Round-Robin automatically)
    """
    xls = pd.ExcelFile(file)
    messages_list = []
    
    # 1. Process Cadastro
    df_cadastro = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
    if len(df_cadastro.columns) < 2:
        raise ValueError("A aba de Cadastro precisa ter pelo menos 2 colunas: Nome e Categoria.")
        
    names = df_cadastro.iloc[:, 0].astype(str).str.strip()
    categories = df_cadastro.iloc[:, 1].astype(str).str.strip()
    
    category_players_map = {}
    
    for name, cat_name in zip(names, categories):
        if pd.isna(name) or name == 'nan' or pd.isna(cat_name) or cat_name == 'nan':
            continue
            
        category, _ = Category.objects.get_or_create(tournament=tournament, name=cat_name)
        player, _ = Player.objects.get_or_create(name=name)
        CategoryPlayer.objects.get_or_create(category=category, player=player)
        
        if category not in category_players_map:
            category_players_map[category] = []
        category_players_map[category].append(player)

    # 2. Check if Confrontos exists and has data
    has_confrontos = False
    matches_created = 0
    matches_updated = 0
    if len(xls.sheet_names) > 1:
        df_confrontos = pd.read_excel(xls, sheet_name=xls.sheet_names[1])
        if not df_confrontos.empty and len(df_confrontos.columns) >= 5:
            has_confrontos = True
            
            for index, row in df_confrontos.iterrows():
                cat_name = str(row.iloc[0]).strip()
                player_a_name = str(row.iloc[2]).strip()
                player_b_name = str(row.iloc[3]).strip()
                resultado = str(row.iloc[4]).strip().lower().replace(" ", "")

                if pd.isna(cat_name) or cat_name == 'nan': continue

                category = Category.objects.filter(tournament=tournament, name__iexact=cat_name).first()
                if not category:
                    category = Category.objects.filter(tournament=tournament, name__iexact=f"Categoria {cat_name}").first()
                if not category and len(cat_name) <= 3:
                    category = Category.objects.filter(tournament=tournament, name__iendswith=f" {cat_name}").first()

                if not category:
                    messages_list.append(f"Linha {index+2}: Categoria não encontrada -> {cat_name}")
                    continue

                p_a = None
                if player_a_name and player_a_name.lower() not in ('nan', 'bye', 'folga'):
                    p_a = Player.objects.filter(name__iexact=player_a_name).first()
                    if not p_a:
                        messages_list.append(f"Linha {index+2}: Atleta A não encontrado -> {player_a_name}")
                        continue
                        
                p_b = None
                if player_b_name and player_b_name.lower() not in ('nan', 'bye', 'folga'):
                    p_b = Player.objects.filter(name__iexact=player_b_name).first()
                    if not p_b:
                        messages_list.append(f"Linha {index+2}: Atleta B não encontrado -> {player_b_name}")
                        continue

                sets_a = 0
                sets_b = 0
                status = 'pending'
                winner = None

                if resultado and resultado not in ('nan', '', '0x0', '-'):
                    status = 'completed'
                    if 'x' in resultado:
                        try:
                            parts = resultado.split('x')
                            sets_a = int(parts[0])
                            sets_b = int(parts[1])
                            if sets_a > sets_b:
                                winner = p_a
                            elif sets_b > sets_a:
                                winner = p_b
                        except ValueError:
                            messages_list.append(f"Linha {index+2}: Placar inválido -> {resultado}")
                            status = 'pending'
                    elif 'v.o' in resultado or 'w.o' in resultado or 'wo' in resultado:
                        sets_a, sets_b = 2, 0
                        winner = p_a
                    else:
                        messages_list.append(f"Linha {index+2}: Placar em formato desconhecido -> {resultado}")
                        status = 'pending'
                
                match = Match.objects.filter(
                    category=category,
                    player_a=p_a,
                    player_b=p_b
                ).first()
                
                if not match:
                    match = Match.objects.filter(
                        category=category,
                        player_a=p_b,
                        player_b=p_a
                    ).first()
                    
                    if match:
                        sets_a, sets_b = sets_b, sets_a
                
                if not match:
                    try:
                        round_number = int(float(row.iloc[1]))
                    except (ValueError, TypeError):
                        round_number = 1
                        
                    match = Match.objects.create(
                        category=category,
                        round_number=round_number,
                        player_a=p_a,
                        player_b=p_b,
                        sets_a=sets_a,
                        sets_b=sets_b,
                        status=status,
                        winner=winner
                    )
                    matches_created += 1
                else:
                    if status == 'completed' or resultado == '0x0':
                        match.sets_a = sets_a
                        match.sets_b = sets_b
                        match.status = status
                        match.winner = winner
                        match.save()
                        matches_updated += 1

    if not has_confrontos:
        for category, players in category_players_map.items():
            Match.objects.filter(category=category).delete()
            generate_round_robin_matches(category, players)
        return True, "Nova Barragem gerada com sucesso! Todos contra todos criados.", messages_list
    
    return True, f"Barragem em andamento atualizada: {matches_created} jogos criados, {matches_updated} atualizados.", messages_list
