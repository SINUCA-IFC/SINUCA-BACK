"""
Script avançado - Tasks dinâmicas, eventos especiais e cronogramas temáticos para Sinuca.
Execute DEPOIS do script principal: python manage.py shell < populate_sinuca_advanced.py
"""

from django.utils import timezone
from datetime import timedelta
from core.models import Country, Task, Post, Schedule, Category

now = timezone.now()

# ==================== TASKS AVANÇADAS E CRIATIVAS ====================

advanced_tasks = [
    # ====== TASKS DE CONFLITO ======
    {
        "title": "Mediar Conflito Regional",
        "description": "Uma crise humanitária eclodiu. Negocie cessar-fogo e coordene ajuda internacional. Ganhe pontos ajudando ambos os lados.",
        "category": "Diplomático",
        "points": 200,
        "countries": ["USA", "RUS", "CHN", "FRA", "GBR"],
        "difficulty": "Difícil",
    },
    {
        "title": "Enviar Tropas Peacekeeping",
        "description": "Contribua com força de paz internacional. Quanto mais cedo, mais pontos. Risco de sofrer veto no Conselho.",
        "category": "Militar",
        "points": 150,
        "countries": None,
        "difficulty": "Média",
    },
    {
        "title": "Bloquear Resolução com Veto",
        "description": "Como membro permanente, você pode vetar. Isso causa impacto diplomático - use com sabedoria!",
        "category": "Diplomático",
        "points": 180,
        "countries": ["USA", "RUS", "CHN", "FRA", "GBR"],
        "difficulty": "Difícil",
    },
    
    # ====== TASKS ECONÔMICAS ======
    {
        "title": "Fechar Acordo Comercial Trilateral",
        "description": "Negocie com 2 outros países. Maior bloco econômico = mais pontos.",
        "category": "Econômico",
        "points": 140,
        "countries": None,
        "difficulty": "Média",
    },
    {
        "title": "Impor Sanções Econômicas",
        "description": "Convença outros países a sancionar uma nação. Ganha força com mais apoio.",
        "category": "Econômico",
        "points": 120,
        "countries": ["USA", "DEU", "FRA", "GBR", "CAN", "AUS"],
        "difficulty": "Média",
    },
    {
        "title": "Criar Banco de Desenvolvimento",
        "description": "Líder de potências emergentes, proponha banco regional para financiar projetos. (Ex: NDB dos BRICS)",
        "category": "Econômico",
        "points": 160,
        "countries": ["BRA", "RUS", "IND", "CHN", "ZAF"],
        "difficulty": "Difícil",
    },
    {
        "title": "Atrair Investimento Externo",
        "description": "Como país em desenvolvimento, convença potências a investir em sua economia.",
        "category": "Econômico",
        "points": 100,
        "countries": ["BRA", "IND", "EGY", "MEX", "ZAF"],
        "difficulty": "Média",
    },
    
    # ====== TASKS AMBIENTAIS ======
    {
        "title": "Defender Protocolo Climático Forte",
        "description": "Proponha metas ambiciosas. Ganhe pontos de países que votarem com você.",
        "category": "Ambiental",
        "points": 110,
        "countries": None,
        "difficulty": "Média",
    },
    {
        "title": "Rejeitar Protocolo Climático",
        "description": "Defenda interesses econômicos. Risco de isolamento diplomático.",
        "category": "Ambiental",
        "points": 90,
        "countries": ["USA", "CHN", "RUS", "IND", "AUS"],
        "difficulty": "Média",
    },
    {
        "title": "Liderar Coalizão Verde",
        "description": "Convoque países para formar bloco ambiental. Maior bloco = mais influência.",
        "category": "Ambiental",
        "points": 130,
        "countries": ["DEU", "BRA", "CAN", "SWE"],
        "difficulty": "Média",
    },
    {
        "title": "Reparações Climáticas",
        "description": "Países desenvolvidos pagam países em desenvolvimento pelos danos climáticos. Negocie valor.",
        "category": "Ambiental",
        "points": 120,
        "countries": None,
        "difficulty": "Difícil",
    },
    
    # ====== TASKS TECNOLÓGICAS ======
    {
        "title": "Regulação da Inteligência Artificial",
        "description": "Proponha framework internacional para IA. Pode dividir opinião: inovação vs segurança.",
        "category": "Tecnológico",
        "points": 135,
        "countries": ["USA", "CHN", "DEU", "GBR", "JPN"],
        "difficulty": "Difícil",
    },
    {
        "title": "Ataque Cibernético - Responder",
        "description": "Seu país sofreu ataque cibernético. Negocie resposta diplomática ou militar.",
        "category": "Militar",
        "points": 100,
        "countries": None,
        "difficulty": "Média",
    },
    {
        "title": "Dividir Acesso à Internet",
        "description": "Países querem regular censura online. Defenda liberdade vs segurança.",
        "category": "Tecnológico",
        "points": 105,
        "countries": None,
        "difficulty": "Média",
    },
    
    # ====== TASKS DE DIREITOS HUMANOS ======
    {
        "title": "Condenar Violação de Direitos",
        "description": "Plenário vota condenação de país por violações. Votar contra = risco diplomático.",
        "category": "Social",
        "points": 95,
        "countries": None,
        "difficulty": "Média",
    },
    {
        "title": "Defender Refugiados",
        "description": "Seu país recebe refugiados. Ganhe pontos humanitários mas sofra oposição interna.",
        "category": "Social",
        "points": 110,
        "countries": ["CAN", "DEU", "SWE", "AUS"],
        "difficulty": "Média",
    },
    {
        "title": "Reforma de Direitos das Mulheres",
        "description": "Proponha resoluções sobre igualdade de gênero. Conseguir apoio é desafiador.",
        "category": "Social",
        "points": 115,
        "countries": None,
        "difficulty": "Média",
    },
    
    # ====== TASKS DE PROPAGANDA ======
    {
        "title": "Vencer o Coração da Assembleia",
        "description": "Faça discurso emocionante. Delegados que votarem com você ganham pontos extras.",
        "category": "Diplomático",
        "points": 125,
        "countries": None,
        "difficulty": "Difícil",
    },
    {
        "title": "Desmascarar Propagação de Desinformação",
        "description": "Acuse outro país de fake news. Se provar, ganha pontos. Se falhar, perde credibilidade.",
        "category": "Diplomático",
        "points": 100,
        "countries": None,
        "difficulty": "Difícil",
    },
    
    # ====== TASKS REGIONAIS ESPECÍFICAS ======
    {
        "title": "[EUA] Manter Hegemonia",
        "description": "Como superpotência, mantenha influência sobre aliados. Negocie com UE, Japão e Coreia.",
        "category": "Diplomático",
        "points": 160,
        "countries": ["USA"],
        "difficulty": "Difícil",
    },
    {
        "title": "[China] Expansão da Influência",
        "description": "Implemente Belt and Road. Invista em países em desenvolvimento. Ganhe aliados.",
        "category": "Econômico",
        "points": 150,
        "countries": ["CHN"],
        "difficulty": "Difícil",
    },
    {
        "title": "[Rússia] Afirmar Presença Regional",
        "description": "Defenda influência na Europa Oriental. Risco alto, recompensa alta.",
        "category": "Militar",
        "points": 140,
        "countries": ["RUS"],
        "difficulty": "Difícil",
    },
    {
        "title": "[Brasil] Liderança Sul-Americana",
        "description": "Coordene BRICS, defenda MERCOSUL, promova integração regional.",
        "category": "Econômico",
        "points": 130,
        "countries": ["BRA"],
        "difficulty": "Média",
    },
    {
        "title": "[Índia] Mediador Global",
        "description": "Use posição de não-alinhado para mediar conflitos. Ganhe influência.",
        "category": "Diplomático",
        "points": 140,
        "countries": ["IND"],
        "difficulty": "Média",
    },
    {
        "title": "[África do Sul] Voz do Continente",
        "description": "Represente interesses africanos. Construa coalizão com países do continente.",
        "category": "Diplomático",
        "points": 120,
        "countries": ["ZAF"],
        "difficulty": "Média",
    },
    {
        "title": "[UE] Aprofundar Integração",
        "description": "Proponha política comum em defesa, energia e economia digital.",
        "category": "Econômico",
        "points": 125,
        "countries": ["DEU", "FRA", "ITA", "ESP"],
        "difficulty": "Difícil",
    },
    
    # ====== TASKS SURPRISE ======
    {
        "title": "Ganhar Eleição para Conselho",
        "description": "Como país não-permanente, concorra a vaga no Conselho de Segurança.",
        "category": "Diplomático",
        "points": 200,
        "countries": None,
        "difficulty": "Difícil",
    },
    {
        "title": "Solicitar Revisão Territorial",
        "description": "Reclame território. Risco muito alto - pode gerar guerra.",
        "category": "Militar",
        "points": 180,
        "countries": ["RUS", "CHN", "IRN"],
        "difficulty": "Difícil",
    },
    {
        "title": "Pedir Perdão por Atrocidades",
        "description": "Países podem reconhecer e pedir desculpas por crimes históricos. Ganhe pontos de moral.",
        "category": "Social",
        "points": 140,
        "countries": None,
        "difficulty": "Média",
    },
]

# ==================== INSERIR TASKS AVANÇADAS ====================
try:
    ambiental = Category.objects.get(name="Ambiental")
    economico = Category.objects.get(name="Econômico")
    militar = Category.objects.get(name="Militar")
    social = Category.objects.get(name="Social")
    tecnologico = Category.objects.get(name="Tecnológico")
    diplomatico = Category.objects.get(name="Diplomático")
    
    countries_dict = {c.code: c for c in Country.objects.all()}
    
    created_count = 0
    for task_data in advanced_tasks:
        countries_to_add = []
        if task_data["countries"]:
            countries_to_add = [countries_dict[code] for code in task_data["countries"] if code in countries_dict]
        
        cat_name = task_data["category"]
        cat_map = {
            "Ambiental": ambiental,
            "Econômico": economico,
            "Militar": militar,
            "Social": social,
            "Tecnológico": tecnologico,
            "Diplomático": diplomatico,
        }
        
        task, created = Task.objects.get_or_create(
            title=task_data["title"],
            defaults={
                "description": task_data["description"],
                "category": cat_map.get(cat_name),
                "points": task_data["points"],
                "difficulty": task_data["difficulty"],
            }
        )
        
        if created:
            if countries_to_add:
                task.countries.set(countries_to_add)
            created_count += 1
            print(f"✓ Task criada: {task_data['title']}")
    
    print(f"\n✅ {created_count} tasks avançadas adicionadas!")

except Exception as e:
    print(f"❌ Erro ao criar tasks: {e}")

# ==================== POSTS BREAKING NEWS ====================
breaking_news = [
    {
        "title": "⚠️ BREAKING: Tensão Militar Escala",
        "content": "Relatórios indicam mobilização de forças. Comunidade internacional convocada para sessão de emergência.",
        "image_url": "https://images.unsplash.com/photo-1569163139394-de4798aa62b2?w=800",
        "country": None,
        "created_at": now - timedelta(hours=2),
    },
    {
        "title": "🌊 Desastre Natural Causa Crise Humanitária",
        "content": "Terremoto destrói infraestrutura. Milhares desabrigados. ONU coordena resposta internacional.",
        "image_url": "https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=800",
        "country": None,
        "created_at": now - timedelta(hours=4),
    },
    {
        "title": "📈 Mercados Globais Reagem a Acordo Comercial",
        "content": "Maior bloco comercial formado desde o NAFTA. Índices de bolsa disparam.",
        "image_url": "https://images.unsplash.com/photo-1611432579715-cc69ad386331?w=800",
        "country": None,
        "created_at": now - timedelta(hours=6),
    },
    {
        "title": "🤝 Negociações de Paz Avançam em Rodada Secreta",
        "content": "Diplomatas se encontram discretamente. Esperança renovada de resolução do conflito.",
        "image_url": "https://images.unsplash.com/photo-1552664730-d307ca884978?w=800",
        "country": None,
        "created_at": now - timedelta(hours=8),
    },
    {
        "title": "🏆 Votação Histórica Aprova Tratado Ambiental",
        "content": "Pela primeira vez, maioria esmagadora aprova protocolo climático ambicioso.",
        "image_url": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800",
        "country": None,
        "created_at": now - timedelta(hours=10),
    },
]

try:
    for news in breaking_news:
        post, created = Post.objects.get_or_create(
            title=news["title"],
            created_at=news["created_at"],
            defaults={
                "content": news["content"],
                "image_url": news["image_url"],
                "country": news["country"],
            }
        )
        if created:
            print(f"✓ Breaking News criado: {news['title']}")
    
    print(f"\n✅ Breaking News adicionados!")
except Exception as e:
    print(f"❌ Erro ao criar posts: {e}")

# ==================== CRONOGRAMAS ESPECIAIS ====================
special_schedules = [
    {
        "title": "Duelo Diplomático: EUA vs China",
        "description": "Debate direto entre superpotências sobre liderança global.",
        "start_date": now + timedelta(days=8, hours=14),
        "end_date": now + timedelta(days=8, hours=16),
        "countries": ["USA", "CHN"],
        "location": "Plenário Principal",
    },
    {
        "title": "Bloco de Emergência - Crise Humanitária",
        "description": "Sessão extraordinária de emergência para coordenar resposta humanitária.",
        "start_date": now + timedelta(days=7, hours=10),
        "end_date": now + timedelta(days=7, hours=13),
        "countries": None,
        "location": "Conselho de Segurança",
    },
    {
        "title": "Votação Secreta - Reforma do Conselho",
        "description": "Votação sobre ampliação e reforma do Conselho de Segurança.",
        "start_date": now + timedelta(days=9, hours=15),
        "end_date": now + timedelta(days=9, hours=17),
        "countries": None,
        "location": "Assembleia Geral",
    },
    {
        "title": "Negociações em Câmaras - Acordos Bilaterais",
        "description": "Período aberto para negociações privadas entre delegações.",
        "start_date": now + timedelta(days=5, hours=9),
        "end_date": now + timedelta(days=5, hours=17),
        "countries": None,
        "location": "Salas de Negociação",
    },
    {
        "title": "Conferência de Imprensa - Posição de Países",
        "description": "Cada país tem oportunidade de apresentar sua posição à mídia.",
        "start_date": now + timedelta(days=6, hours=16),
        "end_date": now + timedelta(days=6, hours=18),
        "countries": None,
        "location": "Sala de Imprensa",
    },
]

try:
    countries_dict = {c.code: c for c in Country.objects.all()}
    
    for sched_data in special_schedules:
        countries_to_add = []
        if sched_data["countries"]:
            countries_to_add = [countries_dict[code] for code in sched_data["countries"]]
        
        schedule, created = Schedule.objects.get_or_create(
            title=sched_data["title"],
            start_date=sched_data["start_date"],
            defaults={
                "description": sched_data["description"],
                "end_date": sched_data["end_date"],
                "location": sched_data["location"],
            }
        )
        
        if created:
            if countries_to_add:
                schedule.countries.set(countries_to_add)
            print(f"✓ Cronograma especial criado: {sched_data['title']}")
    
    print(f"\n✅ Cronogramas especiais adicionados!")
except Exception as e:
    print(f"❌ Erro ao criar cronogramas: {e}")

print("\n" + "="*50)
print("🎉 POPULAÇÃO AVANÇADA CONCLUÍDA COM SUCESSO!")
print("="*50)
print(f"\nTotal de tasks: {Task.objects.count()}")
print(f"Total de posts: {Post.objects.count()}")
print(f"Total de cronogramas: {Schedule.objects.count()}")
print("\nO site agora está muito mais dinâmico! 🚀")
