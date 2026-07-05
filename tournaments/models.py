from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class Tournament(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nome da Barragem")
    current_round = models.IntegerField(verbose_name="Rodada Atual", default=1)
    start_date = models.DateField(verbose_name="Data de Início", null=True, blank=True)
    end_date = models.DateField(verbose_name="Data de Fim", null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Ativo (Exibir no site)")
    
    def __str__(self):
        return self.name
        
    class Meta:
        verbose_name = "Barragem"
        verbose_name_plural = "Barragens"

class Category(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='categories', null=True, blank=True)
    name = models.CharField(max_length=100, verbose_name="Nome da Categoria")

    def __str__(self):
        if self.tournament:
            return f"{self.tournament.name} - {self.name}"
        return f"S/ Barragem - {self.name}"

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

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='matches')
    round_number = models.IntegerField(verbose_name="Rodada")
    player_a = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='matches_as_a', null=True, blank=True)
    player_b = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='matches_as_b', null=True, blank=True)
    
    # Results
    sets_a = models.IntegerField(default=0, verbose_name="Sets Atleta A")
    sets_b = models.IntegerField(default=0, verbose_name="Sets Atleta B")
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


