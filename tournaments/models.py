from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class Tournament(models.Model):
    TOURNAMENT_TYPES = [
        ('ranking', 'Ranking'),
        ('knockout', 'Torneio Eliminatório'),
    ]
    COMPETITION_TYPES = [
        ('simples', 'Simples'),
        ('duplas', 'Duplas'),
    ]
    SET_FORMATS = [
        ('3_normal', 'Melhor de 3 Sets Normal'),
        ('3_super', 'Melhor de 3 Sets (3º Set é Super Tiebreak)'),
        ('5_normal', 'Melhor de 5 Sets Normal'),
    ]

    name = models.CharField(max_length=200, verbose_name="Nome do Torneio/Ranking")
    tournament_type = models.CharField(max_length=20, choices=TOURNAMENT_TYPES, default='ranking', verbose_name="Tipo")
    competition_type = models.CharField(max_length=20, choices=COMPETITION_TYPES, default='simples', verbose_name="Competição")
    set_format = models.CharField(max_length=20, choices=SET_FORMATS, default='3_normal', verbose_name="Formato de Sets")
    
    current_round = models.IntegerField(verbose_name="Rodada Atual", default=1)
    start_date = models.DateField(verbose_name="Data de Início", null=True, blank=True)
    end_date = models.DateField(verbose_name="Data de Fim", null=True, blank=True)
    number_of_brackets = models.IntegerField(default=1, verbose_name="Número de Chaves (Eliminatório)", help_text="Apenas para Torneios Eliminatórios: O número de chaves paralelas (ex: 2 para dividir 32 atletas em 2 chaves de 16).")
    is_active = models.BooleanField(default=True, verbose_name="Ativo (Exibir no site)")
    is_finished = models.BooleanField(default=False, verbose_name="Encerrado", help_text="Marque esta opção quando o torneio/ranking chegar ao fim.")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_is_finished = self.is_finished

    def __str__(self):
        return self.name
        
    class Meta:
        verbose_name = "Torneio/Ranking Base"
        verbose_name_plural = "Torneios/Rankings Base"

class RankingTournament(Tournament):
    class Meta:
        proxy = True
        verbose_name = "Ranking"
        verbose_name_plural = "Rankings"

class KnockoutTournament(Tournament):
    class Meta:
        proxy = True
        verbose_name = "Torneio Eliminatório"
        verbose_name_plural = "Torneios Eliminatórios"

class Category(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='categories', null=True, blank=True)
    name = models.CharField(max_length=100, verbose_name="Nome da Categoria")
    is_finished = models.BooleanField(default=False, verbose_name="Encerrada", help_text="Se todas as categorias forem encerradas, o ranking também será.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_is_finished = self.is_finished

    def __str__(self):
        if self.tournament:
            return f"{self.tournament.name} - {self.name}"
        return f"S/ Ranking - {self.name}"

    class Meta:
        unique_together = ('tournament', 'name')
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

class Player(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="Nome do Atleta")

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Atleta"
        verbose_name_plural = "Atletas"

class CategoryPlayer(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='players')
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    points = models.IntegerField(default=0, verbose_name="Pontos")
    matches_played = models.IntegerField(default=0, verbose_name="Jogos")
    wins = models.IntegerField(default=0, verbose_name="Vitórias")
    losses = models.IntegerField(default=0, verbose_name="Derrotas")

    def __str__(self):
        return f"{self.player.name} - {self.category.name}"

    class Meta:
        unique_together = ('category', 'player')
        verbose_name = "Classificação"
        verbose_name_plural = "Classificações"
        ordering = ['-points', '-wins', 'matches_played'] # Basic tiebreakers

class Match(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('completed', 'Finalizado'),
        ('cancelled', 'Não Ocorreu (Cancelado)'),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='matches', null=True, blank=True)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='all_matches', null=True, blank=True)
    round_number = models.IntegerField(verbose_name="Rodada")
    player_a = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='matches_as_a', null=True, blank=True)
    player_b = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='matches_as_b', null=True, blank=True)
    
    # Results
    # General Results
    sets_a = models.IntegerField(default=0, verbose_name="Sets Ganhos (A)")
    sets_b = models.IntegerField(default=0, verbose_name="Sets Ganhos (B)")
    
    # Games per Set
    set1_a = models.IntegerField(null=True, blank=True, verbose_name="Set 1 - A")
    set1_b = models.IntegerField(null=True, blank=True, verbose_name="Set 1 - B")
    set2_a = models.IntegerField(null=True, blank=True, verbose_name="Set 2 - A")
    set2_b = models.IntegerField(null=True, blank=True, verbose_name="Set 2 - B")
    set3_a = models.IntegerField(null=True, blank=True, verbose_name="Set 3 - A")
    set3_b = models.IntegerField(null=True, blank=True, verbose_name="Set 3 - B")
    set4_a = models.IntegerField(null=True, blank=True, verbose_name="Set 4 - A")
    set4_b = models.IntegerField(null=True, blank=True, verbose_name="Set 4 - B")
    set5_a = models.IntegerField(null=True, blank=True, verbose_name="Set 5 - A")
    set5_b = models.IntegerField(null=True, blank=True, verbose_name="Set 5 - B")
    
    # Knockout specific
    next_match = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='previous_matches')
    phase = models.CharField(max_length=50, blank=True, verbose_name="Fase")
    position_in_bracket = models.IntegerField(null=True, blank=True)
    winner = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_matches')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        a_name = self.player_a.name if self.player_a else "Bye"
        b_name = self.player_b.name if self.player_b else "Bye"
        return f"Rodada {self.round_number}: {a_name} vs {b_name}"
    
    @property
    def is_bye(self):
        return self.player_a is None or self.player_b is None

    class Meta:
        verbose_name = "Jogo"
        verbose_name_plural = "Jogos"
        ordering = ['round_number', 'id']

# Signal to calculate points when a match is saved
@receiver(post_save, sender=Match)
def update_rankings(sender, instance, created, **kwargs):
    # Sempre calcula o vencedor e sets automaticamente se finalizado
    if instance.status == 'completed':
        # Calcula sets ganhos baseado nos games caso o ADM tenha esquecido de preencher
        if instance.sets_a == 0 and instance.sets_b == 0:
            calc_a, calc_b = 0, 0
            for i in range(1, 6):
                sa = getattr(instance, f'set{i}_a')
                sb = getattr(instance, f'set{i}_b')
                if sa is not None and sb is not None:
                    if sa > sb: calc_a += 1
                    elif sb > sa: calc_b += 1
            if calc_a > 0 or calc_b > 0:
                instance.sets_a = calc_a
                instance.sets_b = calc_b
                
        calculated_winner = None
        if instance.sets_a > instance.sets_b:
            calculated_winner = instance.player_a
        elif instance.sets_b > instance.sets_a:
            calculated_winner = instance.player_b
            
        if instance.winner != calculated_winner or (instance.sets_a > 0 or instance.sets_b > 0):
            post_save.disconnect(update_rankings, sender=Match)
            instance.winner = calculated_winner
            instance.save(update_fields=['winner', 'sets_a', 'sets_b'])
            post_save.connect(update_rankings, sender=Match)
    elif instance.status == 'pending' and instance.winner is not None:
        post_save.disconnect(update_rankings, sender=Match)
        instance.winner = None
        instance.save(update_fields=['winner'])
        post_save.connect(update_rankings, sender=Match)

    # Se for jogo de Torneio Eliminatório, não calcula pontuação de Ranking
    if instance.tournament and instance.tournament.tournament_type == 'knockout':
        if instance.next_match:
            nm = instance.next_match
            # Avança o vencedor se estiver finalizado, senão limpa a vaga
            if instance.position_in_bracket % 2 != 0:
                nm.player_a = instance.winner if instance.status == 'completed' else None
            else:
                nm.player_b = instance.winner if instance.status == 'completed' else None
            nm.save()
        return

    if not instance.category:
        return
        
    # Recalculate everything for this category to ensure consistency
    category = instance.category
    
    # Reset all stats for players in this category
    for cp in category.players.all():
        cp.points = 0
        cp.matches_played = 0
        cp.wins = 0
        cp.losses = 0
        cp.save()

    # Recalculate
    completed_matches = Match.objects.filter(category=category, status__in=['completed', 'cancelled'])
    for match in completed_matches:
        cp_a = CategoryPlayer.objects.filter(category=category, player=match.player_a).first() if match.player_a else None
        cp_b = CategoryPlayer.objects.filter(category=category, player=match.player_b).first() if match.player_b else None
        
        if match.is_bye:
            cp_real = cp_a if cp_a else cp_b
            if cp_real and match.status == 'completed':
                cp_real.matches_played += 1
                if (cp_real == cp_a and match.sets_a == 2) or (cp_real == cp_b and match.sets_b == 2):
                    cp_real.points += 3
                    cp_real.wins += 1
                cp_real.save()
            continue
            
        if not cp_a or not cp_b:
            continue
            
        if match.status == 'cancelled':
            cp_a.matches_played += 1
            cp_b.matches_played += 1
            # 0 points for both
            cp_a.save()
            cp_b.save()
            continue
            
        # Match completed normally
        cp_a.matches_played += 1
        cp_b.matches_played += 1
        
        # Determine points
        # 2x0 -> 3 pts winner, 0 pts loser
        # 2x1 -> 2 pts winner, 1 pt loser
        
        if match.sets_a == 2 and match.sets_b == 0:
            cp_a.points += 3
            cp_a.wins += 1
            cp_b.losses += 1
            match.winner = match.player_a
        elif match.sets_a == 2 and match.sets_b == 1:
            cp_a.points += 2
            cp_b.points += 1
            cp_a.wins += 1
            cp_b.losses += 1
            match.winner = match.player_a
        elif match.sets_b == 2 and match.sets_a == 0:
            cp_b.points += 3
            cp_b.wins += 1
            cp_a.losses += 1
            match.winner = match.player_b
        elif match.sets_b == 2 and match.sets_a == 1:
            cp_b.points += 2
            cp_a.points += 1
            cp_b.wins += 1
            cp_a.losses += 1
            match.winner = match.player_b
            
        cp_a.save()
        cp_b.save()
        
        # Disconnect signal temporarily to save winner without recursion
        post_save.disconnect(update_rankings, sender=Match)
        match.save(update_fields=['winner'])
        post_save.connect(update_rankings, sender=Match)

@receiver(post_save, sender=Tournament)
@receiver(post_save, sender=RankingTournament)
@receiver(post_save, sender=KnockoutTournament)
def sync_tournament_finished_state(sender, instance, **kwargs):
    if hasattr(instance, '_initial_is_finished') and instance.is_finished != instance._initial_is_finished:
        if instance.is_finished:
            instance.categories.filter(is_finished=False).update(is_finished=True)
        else:
            instance.categories.filter(is_finished=True).update(is_finished=False)
        instance._initial_is_finished = instance.is_finished

@receiver(post_save, sender=Category)
def sync_category_finished_state(sender, instance, **kwargs):
    if not instance.tournament:
        return
        
    if hasattr(instance, '_initial_is_finished') and instance.is_finished != instance._initial_is_finished:
        tournament = instance.tournament
        if instance.is_finished:
            all_finished = not tournament.categories.filter(is_finished=False).exists()
            if all_finished and not tournament.is_finished:
                Tournament.objects.filter(id=tournament.id).update(is_finished=True)
                tournament.is_finished = True
                tournament._initial_is_finished = True
        else:
            if tournament.is_finished:
                Tournament.objects.filter(id=tournament.id).update(is_finished=False)
                tournament.is_finished = False
                tournament._initial_is_finished = False
                
        instance._initial_is_finished = instance.is_finished
